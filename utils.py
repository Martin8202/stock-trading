"""
輔助函數模組
"""
from datetime import datetime
import twstock


def format_number(num):
    """
    格式化數字為千分位格式
    
    Args:
        num: 數字
        
    Returns:
        str: 格式化後的字串
    """
    try:
        return f"{num:,.0f}"
    except:
        return str(num)


def format_currency(num):
    """
    格式化貨幣
    
    Args:
        num: 數字
        
    Returns:
        str: 格式化後的字串，帶正負號
    """
    try:
        sign = "+" if num > 0 else ""
        return f"{sign}{num:,.0f}"
    except:
        return str(num)


def format_percentage(num):
    """
    格式化百分比
    
    Args:
        num: 數字
        
    Returns:
        str: 格式化後的字串
    """
    try:
        sign = "+" if num > 0 else ""
        return f"{sign}{num:.2f}%"
    except:
        return str(num)


def get_stock_name(ticker):
    """
    取得股票名稱
    
    Args:
        ticker: 股票代號（可能是字串或數字）
        
    Returns:
        str: 股票名稱，若找不到則返回代號
    """
    try:
        # 確保 ticker 是字串格式
        ticker_str = str(ticker)
        clean_ticker = ticker_str.upper().replace(".TW", "").replace(".TWO", "").strip()
        if clean_ticker in twstock.codes:
            return twstock.codes[clean_ticker].name
        return ticker_str
    except:
        return str(ticker)


def validate_date(date_str):
    """
    驗證日期格式
    
    Args:
        date_str: 日期字串
        
    Returns:
        bool: 是否為有效日期
    """
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except:
        return False


def generate_position_id(ticker, entry_date):
    """
    產生部位唯一 ID
    
    Args:
        ticker: 股票代號
        entry_date: 進場日期
        
    Returns:
        str: 唯一 ID
    """
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    return f"{ticker}_{entry_date}_{timestamp}"


def safe_float(value, default=0.0):
    """
    安全轉換為浮點數
    
    Args:
        value: 要轉換的值
        default: 預設值
        
    Returns:
        float: 轉換後的浮點數
    """
    try:
        return float(value)
    except:
        return default


def safe_int(value, default=0):
    """
    安全轉換為整數
    
    Args:
        value: 要轉換的值
        default: 預設值
        
    Returns:
        int: 轉換後的整數
    """
    try:
        return int(value)
    except:
        return default


def safe_bool(value, default=False):
    """
    安全轉換為布林值
    
    Args:
        value: 要轉換的值
        default: 預設值
        
    Returns:
        bool: 轉換後的布林值
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ('true', '1', 'yes', 't')
    try:
        return bool(value)
    except:
        return default
