from flask import Flask, request, abort, Response, jsonify
from flask_cors import CORS
import json
import requests
import logging
import traceback
import os
from dotenv import load_dotenv
import tempfile
import uuid
from datetime import datetime
import shutil
import hmac
import hashlib
import base64



logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


app = Flask(__name__)
CORS(app)  # 啟用 CORS 支援

# 載入環境變數
load_dotenv()

# 從環境變數讀取設定
CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")
ASSERTION_SIGNING_KEY = os.getenv("ASSERTION_SIGNING_KEY")

# 檢查必要的環境變數
if not CHANNEL_ACCESS_TOKEN or not CHANNEL_SECRET:
    raise ValueError("請在 .env 檔案中設定 CHANNEL_ACCESS_TOKEN 和 CHANNEL_SECRET")

# === 驗證 webhook 請求 ===
def verify_signature(body, signature):
    if not ASSERTION_SIGNING_KEY:
        return True  # 如果沒有設定 key，暫時跳過驗證
        
    try:
        # 計算 HMAC-SHA256
        hash = hmac.new(
            ASSERTION_SIGNING_KEY.encode('utf-8'),
            body.encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        # 轉換為 base64
        calculated_signature = base64.b64encode(hash).decode('utf-8')
        
        # 比較簽名
        return hmac.compare_digest(calculated_signature, signature)
    except Exception as e:
        logging.error(f"驗證簽名時發生錯誤：{str(e)}")
        return False

# === 模擬詐騙分析結果 ===
def analyze_text(text):
    scam_keywords = [
    "怎麼投資", "怎麼給你", "錢怎麼轉", 
    "要匯到哪", "我相信你", "我沒有別人可以相信了"]

    if any(word in text for word in scam_keywords):
        return {
            "label": "scam",
            "confidence": 0.9,
            "reply": "這是我投資成功的故事，你想聽嗎？"
        }
    else:
        return {
            "label": "safe",
            "confidence": 0.1,
            "reply": "哈哈你說得真有趣，我懂你！"
        }

# === 模擬 LLM API 端點 ===
@app.route("/api/analyze", methods=["POST"])
def mock_llm_api():
    try:
        data = request.get_json()
        logging.info(f"收到 API 請求：{json.dumps(data, ensure_ascii=False)}")
        
        # 檢查請求資料
        if not data:
            return jsonify({
                "error": "無效的請求資料"
            }), 400
            
        message_type = data.get("message_type", "text")
        user_id = data.get("user_id", "")
        current_message = data.get("current_message", "")
        image_path = data.get("image_path", "")
        chat_history = data.get("chat_history", [])
        
        # 根據訊息類型生成不同的回應
        if message_type == "image":
            # 模擬圖片分析
            analysis_result = {
                "is_scam": True,
                "confidence": 0.85,
                "details": {
                    "scam_type": "investment_scam",
                    "risk_level": "high",
                    "detected_elements": ["fake_investment", "urgency", "high_returns"],
                    "image_path": image_path,
                    "analysis_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            }
        else:
            # 模擬文字分析
            analysis_result = {
                "is_scam": True,
                "confidence": 0.75,
                "details": {
                    "scam_type": "phishing_scam",
                    "risk_level": "high",
                    "detected_elements": ["suspicious_link", "personal_info_request"],
                    "message": current_message,
                    "analysis_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            }
        
        # 生成回覆訊息
        if analysis_result["is_scam"]:
            reply = f"警告！這可能是詐騙訊息（可信度：{analysis_result['confidence']*100:.1f}%）"
        else:
            reply = "這看起來是安全的訊息。"
            
        response = {
            "status": "success",
            "data": {
                "analysis": analysis_result,
                "reply": reply,
                "user_id": user_id,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }
        
        logging.info(f"API 回應：{json.dumps(response, ensure_ascii=False)}")
        return jsonify(response)
        
    except Exception as e:
        logging.error(f"API 處理錯誤：{str(e)}")
        logging.error(traceback.format_exc())
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

# === 傳送資料到 API 伺服器並接收回覆語句 + 詐騙風險分析 ===
def send_to_api(data):
    try:
        # 使用本地模擬 API
        api_url = "http://localhost:10001/api/analyze"
        headers = {
            "Content-Type": "application/json"
        }
        
        logging.info(f"傳送資料到 API：{json.dumps(data, ensure_ascii=False)}")
        res = requests.post(api_url, headers=headers, data=json.dumps(data), timeout=5)
        
        if res.status_code == 200:
            result = res.json()
            logging.info(f"API 回應：{json.dumps(result, ensure_ascii=False)}")
            return result.get("data", {}).get("analysis", {})
        else:
            logging.error(f"API 回應錯誤：{res.status_code}")
            logging.error(f"錯誤內容：{res.text}")
            return {
                "label": "unknown",
                "confidence": 0.0,
                "reply": "目前系統繁忙，請稍後再試。"
            }
    except Exception as e:
        logging.error(f"傳送 API 發生錯誤：{str(e)}")
        logging.error(traceback.format_exc())
        return {
            "label": "unknown",
            "confidence": 0.0,
            "reply": "目前系統無法使用，請晚點再聊。"
        }

# 回傳生成的詐騙訊息
def generate_reply(result):
    return result.get("reply", "我還想聽更多～")

# 判斷是否需要警示訊息
def should_warn(result):
    return result.get("label") == "scam" and result.get("confidence", 0.0) > 0.7

# 如果需要警示，產生警示內容
def generate_warning(result):
    confidence = result.get("confidence", 0.0)
    return f"[警示] 你可能正被詐騙，請提高警覺（可信度 {confidence * 100:.1f}%）"

# === 獲取使用者基本資料 ===
def get_user_profile(user_id):
    try:
        url = f"https://api.line.me/v2/bot/profile/{user_id}"
        headers = {
            "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}"
        }
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            return res.json()
        else:
            logging.warning(f"取得使用者資料失敗，狀態碼：{res.status_code}")
    except Exception as e:
        logging.error("[get_user_profile 錯誤]")
        logging.error(traceback.format_exc())
    return {}  


# === 整合資料給模型 / API 使用 ===
def prepare_analysis_data(user_id, message):
    profile = get_user_profile(user_id)
    history = user_chat_history.get(user_id, [])
    return {
        "user_id": user_id,
        "display_name": profile.get("displayName", ""),
        "picture_url": profile.get("pictureUrl", ""),
        "language": profile.get("language", ""),
        "current_message": message,
        "chat_history": history
    }

# === 儲存聊天紀錄（記憶體版） ===
user_chat_history = {}  # key: userId, value: list of text messages

# === 圖片處理相關設定 ===
IMAGE_STORAGE_DIR = "scam_images"
os.makedirs(IMAGE_STORAGE_DIR, exist_ok=True)

# === 處理圖片訊息 ===
def handle_image_message(message_id, user_id):
    try:
        # 使用正確的 API 端點
        url = f"https://api-data.line.me/v2/bot/message/{message_id}/content"
        headers = {
            "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}"
        }
        logging.info(f"=== 開始處理圖片 ===")
        logging.info(f"Message ID: {message_id}")
        logging.info(f"User ID: {user_id}")
        logging.info(f"請求 URL: {url}")
        
        # 獲取圖片
        response = requests.get(url, headers=headers, stream=True)
        logging.info(f"回應狀態碼: {response.status_code}")
        
        if response.status_code == 200:
            # 生成唯一的檔案名稱
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{user_id}_{timestamp}_{uuid.uuid4().hex[:8]}.jpg"
            filepath = os.path.join(IMAGE_STORAGE_DIR, filename)
            
            # 確保目錄存在
            os.makedirs(IMAGE_STORAGE_DIR, exist_ok=True)
            
            # 儲存圖片
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            logging.info(f"圖片已成功儲存至：{filepath}")
            file_size = os.path.getsize(filepath)
            logging.info(f"圖片大小: {file_size} bytes")
            
            if file_size > 0:
                return filepath
            else:
                logging.error("下載的圖片檔案大小為 0")
                return None
        else:
            logging.error(f"無法獲取圖片，狀態碼：{response.status_code}")
            logging.error(f"回應內容：{response.text}")
            return None
    except Exception as e:
        logging.error(f"處理圖片時發生錯誤：{str(e)}")
        logging.error(traceback.format_exc())
        return None

# === 分析圖片內容 ===
def analyze_image(image_path):
    try:
        if not os.path.exists(image_path):
            logging.error(f"圖片檔案不存在：{image_path}")
            return None
            
        # 獲取圖片大小
        file_size = os.path.getsize(image_path)
        
        # 根據圖片大小和時間生成不同的模擬結果
        current_hour = datetime.now().hour
        current_minute = datetime.now().minute
        
        # 使用時間和檔案大小來生成不同的結果
        if file_size < 100000:  # 小於 100KB
            scam_type = "low_quality_scam"
            confidence = 0.6
            risk_level = "medium"
            elements = ["blurry_image", "low_resolution"]
        elif current_hour % 2 == 0:  # 偶數小時
            scam_type = "investment_scam"
            confidence = 0.85
            risk_level = "high"
            elements = ["fake_investment", "urgency", "high_returns"]
        else:  # 奇數小時
            scam_type = "phishing_scam"
            confidence = 0.75
            risk_level = "high"
            elements = ["fake_website", "personal_info", "urgency"]
            
        # 根據分鐘數調整可信度
        confidence = min(0.95, confidence + (current_minute / 100))
        
        analysis_result = {
            "is_scam": True,
            "confidence": confidence,
            "details": {
                "scam_type": scam_type,
                "risk_level": risk_level,
                "detected_elements": elements,
                "image_size": file_size,
                "analysis_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }
        
        logging.info(f"圖片分析完成：{image_path}")
        logging.info(f"分析結果：{json.dumps(analysis_result, ensure_ascii=False)}")
        return analysis_result
    except Exception as e:
        logging.error(f"分析圖片時發生錯誤：{str(e)}")
        logging.error(traceback.format_exc())
        return None

# === 生成警示訊息 ===
def generate_image_warning(analysis_result):
    if not analysis_result:
        return "無法分析圖片內容，請提高警覺。"
    
    confidence = analysis_result.get("confidence", 0) * 100
    scam_type = analysis_result.get("details", {}).get("scam_type", "未知類型")
    risk_level = analysis_result.get("details", {}).get("risk_level", "未知")
    elements = analysis_result.get("details", {}).get("detected_elements", [])
    
    # 根據詐騙類型生成不同的警告訊息
    scam_type_messages = {
        "investment_scam": "這可能是投資詐騙，請注意：\n1. 不要相信高報酬承諾\n2. 不要輕易投資不熟悉的項目\n3. 不要提供銀行帳戶資訊",
        "phishing_scam": "這可能是釣魚詐騙，請注意：\n1. 不要點擊可疑連結\n2. 不要輸入個人資料\n3. 不要提供密碼或驗證碼",
        "low_quality_scam": "這可能是低品質詐騙，請注意：\n1. 圖片品質不佳可能是偽造的\n2. 不要相信來源不明的圖片\n3. 請向官方管道求證"
    }
    
    warning_msg = f"""
[警示] 圖片分析結果：
- 詐騙可能性：{confidence:.1f}%
- 詐騙類型：{scam_type}
- 風險等級：{risk_level}
- 檢測到的特徵：{', '.join(elements)}

{scam_type_messages.get(scam_type, "請提高警覺，不要輕易相信可疑訊息。")}

如有疑慮請撥打 165 反詐騙專線
"""
    return warning_msg

# === 清理圖片 ===
def cleanup_image(image_path):
    try:
        if os.path.exists(image_path):
            os.remove(image_path)
            logging.info(f"已刪除圖片：{image_path}")
    except Exception as e:
        logging.error(f"清理圖片時發生錯誤：{str(e)}")

# === 接收來自 LINE 的訊息 ===
@app.route("/callback", methods=["GET", "POST", "OPTIONS"])
def callback():
    logging.info(f"=== 收到新的請求 ===")
    logging.info(f"請求方法：{request.method}")
    logging.info(f"請求標頭：{dict(request.headers)}")
    
    if request.method == "OPTIONS":
        response = Response(status=200)
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
        return response
        
    if request.method == "GET":
        return "OK"
        
    # 驗證請求簽名
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    
    logging.info(f"收到 webhook 請求，簽名：{signature}")
    logging.info(f"請求內容：{body}")
    
    if not verify_signature(body, signature):
        logging.error("請求簽名驗證失敗")
        return Response("OK", status=200)

    try:
        json_data = json.loads(body)
        logging.info("\n==== [Log] 接收到的資料 ====\n" + json.dumps(json_data, ensure_ascii=False, indent=2))

        events = json_data.get("events", [])
        for event in events:
            if event["type"] == "message":
                reply_token = event["replyToken"]
                user_id = event["source"]["userId"]
                
                # 處理文字訊息
                if event["message"]["type"] == "text":
                    user_msg = event["message"]["text"]
                    user_chat_history.setdefault(user_id, []).append(user_msg)
                    analysis_data = prepare_analysis_data(user_id, user_msg)
                    result = analyze_text(user_msg)
                    reply_msg = generate_reply(result)
                    if should_warn(result):
                        reply_msg += "\n" + generate_warning(result)
                    reply_to_user(reply_token, reply_msg)
                
                # 處理圖片訊息
                elif event["message"]["type"] == "image":
                    logging.info("=== 收到圖片訊息 ===")
                    message_id = event["message"]["id"]
                    logging.info(f"圖片訊息 ID: {message_id}")
                    
                    # 1. 接收並儲存圖片
                    image_path = handle_image_message(message_id, user_id)
                    if not image_path:
                        logging.error("無法處理圖片")
                        reply_to_user(reply_token, "無法處理圖片，請稍後再試。")
                        continue
                    
                    try:
                        # 2. 分析圖片
                        analysis_result = analyze_image(image_path)
                        
                        # 3. 生成回覆訊息
                        if analysis_result and analysis_result.get("is_scam"):
                            warning_msg = generate_image_warning(analysis_result)
                            reply_to_user(reply_token, warning_msg)
                        else:
                            reply_to_user(reply_token, "圖片分析完成，未發現明顯詐騙跡象，但仍請保持警覺。")
                        
                    finally:
                        # 4. 清理圖片
                        cleanup_image(image_path)

    except Exception as e:
        logging.error("\n==== [Log] 發生錯誤 ====")
        logging.error(str(e))
        logging.error(traceback.format_exc())
        return Response("OK", status=200)

    return Response("OK", status=200)

# === 回傳訊息給使用者（使用 reply API） ===
def reply_to_user(reply_token, text):
    try:
        url = "https://api.line.me/v2/bot/message/reply"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}"
        }
        payload = {
            "replyToken": reply_token,
            "messages": [
                {
                    "type": "text",
                    "text": text
                }
            ]
        }
        res = requests.post(url, headers=headers, data=json.dumps(payload))
        if res.status_code != 200:
            logging.warning(f"回傳訊息失敗，狀態碼：{res.status_code}, 回傳內容：{res.text}")
    except Exception as e:
        logging.error("[reply_to_user 錯誤]")
        logging.error(traceback.format_exc())


# === 測試首頁 ===
@app.route("/")
def index():
    return "Hello, Scam Bot!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10001)))
