# LINE Bot 詐騙檢測系統

這是一個基於 LINE Messaging API 的詐騙檢測 Bot，可以分析文字和圖片訊息，識別可能的詐騙內容。

## 功能特點

- 文字訊息分析
- 圖片內容檢測
- 詐騙關鍵字識別
- 自動警告訊息

## 安裝說明

1. 安裝 Python 3.8 或更高版本
2. 安裝依賴套件：
   ```bash
   pip install -r requirements.txt
   ```
3. 設定環境變數：
   - 複製 `.env.example` 為 `.env`
   - 填入必要的設定值

## 環境變數設定

在 `.env` 文件中設定以下變數：
```
CHANNEL_ACCESS_TOKEN=你的Channel Access Token
CHANNEL_SECRET=你的Channel Secret
ASSERTION_SIGNING_KEY=你的Assertion Signing Key
PORT=10000
```

## 運行方式

1. 啟動應用程式：
   ```bash
   python app.py
   ```
2. 使用 ngrok 建立公開 URL：
   ```bash
   ngrok http 10000
   ```
3. 在 LINE Official Account Manager 中設定 Webhook URL

## 測試方法

1. 文字訊息測試：
   - 發送包含詐騙關鍵字的訊息
   - 發送一般對話訊息

2. 圖片訊息測試：
   - 發送可疑的投資相關圖片
   - 發送一般圖片

## 專案結構

```
scam-bot/
├── app.py              # 主程式
├── requirements.txt    # 依賴套件列表
├── .env               # 環境變數設定
├── .env.example       # 環境變數範例
└── README.md          # 專案說明文件
```

## 注意事項

- 請確保所有敏感資訊（如 API 金鑰）都存放在 `.env` 文件中
- 不要將 `.env` 文件提交到版本控制系統
- 定期更新依賴套件以確保安全性

## 授權說明

本專案採用 MIT 授權條款
