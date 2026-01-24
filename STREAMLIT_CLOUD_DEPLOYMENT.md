# Streamlit Cloud 部署準備指南

## 概述

本指南說明如何將股票策略交易系統部署到 Streamlit Cloud，讓您可以在任何地方透過網頁存取。

---

## 部署前準備

### 1. 確認檔案結構

確保您的專案包含以下檔案：

```
stock-strategy-app/
├── app.py                      # 主程式
├── backend.py                  # 後端邏輯
├── config.py                   # 設定檔
├── utils.py                    # 工具函數
├── requirements.txt            # 套件相依性
├── update_stock_prices.py      # 股價更新腳本
├── .gitignore                  # Git 忽略檔案
├── README.md                   # 專案說明
└── .streamlit/
    └── secrets.toml.example    # 憑證範本
```

### 2. 準備 GitHub 儲存庫

1. **建立 GitHub 帳號**（如果還沒有）
   - 前往 https://github.com
   - 註冊帳號

2. **建立新儲存庫**
   - 點擊右上角 "+" → "New repository"
   - 名稱：`stock-strategy-app`
   - 設定為 **Private**（重要！）
   - 不要勾選 "Initialize this repository with a README"

3. **上傳專案到 GitHub**
   ```bash
   cd stock-strategy-app
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/stock-strategy-app.git
   git push -u origin main
   ```

---

## Streamlit Cloud 部署步驟

### 步驟 1：註冊 Streamlit Cloud

1. 前往 https://streamlit.io/cloud
2. 點擊 "Sign up" 使用 GitHub 帳號登入
3. 授權 Streamlit 存取您的 GitHub

### 步驟 2：部署應用程式

1. **點擊 "New app"**

2. **選擇儲存庫**
   - Repository: `YOUR_USERNAME/stock-strategy-app`
   - Branch: `main`
   - Main file path: `app.py`

3. **設定 Secrets**（重要！）
   - 點擊 "Advanced settings"
   - 在 "Secrets" 區域貼上您的 `service_account.json` 內容
   - 格式如下：

   ```toml
   [gcp_service_account]
   type = "service_account"
   project_id = "your-project-id"
   private_key_id = "your-private-key-id"
   private_key = "-----BEGIN PRIVATE KEY-----\nYour-Private-Key-Here\n-----END PRIVATE KEY-----\n"
   client_email = "your-service-account@your-project.iam.gserviceaccount.com"
   client_id = "your-client-id"
   auth_uri = "https://accounts.google.com/o/oauth2/auth"
   token_uri = "https://oauth2.googleapis.com/token"
   auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
   client_x509_cert_url = "your-cert-url"
   ```

4. **點擊 "Deploy"**
   - Streamlit Cloud 會自動安裝套件並啟動應用程式
   - 第一次部署需要 2-5 分鐘

### 步驟 3：測試應用程式

1. 部署完成後，您會看到應用程式的 URL
   - 格式：`https://YOUR_USERNAME-stock-strategy-app-main-app-xxxxx.streamlit.app`

2. 開啟 URL 測試功能
   - 新增買入記錄
   - 查看庫存
   - 標記出場

---

## 自動化股價更新（GitHub Actions）

### 為什麼需要？

- Streamlit Cloud 上無法手動執行 `update_stock_prices.py`
- 需要自動化機制每天更新股價資料

### 設定步驟

#### 1. 建立 GitHub Actions 工作流程

在專案中建立 `.github/workflows/update-prices.yml`：

```yaml
name: Update Stock Prices

on:
  schedule:
    # 每天台灣時間下午 2:30 執行（UTC+8 = 06:30 UTC）
    - cron: '30 6 * * 1-5'  # 週一到週五
  workflow_dispatch:  # 允許手動觸發

jobs:
  update:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    
    - name: Create service account file
      run: |
        echo '${{ secrets.GCP_SERVICE_ACCOUNT }}' > service_account.json
    
    - name: Update stock prices
      run: |
        python update_stock_prices.py
    
    - name: Clean up
      run: |
        rm service_account.json
```

#### 2. 設定 GitHub Secrets

1. 前往 GitHub 儲存庫
2. Settings → Secrets and variables → Actions
3. 點擊 "New repository secret"
4. 名稱：`GCP_SERVICE_ACCOUNT`
5. 值：貼上您的 `service_account.json` 完整內容
6. 點擊 "Add secret"

#### 3. 測試自動化

1. 前往 GitHub 儲存庫
2. Actions 頁籤
3. 選擇 "Update Stock Prices"
4. 點擊 "Run workflow" 手動觸發
5. 查看執行結果

---

## 注意事項

### 🔒 安全性

- ✅ **永遠使用 Private 儲存庫**
- ✅ **不要將 `service_account.json` 提交到 Git**
- ✅ **使用 Secrets 管理敏感資訊**
- ✅ **定期更換服務帳戶金鑰**

### 💰 費用

- **Streamlit Cloud**：免費方案
  - 1 個私有應用程式
  - 1 GB RAM
  - 對個人使用足夠

- **GitHub Actions**：免費方案
  - 每月 2,000 分鐘
  - 每天執行一次約使用 5 分鐘/月
  - 完全免費

### ⚡ 效能

- **首次載入**：
  - 如果有執行 `update_stock_prices.py`：快速
  - 如果沒有：會從 API 抓取（較慢）

- **建議**：
  - 每天執行一次股價更新
  - 設定在收盤後（下午 2:30）

---

## 疑難排解

### 問題：部署失敗

**可能原因**：
1. `requirements.txt` 缺少套件
2. Secrets 設定錯誤
3. 程式碼有錯誤

**解決方案**：
1. 檢查 Streamlit Cloud 的 logs
2. 確認 Secrets 格式正確
3. 在本地測試程式碼

### 問題：無法連線到 Google Sheets

**可能原因**：
1. Secrets 設定錯誤
2. 服務帳戶沒有權限

**解決方案**：
1. 重新檢查 Secrets 設定
2. 確認 Google Sheets 已共用給服務帳戶

### 問題：GitHub Actions 執行失敗

**可能原因**：
1. `GCP_SERVICE_ACCOUNT` Secret 未設定
2. 程式碼錯誤

**解決方案**：
1. 檢查 Actions 的 logs
2. 手動執行 `update_stock_prices.py` 測試

---

## 更新應用程式

### 本地修改後更新

```bash
git add .
git commit -m "Update: description of changes"
git push
```

Streamlit Cloud 會自動偵測變更並重新部署。

---

## 下一步

完成部署後，您可以：

1. ✅ 在任何地方透過網頁存取應用程式
2. ✅ 每天自動更新股價資料
3. ✅ 未來可以加入 K 線圖功能
4. ✅ 分享給其他人使用（如果需要）

---

## 參考資源

- [Streamlit Cloud 文件](https://docs.streamlit.io/streamlit-community-cloud)
- [GitHub Actions 文件](https://docs.github.com/en/actions)
- [Google Sheets API 文件](https://developers.google.com/sheets/api)
