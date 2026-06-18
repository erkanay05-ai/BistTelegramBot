import pandas as pd
from ta.momentum import RSIIndicator, StochasticRSIIndicator, AwesomeOscillatorIndicator

def get_rsi(series, period=14):
    return RSIIndicator(close=series, window=period).rsi()

def get_stoch_rsi(series, period=14, smooth_k=3, smooth_d=3):
    stoch = StochasticRSIIndicator(close=series, window=period, smooth1=smooth_k, smooth2=smooth_d)
    return stoch.stochrsi_k() * 100, stoch.stochrsi_d() * 100

def get_roc(series, period=9):
    return series.pct_change(periods=period) * 100

def get_momentum(series, period=10):
    return series - series.shift(period)
