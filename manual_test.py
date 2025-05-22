import requests
import json
import os
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# LINE Bot 設定
CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
LINE_API_URL = "https://api.line.me/v2/bot/message/push"

def send_test_image(user_id, image_path):
    """發送測試圖片到指定的用戶"""
    try:
        # 1. 上傳圖片到 LINE
        upload_url = "https://api.line.me/v2/bot/message/content/upload"
        headers = {
            "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}"
        }
        
        with open(image_path, "rb") as f:
            files = {"file": f}
            response = requests.post(upload_url, headers=headers, files=files)
            
        if response.status_code != 200:
            print(f"上傳圖片失敗：{response.status_code}")
            return False
            
        # 2. 發送圖片訊息
        message_url = "https://api.line.me/v2/bot/message/push"
        payload = {
            "to": user_id,
            "messages": [
                {
                    "type": "image",
                    "originalContentUrl": response.json()["url"],
                    "previewImageUrl": response.json()["url"]
                }
            ]
        }
        
        response = requests.post(message_url, headers=headers, json=payload)
        if response.status_code == 200:
            print("測試圖片發送成功！")
            return True
        else:
            print(f"發送訊息失敗：{response.status_code}")
            return False
            
    except Exception as e:
        print(f"發送測試圖片時發生錯誤：{str(e)}")
        return False

def main():
    # 測試圖片目錄
    test_images_dir = "test_images"
    if not os.path.exists(test_images_dir):
        os.makedirs(test_images_dir)
        print(f"已建立測試圖片目錄：{test_images_dir}")
        print("請將測試用的詐騙圖片放入此目錄")
        return
    
    # 取得所有測試圖片
    test_images = [f for f in os.listdir(test_images_dir) if f.endswith(('.jpg', '.jpeg', '.png'))]
    if not test_images:
        print("測試圖片目錄中沒有圖片")
        return
    
    # 輸入測試用戶 ID
    user_id = input("請輸入要測試的 LINE 用戶 ID：")
    
    # 發送每張測試圖片
    for image_file in test_images:
        image_path = os.path.join(test_images_dir, image_file)
        print(f"\n正在測試圖片：{image_file}")
        if send_test_image(user_id, image_path):
            print("等待 5 秒後繼續下一個測試...")
            import time
            time.sleep(5)
        else:
            print("測試失敗，跳過此圖片")

if __name__ == "__main__":
    main() 