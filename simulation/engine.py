import pandas as pd
from backtesting import Backtest, Strategy
from ta.momentum import RSIIndicator
from ta.trend import MACD

class StandardStrategy(Strategy):
    rsi_period = 14
    rsi_lower = 35
    rsi_upper = 70
    
    def init(self):
        close_series = pd.Series(self.data.Close)
        self.rsi = self.I(lambda x: RSIIndicator(close=pd.Series(x), window=self.rsi_period).rsi().to_numpy(), self.data.Close)
        macd_obj = MACD(close=close_series)
        self.macd_line = self.I(lambda: macd_obj.macd().to_numpy())
        self.macd_signal = self.I(lambda: macd_obj.macd_signal().to_numpy())

    def next(self):
        rsi_val = self.rsi[-1]
        macd_val = self.macd_line[-1]
        macd_sig = self.macd_signal[-1]
        
        if rsi_val < self.rsi_lower and macd_val > macd_sig:
            if not self.position:
                self.buy()
        elif rsi_val > self.rsi_upper or macd_val < macd_sig:
            if self.position:
                self.position.close()
