# 股票策略交易系統

基於技術分析策略的股票交易管理系統，使用 Google Sheets 作為資料庫。

## 功能特色

- 📝 **買入記錄**：快速記錄股票購買資訊
- 📊 **庫存管理**：即時顯示持倉狀態與損益
- 🎯 **出場訊號**：自動計算停損點與交易建議
- 📱 **行動友善**：支援手機瀏覽器操作
- ☁️ **雲端同步**：資料儲存在 Google Sheets

## 策略說明

### 基礎單 (Basic)
- **停損條件**：跌破 20 日均線 (MA20)
- **適用情境**：長期持有部位

### 加碼單 (Add)
- **停損條件**：跌破前兩日最低價
- **適用情境**：短線加碼部位

## 安裝步驟

### 1. 安裝相依套件

```bash
pip install -r requirements.txt
```

### 2. 設定 Google Sheets API

#### 2.1 建立 Google Cloud 專案

1. 前往 [Google Cloud Console](https://console.cloud.google.com/)
2. 建立新專案
3. 啟用 Google Sheets API 和 Google Drive API

#### 2.2 建立服務帳戶

1. 在 Google Cloud Console 中，前往「IAM 與管理」→「服務帳戶」
2. 建立服務帳戶
3. 下載 JSON 金鑰檔案

#### 2.3 設定本地 Secrets

建立 `.streamlit/secrets.toml` 檔案：

```toml
[gcp_service_account]
type = "service_account"
project_id = "your-project-id"
private_key_id = "your-private-key-id"
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "your-service-account@your-project.iam.gserviceaccount.com"
client_id = "your-client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "your-cert-url"
```

### 3. 設定 Google Sheets

#### 3.1 建立試算表

在您的 Google Sheets 中建立以下欄位（第一列為標題）：

| id | ticker | entry_date | total_amount | shares | strategy_type | is_sold | notes |
|----|--------|------------|--------------|--------|---------------|---------|-------|

#### 3.2 共用試算表

將試算表共用給服務帳戶的 email（在 `secrets.toml` 中的 `client_email`），權限設為「編輯者」。

#### 3.3 更新設定檔

在 `config.py` 中更新您的試算表網址：

```python
SHEET_URL = 'https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit'
```

## 執行應用程式

### 本地執行

```bash
streamlit run app.py
```

應用程式會在瀏覽器中開啟，預設網址為 `http://localhost:8501`

### 部署到 Streamlit Cloud

1. 將程式碼推送到 GitHub
2. 前往 [Streamlit Cloud](https://streamlit.io/cloud)
3. 連結 GitHub 儲存庫
4. 在 Advanced Settings → Secrets 中貼上 `secrets.toml` 的內容
5. 部署！

## 使用說明

### 新增買入記錄

1. 在「📝 新增買入記錄」區塊填寫資料：
   - 股票代號（例如：2330、6770）
   - 股數
   - 總成本
   - 進場日期
   - 策略類型（基礎單/加碼單）
   - 備註（選填）
2. 點擊「💾 儲存」按鈕

### 查看庫存與出場訊號

- 「📊 目前庫存」區塊會顯示所有未出場的部位
- 🟢 綠色標示：建議持有 (HOLD)
- 🔴 紅色標示：建議出場 (SELL)
- 查看「出場價」欄位了解停損點

### 標記已出場

1. 勾選要出場的部位
2. 點擊「✅ 標記已出場並儲存」按鈕
3. 該部位會從庫存列表中移除

## 檔案結構

```
stock-strategy-app/
├── app.py                    # Streamlit 主程式
├── backend.py                # 後端邏輯與 Google Sheets 整合
├── config.py                 # 設定檔
├── utils.py                  # 輔助函數
├── requirements.txt          # Python 套件相依性
├── README.md                 # 說明文件
├── .streamlit/
│   └── secrets.toml.example  # Secrets 範例檔案
└── .gitignore                # Git 忽略檔案
```

## 注意事項

⚠️ **資料安全**
- 請勿將 `secrets.toml` 或服務帳戶金鑰上傳到 GitHub
- `.gitignore` 已設定忽略敏感檔案

⚠️ **API 限制**
- `twstock` 和 `yfinance` 可能有速率限制
- 建議不要過於頻繁重新整理頁面

⚠️ **資料格式**
- 日期格式必須為 YYYY-MM-DD
- 股票代號請使用台股代碼（不含 .TW 或 .TWO）

## 疑難排解

### 無法連線到 Google Sheets

1. 確認服務帳戶金鑰設定正確
2. 確認試算表已共用給服務帳戶 email
3. 確認 Google Sheets API 和 Google Drive API 已啟用

### 無法取得股價資料

1. 確認股票代號正確
2. 檢查網路連線
3. 確認該股票在 `twstock` 或 `yfinance` 中存在

### 計算結果異常

1. 確認進場日期格式正確
2. 確認該股票有足夠的歷史資料（至少 20 個交易日）

## 授權

此專案僅供個人使用，請勿用於商業用途。
