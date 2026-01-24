# 快速開始指南

## 第一步：安裝套件

在專案資料夾中開啟終端機，執行：

```bash
pip install -r requirements.txt
```

## 第二步：設定 Google Sheets API

### 2.1 建立 Google Cloud 專案並啟用 API

1. 前往 [Google Cloud Console](https://console.cloud.google.com/)
2. 建立新專案或選擇現有專案
3. 在左側選單中，選擇「API 和服務」→「程式庫」
4. 搜尋並啟用以下 API：
   - Google Sheets API
   - Google Drive API

### 2.2 建立服務帳戶

1. 在左側選單中，選擇「API 和服務」→「憑證」
2. 點擊「建立憑證」→「服務帳戶」
3. 填寫服務帳戶名稱，點擊「建立並繼續」
4. 角色選擇「編輯者」，點擊「繼續」
5. 點擊「完成」

### 2.3 下載金鑰檔案

1. 在服務帳戶列表中，點擊剛建立的服務帳戶
2. 切換到「金鑰」分頁
3. 點擊「新增金鑰」→「建立新金鑰」
4. 選擇「JSON」格式
5. 下載的 JSON 檔案會包含所有需要的憑證資訊

### 2.4 建立本地 secrets.toml

1. 在專案資料夾中建立 `.streamlit` 資料夾（如果還沒有）
2. 複製 `.streamlit/secrets.toml.example` 為 `.streamlit/secrets.toml`
3. 開啟下載的 JSON 金鑰檔案
4. 將 JSON 內容對應填入 `secrets.toml`：

```toml
[gcp_service_account]
type = "service_account"
project_id = "從 JSON 複製"
private_key_id = "從 JSON 複製"
private_key = "從 JSON 複製（保留換行符號 \n）"
client_email = "從 JSON 複製"
client_id = "從 JSON 複製"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "從 JSON 複製"
```

**重要：** `private_key` 欄位要保留所有的 `\n` 換行符號！

## 第三步：設定 Google Sheets

### 3.1 準備試算表

您的試算表已經存在：
https://docs.google.com/spreadsheets/d/1WuuhxCwgORIJoJ-TLa6isHNjJ7BCuSYKXrW-9JE_Jcc/edit?gid=0#gid=0

確認第一列（標題列）包含以下欄位：

```
id | ticker | entry_date | total_amount | shares | strategy_type | is_sold | notes
```

### 3.2 共用試算表給服務帳戶

1. 開啟您的 Google Sheets
2. 點擊右上角「共用」按鈕
3. 在「新增使用者和群組」中，貼上服務帳戶的 email
   - 這個 email 在 `secrets.toml` 的 `client_email` 欄位
   - 格式類似：`your-service-account@your-project.iam.gserviceaccount.com`
4. 權限設為「編輯者」
5. **取消勾選**「通知使用者」（因為這是機器人帳號）
6. 點擊「共用」

## 第四步：執行應用程式

在終端機中執行：

```bash
streamlit run app.py
```

瀏覽器會自動開啟，網址為 `http://localhost:8501`

## 測試功能

### 測試 1：新增買入記錄

1. 在「新增買入記錄」區塊填寫：
   - 股票代號：2330
   - 股數：1000
   - 總成本：600000
   - 進場日期：選擇今天
   - 策略類型：Basic
   - 備註：測試用
2. 點擊「儲存」
3. 檢查 Google Sheets 是否新增了一筆資料

### 測試 2：查看庫存

1. 等待幾秒讓系統載入資料
2. 在「目前庫存」區塊應該會看到剛才新增的部位
3. 檢查是否顯示：
   - 股票名稱（台積電）
   - 現價
   - 損益
   - 出場價（MA20）
   - 建議（HOLD 或 SELL）

### 測試 3：標記已出場

1. 在「選擇要標記為已出場的部位」下拉選單中選擇測試的股票
2. 點擊「標記已出場並儲存」
3. 該部位應該從庫存列表中消失
4. 檢查 Google Sheets 的 `is_sold` 欄位是否變為 `TRUE`

## 常見問題

### Q1: 出現「找不到 Secrets 設定」錯誤

**解決方法：**
- 確認 `.streamlit/secrets.toml` 檔案存在
- 確認檔案內容格式正確（使用 TOML 格式）
- 確認 `[gcp_service_account]` 標題正確

### Q2: 出現「找不到試算表」錯誤

**解決方法：**
- 確認 `config.py` 中的 `SHEET_URL` 正確
- 確認試算表已共用給服務帳戶 email
- 確認服務帳戶有「編輯者」權限

### Q3: 無法取得股價資料

**解決方法：**
- 確認網路連線正常
- 確認股票代號正確（台股代碼，不含 .TW）
- 嘗試重新整理頁面
- 某些股票可能在 `twstock` 或 `yfinance` 中不存在

### Q4: 計算結果不正確

**解決方法：**
- 確認進場日期格式為 YYYY-MM-DD
- 確認該股票有足夠的歷史資料（至少 20 個交易日）
- 週末或假日可能會影響計算

## 下一步

✅ 系統已經可以使用了！

您可以：
1. 開始記錄真實的股票交易
2. 每天查看出場訊號
3. 根據建議進行交易決策

如需部署到雲端，請參考 `README.md` 中的「部署到 Streamlit Cloud」章節。
