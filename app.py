import streamlit as st
import pandas as pd
import gspread

# --- 設定區 ---
# 這裡填入您的試算表網址 (已從您的測試檔中擷取)
SHEET_URL = 'https://docs.google.com/spreadsheets/d/1WuuhxCwgORIJoJ-TLa6isHNjJ7BCuSYKXrW-9JE_Jcc/edit?gid=0#gid=0'

st.title("📱 我的股票記帳助手 (雲端版)")

# --- 定義連線函數 (使用 Streamlit Secrets) ---
@st.cache_resource
def init_connection():
    try:
        # 1. 從 Streamlit 雲端後台讀取 Secrets
        # 注意：這需要在 Streamlit Cloud 的 "Advanced Settings" -> "Secrets" 中設定
        if "gcp_service_account" not in st.secrets:
            return None, "找不到 Secrets 設定。請確認您已在 Streamlit Cloud 後台貼上 TOML 格式的金鑰。"

        credentials = dict(st.secrets["gcp_service_account"])
        
        # 2. 使用 gspread 進行認證
        client = gspread.service_account_from_dict(credentials)
        return client, None

    except Exception as e:
        return None, str(e)

# --- 主程式邏輯 ---
client, error_msg = init_connection()

if error_msg:
    st.error("❌ 連線失敗")
    st.warning(f"錯誤訊息: {error_msg}")
    st.info("💡 提示：請檢查 Streamlit Cloud 的 Secrets 是否設定正確 (標題必須是 [gcp_service_account])")
else:
    # st.success("✅ 雲端機器人登入成功！") # (測試成功後可以註解掉這行，讓畫面更簡潔)

    try:
        # 3. 開啟 Google 試算表
        sh = client.open_by_url(SHEET_URL)
        
        # 讀取第一張工作表
        worksheet = sh.get_worksheet(0)
        
        # 4. 讀取所有資料並轉為 DataFrame
        data = worksheet.get_all_records()
        
        if not data:
            st.info("⚠️ 目前試算表中沒有資料。")
        else:
            df = pd.DataFrame(data)
            
            st.subheader("📊 目前持倉/交易紀錄")
            # use_container_width=True 讓表格在手機上自動填滿寬度
            st.dataframe(df, use_container_width=True)

    except gspread.exceptions.SpreadsheetNotFound:
        st.error("❌ 找不到試算表")
        st.warning("請確認您是否已將試算表 **「共用 (Share)」** 給 Secrets 中設定的 `client_email`。")
    
    except Exception as e:
        st.error(f"❌ 讀取資料失敗: {e}")