#!/usr/bin/env python3
"""
股價資料更新腳本
每天自動執行，將庫存股票的股價資料寫入 Google Sheets
"""

import os
import gspread
import pandas as pd
from datetime import datetime, timedelta
import twstock
import yfinance as yf
import time

# Google Sheets 設定
SHEET_URL = 'https://docs.google.com/spreadsheets/d/1WuuhxCwgORIJoJ-TLa6isHNjJ7BCuSYKXrW-9JE_Jcc/edit'

def init_connection():
    """初始化 Google Sheets 連線"""
    json_path = os.path.join(os.path.dirname(__file__), 'service_account.json')
    if os.path.exists(json_path):
        return gspread.service_account(filename=json_path)
    raise Exception("找不到 service_account.json")

def get_holdings_tickers():
    """取得所有庫存的股票代號"""
    client = init_connection()
    sh = client.open_by_url(SHEET_URL)
    worksheet = sh.get_worksheet(0)  # 第一個工作表（部位記錄）
    
    data = worksheet.get_all_records()
    
    # 篩選未出場的部位
    tickers = set()
    for row in data:
        is_sold = str(row.get('is_sold', '')).lower() in ('true', '1', 'yes')
        if not is_sold:
            ticker = str(row.get('ticker', '')).strip()
            if ticker:
                tickers.add(ticker)
    
    return list(tickers)

def fetch_stock_data(ticker, days=60):
    """
    從 API 抓取股價資料
    
    Args:
        ticker: 股票代號
        days: 抓取最近幾天的資料
        
    Returns:
        list: 股價資料列表
    """
    clean_ticker = str(ticker).upper().replace(".TW", "").replace(".TWO", "").strip()
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    results = []
    
    # 嘗試使用 twstock
    try:
        if clean_ticker in twstock.codes:
            stock = twstock.Stock(clean_ticker)
            data = stock.fetch_from(start_date.year, start_date.month)
            
            if data:
                for d in data:
                    if d.date >= start_date.date():
                        results.append({
                            '股票代號': clean_ticker,
                            '日期': d.date.strftime('%Y-%m-%d'),
                            '開盤價': d.open,
                            '最高價': d.high,
                            '最低價': d.low,
                            '收盤價': d.close,
                            '成交量': d.capacity
                        })
                
                if results:
                    return results
    except Exception as e:
        print(f"twstock 抓取 {clean_ticker} 失敗: {e}")
    
    # 如果 twstock 失敗，嘗試 yfinance
    try:
        market = twstock.codes[clean_ticker].market if clean_ticker in twstock.codes else "上市"
        suffix = ".TW" if market == "上市" else ".TWO"
        
        stock = yf.Ticker(f"{clean_ticker}{suffix}")
        df = stock.history(start=start_date, end=end_date + timedelta(days=1), auto_adjust=False)
        
        if not df.empty:
            for idx, row in df.iterrows():
                date_str = idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx)[:10]
                results.append({
                    '股票代號': clean_ticker,
                    '日期': date_str,
                    '開盤價': row.get('Open', 0),
                    '最高價': row.get('High', 0),
                    '最低價': row.get('Low', 0),
                    '收盤價': row.get('Close', 0),
                    '成交量': row.get('Volume', 0)
                })
    except Exception as e:
        print(f"yfinance 抓取 {clean_ticker} 失敗: {e}")
    
    return results

def update_prices_to_sheets():
    """主函數：更新所有庫存股票的股價到 Google Sheets"""
    print(f"開始更新股價資料... {datetime.now()}")
    
    # 取得庫存股票
    tickers = get_holdings_tickers()
    print(f"找到 {len(tickers)} 支庫存股票: {tickers}")
    
    if not tickers:
        print("沒有庫存股票需要更新")
        return
    
    # 連線到 Google Sheets
    client = init_connection()
    sh = client.open_by_url(SHEET_URL)
    
    # 取得或建立「股價數據」工作表
    try:
        price_ws = sh.worksheet("股價數據")
    except gspread.WorksheetNotFound:
        price_ws = sh.add_worksheet(title="股價數據", rows=1000, cols=10)
        # 寫入標題
        price_ws.update('A1:G1', [['股票代號', '日期', '開盤價', '最高價', '最低價', '收盤價', '成交量']])
    
    # 讀取現有資料
    existing_data = price_ws.get_all_records()
    existing_keys = set()
    for row in existing_data:
        key = f"{row.get('股票代號', '')}_{row.get('日期', '')}"
        existing_keys.add(key)
    
    # 抓取並更新每支股票
    all_new_data = []
    for ticker in tickers:
        print(f"正在抓取 {ticker}...")
        
        data = fetch_stock_data(ticker, days=60)
        
        # 篩選新資料（避免重複）
        for row in data:
            key = f"{row['股票代號']}_{row['日期']}"
            if key not in existing_keys:
                all_new_data.append([
                    row['股票代號'],
                    row['日期'],
                    row['開盤價'],
                    row['最高價'],
                    row['最低價'],
                    row['收盤價'],
                    row['成交量']
                ])
                existing_keys.add(key)
        
        # 避免 API 限制
        time.sleep(1)
    
    # 批次寫入新資料
    if all_new_data:
        # 找到最後一列
        current_rows = len(existing_data) + 1  # +1 for header
        start_row = current_rows + 1
        end_row = start_row + len(all_new_data) - 1
        
        # 確保工作表有足夠的列
        if end_row > price_ws.row_count:
            price_ws.add_rows(end_row - price_ws.row_count + 100)
        
        # 寫入資料
        cell_range = f'A{start_row}:G{end_row}'
        price_ws.update(cell_range, all_new_data)
        
        print(f"成功新增 {len(all_new_data)} 筆股價資料")
    else:
        print("沒有新的股價資料需要更新")
    
    print(f"股價更新完成！ {datetime.now()}")

if __name__ == "__main__":
    update_prices_to_sheets()
