"""
股票策略交易系統 - Streamlit 主程式
"""
import streamlit as st
import pandas as pd
from datetime import datetime

from backend import (
    add_new_position,
    get_holdings_analysis,
    mark_positions_sold,
    get_recent_pnl
)
from config import STRATEGY_TYPES

# ==========================================
# 頁面設定
# ==========================================

st.set_page_config(
    page_title="股票策略交易系統",
    page_icon="📈",
    layout="wide"
)

st.title("📈 股票策略交易系統")
st.markdown("---")

# ==========================================
# 區塊 1：新增買入記錄
# ==========================================

st.header("📝 新增買入記錄")

with st.form("buy_form"):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        ticker = st.text_input(
            "股票代號 *",
            placeholder="例如：2330, 6770",
            help="請輸入台股代號（不含 .TW 或 .TWO）"
        )
        
        shares_input = st.text_input(
            "股數 *",
            value="",
            placeholder="例如：1000",
            help="購買的股數"
        )
    
    with col2:
        total_amount_input = st.text_input(
            "總成本 *",
            value="",
            placeholder="例如：50000",
            help="購買的總成本（新台幣）"
        )
        
        entry_date = st.date_input(
            "進場日期 *",
            value=datetime.now(),
            help="購買日期"
        )
    
    with col3:
        strategy_type = st.selectbox(
            "策略類型 *",
            options=["基礎單", "加碼單"],
            help="基礎單：守月線 | 加碼單：守兩日低"
        )
        
        notes = st.text_area(
            "備註",
            placeholder="選填：任何想記錄的資訊...",
            help="選填欄位"
        )
    
    submitted = st.form_submit_button("💾 儲存", use_container_width=True)
    
    if submitted:
        # 移除千分位逗號並轉換為數字
        try:
            shares = int(shares_input.replace(',', '').replace(' ', ''))
        except:
            shares = 0
        
        try:
            total_amount = float(total_amount_input.replace(',', '').replace(' ', ''))
        except:
            total_amount = 0
        
        # 驗證必填欄位
        if not ticker:
            st.error("❌ 請填寫股票代號")
        elif shares <= 0:
            st.error("❌ 股數必須大於 0")
        elif total_amount <= 0:
            st.error("❌ 總成本必須大於 0")
        else:
            # 驗證股票代號是否有效
            ticker_clean = ticker.strip().upper()
            
            # 檢查是否為有效的台股代號
            import twstock
            if ticker_clean not in twstock.codes:
                st.error(f"❌ 股票代號 '{ticker_clean}' 不存在或無效")
                st.info("💡 請確認股票代號是否正確（例如：2330、6770、0050）")
            else:
                # 顯示股票名稱確認
                stock_name = twstock.codes[ticker_clean].name
                st.info(f"📌 準備儲存：{ticker_clean} {stock_name}")
                
                # 新增部位
                entry_date_str = entry_date.strftime('%Y-%m-%d')
                
                # 轉換策略類型（中文→英文）
                strategy_type_en = "Basic" if strategy_type == "基礎單" else "Add"
                
                with st.spinner("儲存中..."):
                    success = add_new_position(
                        ticker=ticker_clean,
                        shares=shares,
                        total_amount=total_amount,
                        entry_date=entry_date_str,
                        strategy_type=strategy_type_en,
                        notes=notes.strip()
                    )
                
                if success:
                    st.success("✅ 儲存成功！")
                    st.balloons()
                    # 清除快取以重新載入資料
                    st.cache_data.clear()
                else:
                    st.error("❌ 儲存失敗，請檢查錯誤訊息")

st.markdown("---")

# ==========================================
# 區塊 2：目前庫存
# ==========================================

st.header("📊 目前庫存")

# 重新整理按鈕
if st.button("🔄 重新整理", use_container_width=False):
    st.cache_data.clear()
    st.rerun()

with st.spinner("載入庫存資料中..."):
    try:
        holdings_df = get_holdings_analysis()
        
        if holdings_df.empty:
            st.info("⚠️ 目前沒有庫存部位")
        else:
            # 顯示統計資訊
            total_positions = len(holdings_df)
            sell_signals = len(holdings_df[holdings_df['建議'] == 'SELL'])
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("總部位數", total_positions)
            with col2:
                st.metric("建議出場", sell_signals, delta=None if sell_signals == 0 else f"{sell_signals} 筆")
            with col3:
                st.metric("持續持有", total_positions - sell_signals)
            
            # 計算未實現損益總額
            total_unrealized_pnl = 0
            for idx, row in holdings_df.iterrows():
                # 解析損益金額（格式如 "+1,234 (+5.67%)"）
                pl_str = str(row.get('損益(%)', '0'))
                # 取出第一個數字部分（損益金額）
                pl_str = pl_str.split('(')[0].strip()
                pl_str = pl_str.replace(',', '').replace('+', '').strip()
                try:
                    total_unrealized_pnl += float(pl_str)
                except:
                    pass
            
            with col4:
                pnl_color = "normal" if total_unrealized_pnl >= 0 else "inverse"
                st.metric(
                    "未實現損益", 
                    f"NT$ {total_unrealized_pnl:,.0f}",
                    delta=f"{total_unrealized_pnl:+,.0f}",
                    delta_color=pnl_color
                )
            
            st.markdown("---")
            
            # 策略說明
            st.markdown("""
            **📋 策略說明**
            - 🟢 **HOLD** = 持續持有 | 🔴 **SELL** = 建議出場
            - **基礎單 (Basic)**：跌破月線 (MA20) 出場
            - **加碼單 (Add)**：跌破前兩日收盤低點出場
            """)
            
            # 準備整合表格資料
            integrated_data = []
            for idx, row in holdings_df.iterrows():
                # 根據建議設定狀態符號
                status = "🔴 SELL" if row['建議'] == 'SELL' else "🟢 HOLD"
                
                # 合併代號和名稱
                stock_display = f"{row['代號']} {row['名稱']}"
                
                # 轉換策略類型為中文
                strategy_cn = "基礎單" if row['類型'] == "Basic" else "加碼單"
                
                integrated_data.append({
                    '賣出金額': 0,
                    '狀態': status,
                    '損益(%)': row['損益(%)'],
                    '股票': stock_display,
                    '類型': strategy_cn,
                    '出場價': row['出場價'],
                    '現價': row['現價'],
                    '進場日期': row['進場日期'],
                    '購買天數': row['購買天數'],
                    '總成本': row['總成本'],
                    '庫存股數': row['庫存股數'],
                    '備註': row['備註'],
                    '_id': row['id']
                })
            
            integrated_df = pd.DataFrame(integrated_data)
            
            st.caption("💡 輸入賣出金額（大於 0）即可標記為已出場，然後點擊下方按鈕")
            
            # 使用 form 包裹
            with st.form("integrated_form"):
                # 賣出日期選擇
                sell_date = st.date_input(
                    "賣出日期",
                    value=datetime.now(),
                    help="選擇賣出日期"
                )
                edited_df = st.data_editor(
                    integrated_df[['賣出金額', '狀態', '損益(%)', '股票', '類型', 
                                   '出場價', '現價', '進場日期', '購買天數', '總成本', '庫存股數', '備註']],
                    column_config={
                        '賣出金額': st.column_config.NumberColumn(
                            '賣出金額',
                            help='輸入賣出的總金額（新台幣），大於 0 即標記為已出場',
                            min_value=0,
                            format='%d',
                            width='small'
                        ),
                        '狀態': st.column_config.TextColumn('狀態', disabled=True, width='small'),
                        '損益(%)': st.column_config.TextColumn(
                            '損益(%)', 
                            disabled=True, 
                            width='medium',
                            help='計算公式：(收盤價 × 股數) - 成本，不包含手續費'
                        ),
                        '股票': st.column_config.TextColumn('股票', disabled=True, width='medium'),
                        '類型': st.column_config.TextColumn('類型', disabled=True, width='small'),
                        '出場價': st.column_config.TextColumn('出場價', disabled=True, width='small'),
                        '現價': st.column_config.TextColumn('現價', disabled=True, width='small'),
                        '進場日期': st.column_config.TextColumn('進場日期', disabled=True, width='small'),
                        '購買天數': st.column_config.TextColumn('購買天數', disabled=True, width='small'),
                        '總成本': st.column_config.TextColumn('總成本', disabled=True, width='small'),
                        '庫存股數': st.column_config.TextColumn('庫存股數', disabled=True, width='small'),
                        '備註': st.column_config.TextColumn('備註', disabled=True, width='small'),
                    },
                    hide_index=True,
                    use_container_width=True,
                    key='integrated_editor'
                )
                
                # 標記按鈕
                col1, col2 = st.columns([3, 1])
                with col2:
                    submitted = st.form_submit_button("✅ 標記已出場", use_container_width=True, type="primary")
                
                if submitted:
                    # 找出賣出金額 > 0 的部位
                    positions_to_sell = []
                    for idx in range(len(edited_df)):
                        sell_amount = edited_df.iloc[idx]['賣出金額']
                        if sell_amount > 0:
                            positions_to_sell.append(idx)
                    
                    if not positions_to_sell:
                        st.warning("⚠️ 請輸入賣出金額（大於 0）")
                    else:
                        success_count = 0
                        
                        with st.spinner("更新中..."):
                            for idx in positions_to_sell:
                                position_id = integrated_df.iloc[idx]['_id']
                                sell_amount = edited_df.iloc[idx]['賣出金額']
                                
                                # 轉換為 Python int（避免 int64 序列化錯誤）
                                sell_amount = int(sell_amount) if pd.notna(sell_amount) else 0
                                
                                ids = position_id.split('|')
                                sell_amt = sell_amount if sell_amount > 0 else None
                                sell_date_str = sell_date.strftime('%Y-%m-%d')
                                if mark_positions_sold(ids, sell_amount=sell_amt, sell_date=sell_date_str):
                                    success_count += 1
                        
                        if success_count > 0:
                            st.success(f"✅ 已標記 {success_count} 筆部位為已出場")
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error("❌ 更新失敗，請檢查錯誤訊息")
    
    except Exception as e:
        st.error(f"❌ 載入失敗: {e}")
        st.info("💡 請檢查 Google Sheets 連線設定是否正確")

st.markdown("---")

# ==========================================
# 區塊 3：近期損益
# ==========================================

st.header("💰 近期損益")

# 讓使用者選擇顯示天數
col1, col2 = st.columns([1, 3])
with col1:
    days_to_show = st.selectbox(
        "顯示最近幾天",
        options=[3, 7, 14, 30],
        index=0,
        help="選擇要顯示的天數範圍"
    )

with st.spinner("載入近期損益中..."):
    try:
        recent_pnl_df = get_recent_pnl(days=days_to_show)
        
        if recent_pnl_df.empty:
            st.info(f"⚠️ 最近 {days_to_show} 天沒有出場記錄")
        else:
            # 顯示總計
            total_records = len(recent_pnl_df)
            
            # 計算總損益
            total_pnl = 0
            for idx, row in recent_pnl_df.iterrows():
                # 解析損益金額（移除千分位和貨幣符號）
                pnl_str = str(row.get('損益', '0'))
                pnl_str = pnl_str.replace(',', '').replace('$', '').replace('NT', '').strip()
                try:
                    total_pnl += float(pnl_str)
                except:
                    pass
            
            # 顯示統計資訊
            col1, col2 = st.columns(2)
            with col1:
                st.metric("出場筆數", total_records)
            with col2:
                pnl_color = "normal" if total_pnl >= 0 else "inverse"
                st.metric(
                    "總損益", 
                    f"NT$ {total_pnl:,.0f}",
                    delta=f"{total_pnl:+,.0f}",
                    delta_color=pnl_color
                )
            
            st.markdown("---")
            
            # 顯示表格
            st.dataframe(recent_pnl_df, use_container_width=True, hide_index=True)
    
    except Exception as e:
        st.error(f"❌ 載入近期損益失敗: {e}")

# ==========================================
# 頁尾
# ==========================================

st.markdown("---")
st.caption("📊 股票策略交易系統 | 資料來源：Google Sheets | 市場資料：twstock & yfinance")
