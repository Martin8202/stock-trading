"""
後端邏輯模組
包含 Google Sheets 整合與策略計算
"""
import gspread
import pandas as pd
import twstock
import yfinance as yf
from datetime import datetime, timedelta
import streamlit as st
import os
import json
import time

from config import SHEET_URL, MA_PERIOD, LOOKBACK_DAYS
from utils import (
    get_stock_name, 
    safe_float, 
    safe_int, 
    safe_bool,
    generate_position_id,
    format_number,
    format_currency,
    format_percentage
)


# ==========================================
# Google Sheets 連線
# ==========================================

@st.cache_resource
def init_connection():
    """
    初始化 Google Sheets 連線
    支援兩種方式：
    1. 使用 service_account.json 檔案（本地開發）
    2. 使用 Streamlit Secrets（雲端部署）
    
    Returns:
        tuple: (client, error_msg)
    """
    try:
        # 方法 1: 嘗試使用 service_account.json 檔案
        json_path = os.path.join(os.path.dirname(__file__), 'service_account.json')
        if os.path.exists(json_path):
            client = gspread.service_account(filename=json_path)
            return client, None
        
        # 方法 2: 使用 Streamlit Secrets（雲端部署）
        if "gcp_service_account" in st.secrets:
            credentials = dict(st.secrets["gcp_service_account"])
            client = gspread.service_account_from_dict(credentials)
            return client, None
        
        return None, "找不到憑證設定。請確認 service_account.json 檔案存在，或在 Streamlit Cloud 設定 secrets.toml。"
    
    except Exception as e:
        return None, str(e)



def get_worksheet(sheet_name=None):
    """
    取得工作表
    
    Args:
        sheet_name: 工作表名稱（選填，預設為第一個工作表）
    
    Returns:
        worksheet: Google Sheets 工作表物件
    """
    client, error = init_connection()
    if error:
        raise Exception(f"連線失敗: {error}")
    
    sh = client.open_by_url(SHEET_URL)
    
    if sheet_name:
        try:
            return sh.worksheet(sheet_name)
        except:
            # 如果找不到指定的工作表，返回第一個
            return sh.get_worksheet(0)
    else:
        return sh.get_worksheet(0)


def get_price_worksheet():
    """
    取得股價歷史工作表
    
    Returns:
        worksheet: 股價歷史工作表，如果不存在則返回 None
    """
    try:
        return get_worksheet('股價歷史')
    except:
        return None


# ==========================================
# CRUD 操作
# ==========================================

def add_new_position(ticker, shares, total_amount, entry_date, strategy_type, notes=""):
    """
    新增部位到 Google Sheets
    
    Args:
        ticker: 股票代號
        shares: 股數
        total_amount: 總成本
        entry_date: 進場日期
        strategy_type: 策略類型
        notes: 備註
        
    Returns:
        bool: 是否成功
    """
    try:
        worksheet = get_worksheet()
        
        # 產生唯一 ID
        position_id = generate_position_id(ticker, entry_date)
        
        # 準備資料列（新增 sell_amount 和 sell_date 欄位，預設為空）
        row = [
            position_id,
            ticker,
            entry_date,
            total_amount,
            shares,
            strategy_type,
            False,  # is_sold
            notes,
            "",     # sell_amount（空白）
            ""      # sell_date（空白）
        ]
        
        # 新增到試算表
        worksheet.append_row(row)
        return True
    
    except Exception as e:
        st.error(f"新增失敗: {e}")
        return False


def get_all_positions():
    """
    取得所有部位
    
    Returns:
        list: 部位列表
    """
    try:
        worksheet = get_worksheet()
        data = worksheet.get_all_records()
        return data
    
    except Exception as e:
        st.error(f"讀取失敗: {e}")
        return []


def mark_positions_sold(position_ids, sell_amount=None, sell_date=None):
    """
    標記部位為已出場（按比例分配賣出金額）
    
    Args:
        position_ids: 部位 ID 列表
        sell_amount: 總賣出金額（選填，會按股數比例分配）
        sell_date: 賣出日期（選填）
        
    Returns:
        bool: 是否成功
    """
    try:
        worksheet = get_worksheet()
        all_data = worksheet.get_all_records()
        
        # 如果沒有提供賣出日期，使用今天
        if sell_date is None:
            sell_date = datetime.now().strftime('%Y-%m-%d')
        
        # 第一步：計算總股數（用於按比例分配賣出金額）
        total_shares = 0
        positions_to_update = []
        
        for idx, row in enumerate(all_data, start=2):  # 從第 2 列開始（第 1 列是標題）
            if row['id'] in position_ids:
                shares = safe_int(row.get('shares', 0))
                positions_to_update.append({
                    'row_idx': idx,
                    'id': row['id'],
                    'shares': shares
                })
                total_shares += shares
        
        # 第二步：更新每個部位
        for position in positions_to_update:
            # 更新 is_sold 欄位（第 7 欄）
            worksheet.update_cell(position['row_idx'], 7, True)
            
            # 按比例分配賣出金額
            if sell_amount is not None and total_shares > 0:
                # 計算該部位的賣出金額 = 總賣出金額 × (該部位股數 / 總股數)
                proportional_amount = sell_amount * (position['shares'] / total_shares)
                worksheet.update_cell(position['row_idx'], 9, proportional_amount)
            
            # 更新 sell_date 欄位（第 10 欄）
            worksheet.update_cell(position['row_idx'], 10, sell_date)
            
            # 避免 API 限制
            time.sleep(0.3)
        
        return True
    
    except Exception as e:
        st.error(f"更新失敗: {e}")
        return False


# ==========================================
# 市場資料獲取
# ==========================================

@st.cache_data(ttl=300)  # 快取 5 分鐘（300 秒）
def get_price_data_from_sheets():
    """
    從 Google Sheets 讀取所有股價資料（快取版本）
    
    Returns:
        dict: {ticker: DataFrame} 格式的股價資料
    """
    try:
        price_worksheet = get_price_worksheet()
        if not price_worksheet:
            print("[DEBUG] 股價歷史工作表不存在")
            return {}
        
        # 讀取所有資料
        all_data = price_worksheet.get_all_records()
        if not all_data:
            print("[DEBUG] 股價歷史工作表沒有資料")
            return {}
        
        print(f"[DEBUG] 從 Google Sheets 讀取到 {len(all_data)} 筆股價資料")
        
        # 按股票代號分組
        ticker_data = {}
        for row in all_data:
            ticker = str(row.get('股票代號', '')).strip()
            if not ticker:
                continue
            
            if ticker not in ticker_data:
                ticker_data[ticker] = []
            ticker_data[ticker].append(row)
        
        # 轉換為 DataFrame
        result = {}
        for ticker, rows in ticker_data.items():
            df = pd.DataFrame(rows)
            df['Date'] = pd.to_datetime(df['日期'])
            df.set_index('Date', inplace=True)
            df = df.rename(columns={
                '收盤價': 'Close',
                '開盤價': 'Open',
                '最高價': 'High',
                '最低價': 'Low',
                '成交量': 'Volume'
            })
            # 確保數值欄位是數字類型
            for col in ['Close', 'Open', 'High', 'Low', 'Volume']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            df = df.sort_index()
            result[ticker] = df
        
        print(f"[DEBUG] 處理完成，共 {len(result)} 支股票的價格資料")
        return result
    except Exception as e:
        print(f"[DEBUG] 讀取股價歷史失敗: {e}")
        return {}


@st.cache_data(ttl=300)  # 快取 5 分鐘（300 秒）
def get_market_data(ticker, target_date):
    """
    取得市場資料（優先從 Google Sheets 讀取，失敗則從 API 抓取）
    
    Args:
        ticker: 股票代號（可能是字串或數字）
        target_date: 目標日期
        
    Returns:
        DataFrame: 股價資料
    
    Note:
        此函數會快取結果 5 分鐘，避免頻繁呼叫 API
    """
    # 確保 ticker 是字串格式
    ticker_str = str(ticker)
    clean_ticker = ticker_str.upper().replace(".TW", "").replace(".TWO", "").strip()
    
    # 方法 1: 嘗試從快取的 Google Sheets 資料讀取
    cached_prices = get_price_data_from_sheets()
    if clean_ticker in cached_prices:
        df = cached_prices[clean_ticker]
        # 篩選到目標日期為止的資料
        df = df[df.index <= pd.to_datetime(target_date)]
        if not df.empty and len(df) >= 20:
            print(f"[✅ Sheets] {clean_ticker} 從 Google Sheets 讀取，{len(df)} 筆資料")
            return df[['Close', 'Open', 'High', 'Low', 'Volume']] if 'Open' in df.columns else df[['Close']]
        else:
            print(f"[⚠️ Sheets] {clean_ticker} 在 Sheets 中資料不足 ({len(df)} 筆)，改用 API")
    else:
        print(f"[❌ Sheets] {clean_ticker} 不在 Sheets 中，改用 API")
    
    # 方法 2: 從 API 抓取（原本的邏輯）
    final_df = None
    start_date = target_date - timedelta(days=90)
    start_year = start_date.year
    start_month = start_date.month
    
    # 嘗試使用 twstock
    try:
        if clean_ticker in twstock.codes:
            stock = twstock.Stock(clean_ticker)
            target_data = stock.fetch_from(start_year, start_month)
            if target_data:
                data_list = [{"Date": d.date, "Close": d.close} for d in target_data]
                df = pd.DataFrame(data_list)
                df.set_index("Date", inplace=True)
                df.index = pd.to_datetime(df.index)
                if len(df) >= 20:
                    final_df = df
    except:
        pass
    
    # 如果 twstock 失敗，嘗試使用 yfinance
    if final_df is None:
        try:
            market = twstock.codes[clean_ticker].market if clean_ticker in twstock.codes else "上市"
            suffix = ".TW" if market == "上市" else ".TWO"
            stock_obj = yf.Ticker(f"{clean_ticker}{suffix}")
            df = stock_obj.history(
                start=start_date,
                end=target_date + timedelta(days=1),
                auto_adjust=False
            )
            if not df.empty and len(df) >= 20:
                final_df = df
        except:
            pass
    
    if final_df is None:
        return None
    
    # 移除時區資訊
    if final_df.index.tz is not None:
        final_df.index = final_df.index.tz_localize(None)
    
    return final_df


# ==========================================
# 策略分析
# ==========================================

def analyze_portfolio(portfolio, analysis_date_str=None):
    """
    分析投資組合
    
    Args:
        portfolio: 投資組合列表
        analysis_date_str: 分析日期字串
        
    Returns:
        DataFrame: 分析結果
    """
    # 確定目標日期
    if analysis_date_str:
        try:
            target_date = pd.to_datetime(analysis_date_str)
        except:
            target_date = datetime.now()
    else:
        target_date = datetime.now()
    
    if target_date.tzinfo is not None:
        target_date = target_date.tz_localize(None)
    
    # 合併庫存
    aggregated_inventory = {}
    
    for lot in portfolio:
        # 跳過已賣出的部位
        if safe_bool(lot.get('is_sold', False)):
            continue
        
        key = (lot['ticker'], lot['strategy_type'])
        
        if key not in aggregated_inventory:
            stock_name = get_stock_name(lot['ticker'])
            
            aggregated_inventory[key] = {
                "ticker": lot['ticker'],
                "name": stock_name,
                "strategy_type": lot['strategy_type'],
                "total_shares": 0,
                "total_cost": 0,
                "first_entry_date": lot['entry_date'],
                "entry_dates_set": set(),
                "notes": lot.get('notes', ''),
                "ids": []  # 儲存所有相關的 ID
            }
        
        aggregated_inventory[key]["total_shares"] += safe_int(lot['shares'])
        aggregated_inventory[key]["total_cost"] += safe_float(lot['total_amount'])
        aggregated_inventory[key]["entry_dates_set"].add(lot['entry_date'])
        aggregated_inventory[key]["ids"].append(lot['id'])
        
        # 更新最早進場日期
        if lot['entry_date'] < aggregated_inventory[key]["first_entry_date"]:
            aggregated_inventory[key]["first_entry_date"] = lot['entry_date']
        
        # 合併備註
        if lot.get('notes') and lot['notes'] not in aggregated_inventory[key]["notes"]:
            if aggregated_inventory[key]["notes"]:
                aggregated_inventory[key]["notes"] += "; " + lot['notes']
            else:
                aggregated_inventory[key]["notes"] = lot['notes']
    
    # 分析與彙整
    results = []
    data_cache = {}
    
    for position in aggregated_inventory.values():
        ticker = position['ticker']
        
        # 取得市場資料
        if ticker not in data_cache:
            df = get_market_data(ticker, target_date)
            if df is None:
                continue
            
            df_slice = df[df.index <= target_date]
            if df_slice.empty or len(df_slice) < 20:
                continue
            
            current_close = df_slice['Close'].iloc[-1]
            ma20 = df_slice['Close'].rolling(window=MA_PERIOD).mean().iloc[-1]
            prev_2_days_low = df_slice['Close'].iloc[-3:-1].min()
            
            data_cache[ticker] = {
                "close": current_close,
                "ma20": ma20,
                "min_2day": prev_2_days_low
            }
        
        market_data = data_cache[ticker]
        total_cost = position['total_cost']
        total_shares = position['total_shares']
        market_value = market_data['close'] * total_shares
        
        pl_amount = market_value - total_cost
        roi = (pl_amount / total_cost * 100) if total_cost != 0 else 0
        pl_display = f"{format_currency(pl_amount)} ({format_percentage(roi)})"
        
        # 計算停損與建議
        signal = "HOLD"
        reason = ""
        stop_loss_price = 0.0
        
        if position['strategy_type'] == "Basic":
            stop_loss_price = market_data['ma20']
            if market_data['close'] < stop_loss_price:
                signal = "SELL"
                reason = f"跌破月線 ({stop_loss_price:.2f})"
            else:
                reason = f"月線 ({stop_loss_price:.2f}) 之上"
        
        elif position['strategy_type'] == "Add":
            stop_loss_price = market_data['min_2day']
            if market_data['close'] < stop_loss_price:
                signal = "SELL"
                reason = f"跌破前兩日低 ({stop_loss_price:.2f})"
            else:
                reason = f"前兩日低 ({stop_loss_price:.2f}) 之上"
        
        results.append({
            "id": "|".join(position['ids']),  # 合併所有 ID
            "進場日期": position['first_entry_date'],
            "代號": ticker,
            "名稱": position['name'],
            "類型": position['strategy_type'],
            "購買天數": len(position['entry_dates_set']),
            "庫存股數": format_number(total_shares),
            "總成本": format_number(total_cost),
            "現價": format_number(market_value),
            "損益(%)": pl_display,
            "出場價": f"{stop_loss_price:.2f}",
            "建議": signal,
            "原因": reason,
            "備註": position['notes']
        })
    
    return pd.DataFrame(results)


def get_holdings_analysis():
    """
    取得庫存分析
    
    Returns:
        DataFrame: 分析結果
    """
    positions = get_all_positions()
    if not positions:
        return pd.DataFrame()
    
    return analyze_portfolio(positions)


def get_recent_pnl(days=3):
    """
    取得近期損益記錄
    
    Args:
        days: 顯示最近幾天的記錄
        
    Returns:
        DataFrame: 近期損益記錄
    """
    try:
        positions = get_all_positions()
        
        # 篩選已出場的部位
        sold_positions = [p for p in positions if safe_bool(p.get('is_sold', False))]
        
        if not sold_positions:
            return pd.DataFrame()
        
        # 計算截止日期
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        # 篩選近期出場的部位
        recent_sold = []
        for p in sold_positions:
            sell_date = p.get('sell_date', '')
            if sell_date and sell_date >= cutoff_date:
                recent_sold.append(p)
        
        if not recent_sold:
            return pd.DataFrame()
        
        # 整理資料
        results = []
        for p in recent_sold:
            ticker = str(p['ticker'])
            stock_name = get_stock_name(ticker)
            
            total_cost = safe_float(p.get('total_amount', 0))
            sell_amount = safe_float(p.get('sell_amount', 0))
            
            # 計算損益
            if sell_amount > 0:
                pl_amount = sell_amount - total_cost
                roi = (pl_amount / total_cost * 100) if total_cost != 0 else 0
            else:
                pl_amount = 0
                roi = 0
            
            results.append({
                "出場日期": p.get('sell_date', ''),
                "代號": ticker,
                "名稱": stock_name,
                "類型": "基礎單" if p.get('strategy_type', '') == "Basic" else "加碼單",
                "股數": format_number(safe_int(p.get('shares', 0))),
                "買入成本": format_number(total_cost),
                "賣出金額": format_number(sell_amount) if sell_amount > 0 else "-",
                "損益": format_currency(pl_amount),
                "報酬率": format_percentage(roi),
                "備註": p.get('notes', '')
            })
        
        # 按出場日期排序（最新的在前）
        df = pd.DataFrame(results)
        if not df.empty:
            df = df.sort_values('出場日期', ascending=False)
        
        return df
    
    except Exception as e:
        st.error(f"讀取近期損益失敗: {e}")
        return pd.DataFrame()
