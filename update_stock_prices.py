"""
股價資料更新腳本
每日執行以更新所有持倉股票的歷史股價資料到 Google Sheets

使用方式：
    python update_stock_prices.py
"""
import gspread
import pandas as pd
import twstock
import yfinance as yf
from datetime import datetime, timedelta
import os
import time

# ==========================================
# 設定
# ==========================================

SHEET_URL = 'https://docs.google.com/spreadsheets/d/1WuuhxCwgORIJoJ-TLa6isHNjJ7BCuSYKXrW-9JE_Jcc/edit?gid=0#gid=0'
PRICE_SHEET_NAME = '股價歷史'  # 新的工作表名稱
LOOKBACK_DAYS = 90  # 回溯天數

# ==========================================
# Google Sheets 連線
# ==========================================

def init_connection():
    """初始化 Google Sheets 連線"""
    json_path = os.path.join(os.path.dirname(__file__), 'service_account.json')
    if not os.path.exists(json_path):
        raise Exception("找不到 service_account.json 檔案")
    
    client = gspread.service_account(filename=json_path)
    return client


def get_or_create_price_sheet(client):
    """取得或建立股價歷史工作表"""
    sh = client.open_by_url(SHEET_URL)
    
    # 檢查工作表是否存在
    try:
        worksheet = sh.worksheet(PRICE_SHEET_NAME)
        print(f"✅ 找到現有工作表：{PRICE_SHEET_NAME}")
        return worksheet
    except:
        # 建立新工作表
        print(f"📝 建立新工作表：{PRICE_SHEET_NAME}")
        worksheet = sh.add_worksheet(title=PRICE_SHEET_NAME, rows=1000, cols=15)
        
        # 設定標題列
        headers = [
            '日期', '股票代號', '股票名稱', 
            '開盤價', '最高價', '最低價', '收盤價', '成交量',
            'MA5', 'MA10', 'MA20', 'MA60',
            '兩日低', '更新時間'
        ]
        worksheet.append_row(headers)
        print("✅ 工作表建立完成")
        return worksheet


def get_active_tickers(client):
    """取得所有活躍的股票代號（未出場的部位）"""
    sh = client.open_by_url(SHEET_URL)
    # 使用第一個工作表（交易記錄）
    worksheet = sh.get_worksheet(0)
    
    data = worksheet.get_all_records()
    
    # 取得未出場的股票代號（去重）
    active_tickers = set()
    for row in data:
        # 檢查 is_sold 欄位，可能是布林值或字串
        is_sold = row.get('is_sold', False)
        if isinstance(is_sold, str):
            is_sold = is_sold.upper() == 'TRUE'
        
        if not is_sold:
            ticker = str(row['ticker']).strip()
            active_tickers.add(ticker)
    
    return list(active_tickers)


# ==========================================
# 股價資料獲取
# ==========================================

def fetch_stock_data(ticker, days=90):
    """
    獲取股票歷史資料
    
    Args:
        ticker: 股票代號
        days: 回溯天數
        
    Returns:
        DataFrame: 包含 OHLCV 的資料
    """
    ticker_str = str(ticker).upper().strip()
    clean_ticker = ticker_str.replace(".TW", "").replace(".TWO", "")
    
    print(f"  📊 抓取 {clean_ticker} 的資料...", end=" ")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    df = None
    
    # 嘗試使用 twstock
    try:
        if clean_ticker in twstock.codes:
            stock = twstock.Stock(clean_ticker)
            data = stock.fetch_from(start_date.year, start_date.month)
            
            if data:
                records = []
                for d in data:
                    records.append({
                        'Date': d.date,
                        'Open': d.open,
                        'High': d.high,
                        'Low': d.low,
                        'Close': d.close,
                        'Volume': d.capacity
                    })
                
                df = pd.DataFrame(records)
                df['Date'] = pd.to_datetime(df['Date'])
                df.set_index('Date', inplace=True)
                print("✅ (twstock)")
    except Exception as e:
        print(f"⚠️ twstock 失敗: {e}")
    
    # 如果 twstock 失敗，使用 yfinance
    if df is None or df.empty:
        try:
            market = twstock.codes[clean_ticker].market if clean_ticker in twstock.codes else "上市"
            suffix = ".TW" if market == "上市" else ".TWO"
            
            stock_obj = yf.Ticker(f"{clean_ticker}{suffix}")
            df = stock_obj.history(start=start_date, end=end_date, auto_adjust=False)
            
            if not df.empty:
                # 重新命名欄位以符合格式
                df = df.rename(columns={
                    'Open': 'Open',
                    'High': 'High',
                    'Low': 'Low',
                    'Close': 'Close',
                    'Volume': 'Volume'
                })
                print("✅ (yfinance)")
        except Exception as e:
            print(f"❌ yfinance 也失敗: {e}")
            return None
    
    if df is None or df.empty:
        print("❌ 無法獲取資料")
        return None
    
    # 移除時區資訊
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    
    return df


def calculate_indicators(df):
    """
    計算技術指標
    
    Args:
        df: 包含 Close 欄位的 DataFrame
        
    Returns:
        DataFrame: 加入指標後的 DataFrame
    """
    if df is None or df.empty:
        return df
    
    # 計算均線
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA10'] = df['Close'].rolling(window=10).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    
    # 計算兩日低點
    df['Min2Day'] = df['Low'].rolling(window=2).min()
    
    return df


# ==========================================
# 資料寫入 Google Sheets
# ==========================================

def update_price_data(worksheet, ticker, df):
    """
    更新股價資料到 Google Sheets（使用批次操作避免 API 限制）
    
    Args:
        worksheet: Google Sheets 工作表
        ticker: 股票代號
        df: 股價資料 DataFrame
    """
    if df is None or df.empty:
        return
    
    # 取得股票名稱
    ticker_str = str(ticker).upper().strip()
    clean_ticker = ticker_str.replace(".TW", "").replace(".TWO", "")
    
    stock_name = clean_ticker
    if clean_ticker in twstock.codes:
        stock_name = twstock.codes[clean_ticker].name
    
    # 準備資料列
    rows = []
    update_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    for date, row in df.iterrows():
        rows.append([
            date.strftime('%Y-%m-%d'),
            clean_ticker,
            stock_name,
            round(row.get('Open', 0), 2),
            round(row.get('High', 0), 2),
            round(row.get('Low', 0), 2),
            round(row.get('Close', 0), 2),
            int(row.get('Volume', 0)),
            round(row.get('MA5', 0), 2) if pd.notna(row.get('MA5')) else '',
            round(row.get('MA10', 0), 2) if pd.notna(row.get('MA10')) else '',
            round(row.get('MA20', 0), 2) if pd.notna(row.get('MA20')) else '',
            round(row.get('MA60', 0), 2) if pd.notna(row.get('MA60')) else '',
            round(row.get('Min2Day', 0), 2) if pd.notna(row.get('Min2Day')) else '',
            update_time
        ])
    
    # 讀取現有資料
    all_data = worksheet.get_all_values()
    
    if len(all_data) <= 1:
        # 如果只有標題列或空白，直接新增
        worksheet.append_rows(rows)
        print(f"  ✅ 已新增 {len(rows)} 筆資料")
        return
    
    # 找出該股票的資料列索引（從 1 開始，第 1 列是標題）
    header = all_data[0]
    ticker_col_idx = header.index('股票代號') if '股票代號' in header else 1
    
    # 保留非該股票的資料
    rows_to_keep = [all_data[0]]  # 保留標題列
    for row_data in all_data[1:]:
        if len(row_data) > ticker_col_idx:
            if str(row_data[ticker_col_idx]).strip() != clean_ticker:
                rows_to_keep.append(row_data)
    
    # 加入新資料
    rows_to_keep.extend(rows)
    
    # 清空工作表並重新寫入（批次操作）
    worksheet.clear()
    time.sleep(1)  # 避免 API 限制
    
    # 批次寫入所有資料
    worksheet.update('A1', rows_to_keep)
    
    print(f"  ✅ 已更新 {len(rows)} 筆資料")


# ==========================================
# 主程式
# ==========================================

def main():
    """主程式"""
    print("=" * 60)
    print("📈 股價資料更新腳本")
    print("=" * 60)
    print()
    
    try:
        # 連線到 Google Sheets
        print("🔗 連線到 Google Sheets...")
        client = init_connection()
        print("✅ 連線成功")
        print()
        
        # 取得或建立股價歷史工作表
        price_worksheet = get_or_create_price_sheet(client)
        print()
        
        # 取得活躍的股票代號
        print("📋 取得活躍股票清單...")
        tickers = get_active_tickers(client)
        print(f"✅ 找到 {len(tickers)} 支股票：{', '.join(tickers)}")
        print()
        
        # 更新每支股票的資料
        print("📊 開始更新股價資料...")
        print()
        
        for i, ticker in enumerate(tickers, 1):
            print(f"[{i}/{len(tickers)}] 處理 {ticker}")
            
            # 獲取股價資料
            df = fetch_stock_data(ticker, days=LOOKBACK_DAYS)
            
            if df is not None and not df.empty:
                # 計算技術指標
                df = calculate_indicators(df)
                
                # 更新到 Google Sheets
                update_price_data(price_worksheet, ticker, df)
            
            print()
            time.sleep(2)  # 避免 API 限制（增加到 2 秒）
        
        print("=" * 60)
        print("✅ 所有股票資料更新完成！")
        print("=" * 60)
    
    except Exception as e:
        print(f"❌ 發生錯誤: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
