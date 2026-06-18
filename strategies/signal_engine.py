import pandas as pd
from indicators.trend import get_ema, get_macd_data
from indicators.momentum import get_rsi
from strategies.risk_management import get_risk_reward_params

def generate_signal(df):
    """
    Generates trading signals based on standardized indicators.
    """
    if len(df) < 50:
        return {"Signal": "Nötr", "Score": 0, "Risk": "Nötr"}

    close = df['Close']
    volume = df['Volume']

    # Indicators
    rsi_series = get_rsi(close)
    ema50_series = get_ema(close, 50)
    macd_line, macd_signal = get_macd_data(close)
    avg_vol = volume.rolling(window=20).mean()

    # Current values
    c_price = float(close.iloc[-1])
    c_rsi = float(rsi_series.iloc[-1])
    c_ema50 = float(ema50_series.iloc[-1])
    c_macd = float(macd_line.iloc[-1])
    c_macd_sig = float(macd_signal.iloc[-1])
    c_vol = float(volume.iloc[-1])
    c_avg_vol = float(avg_vol.iloc[-1])

    # Conditions
    bullish_macd = c_macd > c_macd_sig
    bearish_macd = c_macd < c_macd_sig

    # Buy Signal: RSI < 30 (or close), MACD bullish, Price > EMA50, Volume > Avg
    if c_rsi < 40 and bullish_macd and c_price > c_ema50 and c_vol > c_avg_vol * 1.05:
        score = 80 if c_rsi < 30 else 65
        stop, tp, rr = get_risk_reward_params(c_price, stop_loss_pct=7.0, target_pct=14.0)
        return {
            "Signal": "Al",
            "Score": score,
            "Risk": "Orta",
            "Stop": stop,
            "TP": tp,
            "RR": rr
        }

    # Sell Signal: RSI > 70, MACD bearish, Price < EMA50
    elif c_rsi > 70 and bearish_macd and c_price < c_ema50:
        return {
            "Signal": "Sat",
            "Score": 85,
            "Risk": "Yüksek",
            "Stop": round(c_price * 1.05, 2),
            "TP": round(c_price * 0.90, 2),
            "RR": 2.0
        }

    return {"Signal": "Nötr", "Score": 50, "Risk": "Düşük"}
