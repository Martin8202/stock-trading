# 設定檔

# Google Sheets 網址
SHEET_URL = 'https://docs.google.com/spreadsheets/d/1WuuhxCwgORIJoJ-TLa6isHNjJ7BCuSYKXrW-9JE_Jcc/edit?gid=0#gid=0'

# 策略參數
MA_PERIOD = 20  # 均線週期
LOOKBACK_DAYS = 2  # 加碼單回看天數

# Google Sheets 欄位對應
SHEET_COLUMNS = {
    'id': 'id',
    'ticker': 'ticker',
    'entry_date': 'entry_date',
    'total_amount': 'total_amount',
    'shares': 'shares',
    'strategy_type': 'strategy_type',
    'is_sold': 'is_sold',
    'notes': 'notes',
    'sell_amount': 'sell_amount',  # 賣出金額
    'sell_date': 'sell_date'  # 賣出日期
}

# 策略類型
STRATEGY_TYPES = {
    'BASIC': 'Basic',
    'ADD': 'Add'
}
