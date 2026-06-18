import pandas as pd
from ta.volatility import AverageTrueRange, BollingerBands
from ta.volume import OnBalanceVolumeIndicator

def get_atr(df, window=14):
    atr = AverageTrueRange(high=df['High'], low=df['Low'], close=df['Close'], window=window)
    return atr.average_true_range()

def get_bollinger_bands(series, window=20, dev=2):
    bb = BollingerBands(close=series, window=window, window_dev=dev)
    return bb.bollinger_hband(), bb.bollinger_lband()

def get_obv(series_close, series_volume):
    obv = OnBalanceVolumeIndicator(close=series_close, volume=series_volume)
    return obv.on_balance_volume()

def get_vwap_20(df, window=20):
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
    pv = typical_price * df['Volume']
    rolling_pv = pv.rolling(window=window).sum()
    rolling_vol = df['Volume'].rolling(window=window).sum()
    return (rolling_pv / rolling_vol).fillna(df['Close'])
