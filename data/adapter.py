import yfinance as yf
import pandas as pd
from data.cache import cache_store

class DataAdapter:
    def __init__(self):
        pass

    def fetch_historical_data(self, ticker, period="1y", interval="1d"):
        if not ticker.endswith(".IS"):
            ticker += ".IS"
            
        cache_key = f"{ticker}_{period}_{interval}"
        cached_data = cache_store.get(cache_key)
        if cached_data is not None:
            return cached_data

        try:
            t = yf.Ticker(ticker)
            df = t.history(period=period, interval=interval)
            if not df.empty:
                cache_store.set(cache_key, df, ttl=300) # cache for 5 minutes
            return df
        except Exception as e:
            print(f"Error fetching data from yfinance for {ticker}: {e}")
            return pd.DataFrame()

data_adapter = DataAdapter()
