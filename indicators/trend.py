import pandas as pd
from ta.trend import SMAIndicator, EMAIndicator, MACD

def get_sma(series, window):
    return SMAIndicator(close=series, window=window).sma()

def get_ema(series, window):
    return EMAIndicator(close=series, window=window).ema()

def get_macd_data(series, fast=12, slow=26, sign=9):
    macd = MACD(close=series, window_fast=fast, window_slow=slow, window_sign=sign)
    return macd.macd(), macd.macd_signal()
