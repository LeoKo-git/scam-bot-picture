import unittest
import os
import json
import requests
from app import app, handle_image_message, analyze_image, generate_image_warning, cleanup_image
import tempfile
from datetime import datetime

class TestScamBot(unittest.TestCase):
    def setUp(self):
        # 設定測試環境
        self.app = app.test_client()
        self.test_image_dir = "test_images"
        os.makedirs(self.test_image_dir, exist_ok=True)
        
        # 模擬 LINE 的測試圖片
        self.test_image_path = os.path.join(self.test_image_dir, "test_scam.jpg")
        with open(self.test_image_path, "wb") as f:
            f.write(b"fake image content")

    def tearDown(self):
        # 清理測試檔案
        if os.path.exists(self.test_image_path):
            os.remove(self.test_image_path)
        if os.path.exists(self.test_image_dir):
            os.rmdir(self.test_image_dir)

    def test_handle_image_message(self):
        """測試圖片處理功能"""
        # 模擬 LINE 的圖片 ID
        test_message_id = "test_message_id"
        test_user_id = "test_user_id"
        
        # 測試圖片處理
        result = handle_image_message(test_message_id, test_user_id)
        self.assertIsNotNone(result)
        self.assertTrue(os.path.exists(result))
        
        # 清理測試檔案
        if result and os.path.exists(result):
            os.remove(result)

    def test_analyze_image(self):
        """測試圖片分析功能"""
        # 使用測試圖片
        result = analyze_image(self.test_image_path)
        
        # 驗證分析結果格式
        self.assertIsNotNone(result)
        self.assertIn("is_scam", result)
        self.assertIn("confidence", result)
        self.assertIn("details", result)
        
        # 驗證詳細資訊
        details = result["details"]
        self.assertIn("scam_type", details)
        self.assertIn("risk_level", details)
        self.assertIn("detected_elements", details)

    def test_generate_warning(self):
        """測試警示訊息生成"""
        # 模擬分析結果
        test_result = {
            "is_scam": True,
            "confidence": 0.85,
            "details": {
                "scam_type": "investment_scam",
                "risk_level": "high",
                "detected_elements": ["fake_investment", "urgency", "high_returns"]
            }
        }
        
        # 生成警示訊息
        warning = generate_image_warning(test_result)
        
        # 驗證警示訊息內容
        self.assertIn("詐騙可能性", warning)
        self.assertIn("詐騙類型", warning)
        self.assertIn("風險等級", warning)
        self.assertIn("165", warning)  # 確認包含反詐騙專線

    def test_cleanup_image(self):
        """測試圖片清理功能"""
        # 建立測試圖片
        test_path = os.path.join(self.test_image_dir, "test_cleanup.jpg")
        with open(test_path, "wb") as f:
            f.write(b"test content")
        
        # 測試清理功能
        cleanup_image(test_path)
        
        # 確認圖片已被刪除
        self.assertFalse(os.path.exists(test_path))

    def test_callback_endpoint(self):
        """測試 LINE webhook 端點"""
        # 模擬 LINE 的 webhook 請求
        test_data = {
            "events": [
                {
                    "type": "message",
                    "message": {
                        "type": "image",
                        "id": "test_image_id"
                    },
                    "source": {
                        "userId": "test_user_id"
                    },
                    "replyToken": "test_reply_token"
                }
            ]
        }
        
        # 發送測試請求
        response = self.app.post(
            "/callback",
            data=json.dumps(test_data),
            content_type="application/json"
        )
        
        # 驗證回應
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.decode(), "OK")

if __name__ == "__main__":
    unittest.main() 