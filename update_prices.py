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
import urllib3

# 禁用 SSL 警告（因為證交所證書在某些環境有問題）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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

def fetch_from_twse(ticker, year, month, max_retries=3):
    """
    直接從證交所 API 抓取股價資料（繞過 twstock 的解析問題）
    
    Args:
        ticker: 股票代號
        year: 年份
        month: 月份
        max_retries: 最大重試次數
        
    Returns:
        list: 股價資料列表
    """
    import requests
    
    results = []
    
    # 證交所 API URL
    date_str = f"{year}{month:02d}01"
    url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={date_str}&stockNo={ticker}"
    
    # 添加瀏覽器 User-Agent 以避免被封鎖
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    # 重試邏輯
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=15, verify=False)
            
            # 檢查 HTTP 狀態碼
            if response.status_code != 200:
                print(f"  API 返回 HTTP {response.status_code}，重試中... ({attempt + 1}/{max_retries})")
                time.sleep(2 ** attempt)  # 指數退避
                continue
            
            data = response.json()
            
            if data.get('stat') == 'OK' and data.get('data'):
                for row in data['data']:
                    # row 格式: [日期, 成交股數, 成交金額, 開盤價, 最高價, 最低價, 收盤價, 漲跌價差, 成交筆數]
                    try:
                        # 解析民國年日期 (例如: "114/01/27")
                        date_parts = row[0].split('/')
                        tw_year = int(date_parts[0])
                        gregorian_year = tw_year + 1911
                        date_formatted = f"{gregorian_year}-{date_parts[1]}-{date_parts[2]}"
                        
                        # 解析價格（移除逗號）
                        open_price = float(row[3].replace(',', '')) if row[3] != '--' else 0
                        high_price = float(row[4].replace(',', '')) if row[4] != '--' else 0
                        low_price = float(row[5].replace(',', '')) if row[5] != '--' else 0
                        close_price = float(row[6].replace(',', '')) if row[6] != '--' else 0
                        volume = int(row[1].replace(',', '')) if row[1] != '--' else 0
                        
                        results.append({
                            '股票代號': ticker,
                            '日期': date_formatted,
                            '開盤價': open_price,
                            '最高價': high_price,
                            '最低價': low_price,
                            '收盤價': close_price,
                            '成交量': volume
                        })
                    except (ValueError, IndexError) as e:
                        continue
                
                # 成功抓取，跳出重試迴圈
                break
            else:
                # API 回應不是 OK，可能是查無資料或其他錯誤
                if attempt < max_retries - 1:
                    print(f"  API 回應異常 (stat={data.get('stat')})，重試中... ({attempt + 1}/{max_retries})")
                    time.sleep(2 ** attempt)
                    
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"  TWSE API 抓取 {ticker} 失敗 (嘗試 {attempt + 1}/{max_retries}): {e}")
                time.sleep(2 ** attempt)  # 指數退避：1s, 2s, 4s
            else:
                print(f"  TWSE API 抓取 {ticker} 最終失敗: {e}")
    
    return results


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
    
    # 方法 1: 直接呼叫證交所 API（優先）
    try:
        # 抓取需要的月份
        current_year = start_date.year
        current_month = start_date.month
        end_year = end_date.year
        end_month = end_date.month
        
        while (current_year, current_month) <= (end_year, end_month):
            month_data = fetch_from_twse(clean_ticker, current_year, current_month)
            
            # 篩選日期範圍內的資料
            for row in month_data:
                row_date = datetime.strptime(row['日期'], '%Y-%m-%d').date()
                if start_date.date() <= row_date <= end_date.date():
                    results.append(row)
            
            # 下一個月
            if current_month == 12:
                current_year += 1
                current_month = 1
            else:
                current_month += 1
            
            # 避免 API 限制（增加延遲以防被封鎖）
            time.sleep(3)
        
        if results:
            print(f"  ✓ TWSE API 成功抓取 {clean_ticker}: {len(results)} 筆")
            return results
            
    except Exception as e:
        print(f"TWSE API 抓取 {clean_ticker} 失敗: {e}")
    
    # 方法 2: 如果證交所 API 失敗，嘗試 yfinance（備援）
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
            print(f"  ✓ yfinance 成功抓取 {clean_ticker}: {len(results)} 筆")
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
    
    # 取得或建立「股價歷史」工作表
    # 欄位：日期, 股票代號, 股票名稱, 開盤價, 最高價, 最低價, 收盤價, 成交量, MA5, MA10, MA20, MA60, 兩日低, 更新時間
    try:
        price_ws = sh.worksheet("股價歷史")
    except gspread.WorksheetNotFound:
        price_ws = sh.add_worksheet(title="股價歷史", rows=5000, cols=15)
        # 寫入標題
        headers = ['日期', '股票代號', '股票名稱', '開盤價', '最高價', '最低價', '收盤價', '成交量', 'MA5', 'MA10', 'MA20', 'MA60', '兩日低', '更新時間']
        price_ws.update('A1:N1', [headers])
    
    # 讀取現有資料
    existing_data = price_ws.get_all_records()
    existing_keys = set()
    for row in existing_data:
        key = f"{row.get('股票代號', '')}_{row.get('日期', '')}"
        existing_keys.add(key)
    
    print(f"[DEBUG] Google Sheets 中現有資料筆數: {len(existing_data)}")
    print(f"[DEBUG] 唯一的 (股票代號_日期) 組合數: {len(existing_keys)}")
    
    # 取得股票名稱對照表
    def get_stock_name(ticker):
        try:
            if ticker in twstock.codes:
                return twstock.codes[ticker].name
            return ticker
        except:
            return ticker
    
    # 抓取並更新每支股票
    all_new_data = []
    update_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    for ticker in tickers:
        print(f"正在抓取 {ticker}...")
        
        data = fetch_stock_data(ticker, days=70)  # 多抓幾天以計算 MA60
        
        if not data:
            print(f"  ⚠ {ticker} 無法取得資料")
            continue
        
        print(f"  [DEBUG] {ticker} 抓取到 {len(data)} 筆資料")
        if data:
            print(f"  [DEBUG] 日期範圍: {data[0]['日期']} ~ {data[-1]['日期']}")
        
        # 將資料按日期排序
        data_sorted = sorted(data, key=lambda x: x['日期'])
        
        # 計算 MA 和兩日低
        closes = [row['收盤價'] for row in data_sorted]
        stock_name = get_stock_name(ticker)
        
        new_count_for_ticker = 0
        for i, row in enumerate(data_sorted):
            key = f"{row['股票代號']}_{row['日期']}"
            if key in existing_keys:
                continue  # 跳過已存在的資料
            
            new_count_for_ticker += 1
            
            # 計算 MA 值
            ma5 = sum(closes[max(0, i-4):i+1]) / min(5, i+1) if i >= 0 else 0
            ma10 = sum(closes[max(0, i-9):i+1]) / min(10, i+1) if i >= 0 else 0
            ma20 = sum(closes[max(0, i-19):i+1]) / min(20, i+1) if i >= 0 else 0
            ma60 = sum(closes[max(0, i-59):i+1]) / min(60, i+1) if i >= 0 else 0
            
            # 計算兩日低（今天和昨天的收盤價最低點）
            if i >= 1:
                two_day_low = min(closes[i], closes[i-1])  # 今天和昨天
            else:
                two_day_low = closes[i]  # 第一天沒有昨天，用今天
            
            # 按照原本的欄位順序：日期, 股票代號, 股票名稱, 開盤價, 最高價, 最低價, 收盤價, 成交量, MA5, MA10, MA20, MA60, 兩日低, 更新時間
            all_new_data.append([
                row['日期'],
                row['股票代號'],
                stock_name,
                row['開盤價'],
                row['最高價'],
                row['最低價'],
                row['收盤價'],
                row['成交量'],
                round(ma5, 2),
                round(ma10, 2),
                round(ma20, 2),
                round(ma60, 2),
                round(two_day_low, 2),
                update_time
            ])
            existing_keys.add(key)
        
        print(f"  [DEBUG] {ticker} 有 {new_count_for_ticker} 筆新資料將被寫入")
        
        # 避免 API 限制（增加延遲以防被封鎖）
        time.sleep(3)
    
    # 批次寫入新資料
    if all_new_data:
        # 找到最後一列
        current_rows = len(existing_data) + 1  # +1 for header
        start_row = current_rows + 1
        end_row = start_row + len(all_new_data) - 1
        
        # 確保工作表有足夠的列
        if end_row > price_ws.row_count:
            price_ws.add_rows(end_row - price_ws.row_count + 100)
        
        # 寫入資料（14 個欄位）
        cell_range = f'A{start_row}:N{end_row}'
        price_ws.update(cell_range, all_new_data)
        
        print(f"成功新增 {len(all_new_data)} 筆股價資料")
    else:
        print("沒有新的股價資料需要更新")
    
    print(f"股價更新完成！ {datetime.now()}")

if __name__ == "__main__":
    update_prices_to_sheets()
