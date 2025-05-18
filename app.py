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

# === 傳送資料到 API 伺服器並接收回覆語句 + 詐騙風險分析 ===
def send_to_api(data):
    try:
        api_url = "https://example.com/api/analyze"  # 替換成正式 API URL
        headers = {"Content-Type": "application/json"}
        res = requests.post(api_url, headers=headers, data=json.dumps(data), timeout=5)
        if res.status_code == 200:
            print(res.json())  # 印出回傳內容方便 debug
            return res.json()
        else:
            print(f"API 回應錯誤：{res.status_code}")
            return {"label": "unknown", "confidence": 0.0, "reply": "目前系統繁忙，請稍後再試。"}
    except Exception as e:
        print(f"傳送 API 發生錯誤：{e}")
        return {"label": "unknown", "confidence": 0.0, "reply": "目前系統無法使用，請晚點再聊。"}

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
        # 獲取圖片內容
        url = f"https://api.line.me/v2/bot/message/{message_id}/content"
        headers = {
            "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}"
        }
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            # 生成唯一的檔案名稱
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{user_id}_{timestamp}_{uuid.uuid4().hex[:8]}.jpg"
            filepath = os.path.join(IMAGE_STORAGE_DIR, filename)
            
            # 儲存圖片
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            logging.info(f"圖片已儲存至：{filepath}")
            return filepath
        else:
            logging.error(f"無法獲取圖片，狀態碼：{response.status_code}")
            return None
    except Exception as e:
        logging.error(f"處理圖片時發生錯誤：{str(e)}")
        return None

# === 分析圖片內容 ===
def analyze_image(image_path):
    try:
        # 這裡可以整合你的 LLM 圖片分析邏輯
        # 例如：使用 OpenAI 的 GPT-4 Vision 或其他圖片分析 API
        
        # 模擬分析結果
        analysis_result = {
            "is_scam": True,
            "confidence": 0.85,
            "details": {
                "scam_type": "investment_scam",
                "risk_level": "high",
                "detected_elements": ["fake_investment", "urgency", "high_returns"]
            }
        }
        
        return analysis_result
    except Exception as e:
        logging.error(f"分析圖片時發生錯誤：{str(e)}")
        return None

# === 生成警示訊息 ===
def generate_image_warning(analysis_result):
    if not analysis_result:
        return "無法分析圖片內容，請提高警覺。"
    
    confidence = analysis_result.get("confidence", 0) * 100
    scam_type = analysis_result.get("details", {}).get("scam_type", "未知類型")
    risk_level = analysis_result.get("details", {}).get("risk_level", "未知")
    
    warning_msg = f"""
[警示] 圖片分析結果：
- 詐騙可能性：{confidence:.1f}%
- 詐騙類型：{scam_type}
- 風險等級：{risk_level}

請注意：
1. 不要輕易相信高報酬投資
2. 不要提供個人資料
3. 不要轉帳或匯款
4. 如有疑慮請撥打 165 反詐騙專線
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
    logging.info(f"收到請求：{request.method}")
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
                    message_id = event["message"]["id"]
                    
                    # 1. 接收並儲存圖片
                    image_path = handle_image_message(message_id, user_id)
                    if not image_path:
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
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
