import pandas as pd
import numpy as np
import yfinance as yf
from backtesting import Backtest, Strategy
from ta.momentum import RSIIndicator
from ta.trend import MACD

class RSIMACDStrategy(Strategy):
    # Optimizable parameters
    rsi_period = 14
    rsi_lower = 35
    rsi_upper = 70
    macd_fast = 12
    macd_slow = 26
    macd_sign = 9

    def init(self):
        # Calculate indicators
        close_series = pd.Series(self.data.Close)
        
        self.rsi = self.I(lambda x: RSIIndicator(close=pd.Series(x), window=self.rsi_period).rsi().to_numpy(), self.data.Close)
        
        # MACD
        macd_obj = MACD(close=close_series, window_fast=self.macd_fast, window_slow=self.macd_slow, window_sign=self.macd_sign)
        self.macd_line = self.I(lambda: macd_obj.macd().to_numpy())
        self.macd_signal = self.I(lambda: macd_obj.macd_signal().to_numpy())

    def next(self):
        # Trading logic
        rsi_val = self.rsi[-1]
        macd_val = self.macd_line[-1]
        macd_sig = self.macd_signal[-1]
        
        # Buy condition: RSI is low (oversold) and MACD crosses above signal line
        if rsi_val < self.rsi_lower and macd_val > macd_sig:
            if not self.position:
                self.buy()
        
        # Sell condition: RSI is high (overbought) or MACD crosses below signal line
        elif rsi_val > self.rsi_upper or macd_val < macd_sig:
            if self.position:
                self.position.close()

def run_backtest(ticker, days=180):
    """
    Delegates to the modularized simulation package.
    """
    from simulation.reports import run_simulation
    return run_simulation(ticker, days=days)
