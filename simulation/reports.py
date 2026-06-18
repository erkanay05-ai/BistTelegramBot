import pandas as pd
from backtesting import Backtest
from simulation.engine import StandardStrategy
from data.adapter import data_adapter

def run_simulation(ticker, days=180):
    df = data_adapter.fetch_historical_data(ticker, period=f"{days}d")
    if df.empty or len(df) < 50:
        return None, "Yetersiz veri veya yanlış ticker kodu."
        
    try:
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
        bt = Backtest(df, StandardStrategy, cash=100000, commission=.002, exclusive_orders=True)
        stats = bt.run()
        
        results = {
            "Start": stats['Start'].strftime('%Y-%m-%d') if hasattr(stats['Start'], 'strftime') else str(stats['Start']),
            "End": stats['End'].strftime('%Y-%m-%d') if hasattr(stats['End'], 'strftime') else str(stats['End']),
            "Duration": f"{stats['Duration'].days} Gün" if hasattr(stats['Duration'], 'days') else str(stats['Duration']),
            "Equity_Final": round(float(stats['Equity Final [$]']), 2),
            "Return_Pct": round(float(stats['Return [%]']), 2),
            "Buy_And_Hold_Return": round(float(stats['Buy & Hold Return [%]']), 2),
            "Max_Drawdown_Pct": round(float(stats['Max. Drawdown [%]']), 2),
            "Sharpe_Ratio": round(float(stats['Sharpe Ratio']), 2) if not pd.isna(stats['Sharpe Ratio']) else 0.0,
            "Trades_Count": int(stats['# Trades']),
            "Win_Rate_Pct": round(float(stats['Win Rate [%]']), 2) if not pd.isna(stats['Win Rate [%]']) else 0.0
        }
        return results, None
    except Exception as e:
        return None, f"Backtest simülasyon hatası: {str(e)}"
