# 超快速開始（使用現有的 service_account.json）

## 只需要 3 步驟！

### 第 1 步：複製 JSON 金鑰檔案

將您現有的 `service_account.json` 複製到 `stock-strategy-app` 資料夾中：

```
stock-strategy-app/
├── service_account.json  ← 複製到這裡
├── app.py
├── backend.py
└── ...
```

**來源檔案位置：**
```
【test】stock-trading-app/service_account.json
```

### 第 2 步：安裝套件

```bash
cd stock-strategy-app
pip install -r requirements.txt
```

### 第 3 步：執行應用程式

```bash
streamlit run app.py
```

就這樣！系統會自動使用 `service_account.json` 連線到 Google Sheets。

---

## 確認事項

✅ **Google Sheets 已共用給服務帳戶**

確認您的試算表已共用給：
```
streamlit-bot@stock-trading-484313.iam.gserviceaccount.com
```

✅ **試算表欄位正確**

第一列應該包含：
```
id | ticker | entry_date | total_amount | shares | strategy_type | is_sold | notes
```

---

## 常見問題

### Q: 我需要設定 secrets.toml 嗎？

**不需要！** 如果您有 `service_account.json` 檔案，系統會自動使用它。

`secrets.toml` 只在以下情況需要：
- 部署到 Streamlit Cloud
- 不想把 JSON 檔案放在專案資料夾中

### Q: service_account.json 會被上傳到 Git 嗎？

**不會！** `.gitignore` 已經設定忽略所有 `.json` 檔案，確保您的金鑰安全。

### Q: 如何確認連線成功？

執行應用程式後，如果沒有出現錯誤訊息，就代表連線成功了！

---

## 下一步

1. 複製 `service_account.json` 到專案資料夾
2. 執行 `pip install -r requirements.txt`
3. 執行 `streamlit run app.py`
4. 開始使用！🎉
