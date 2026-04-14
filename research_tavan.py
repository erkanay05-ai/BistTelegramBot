import yfinance as yf
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_bist_tickers():
    # Researching on a broad list (BIST 100 approx)
    tickers = [
        'THYAO', 'ASELS', 'EREGL', 'KCHOL', 'SISE', 'AKBNK', 'GARAN', 'ISCTR', 'YKBNK', 'BIMAS',
        'TUPRS', 'SAHOL', 'HEKTS', 'SASA', 'PETKM', 'TOASO', 'FROTO', 'ARCLK', 'TTKOM', 'TCELL',
        'HALKB', 'VAKBN', 'EKGYO', 'PGSUS', 'ENKAI', 'DOHOL', 'SOKM', 'AEFES', 'MGROS', 'KOZAA',
        'TKFEN', 'GUBRF', 'VESTL', 'KARSN', 'OTKAR', 'ALARK', 'ODAS', 'ZOREN', 'CANTE', 'SMRTG',
        'KONTR', 'YEOTK', 'EUPWR', 'ASTOR', 'CWENE', 'ALFAS', 'BRYAT', 'QUAGR', 'MIATK', 'REEDR'
    ]
    return [t + '.IS' for t in tickers]

def analyze_ticker(ticker, period='5y'):
    logging.info(f"Analyzing {ticker} for the last {period}...")
    try:
        t_obj = yf.Ticker(ticker)
        info = t_obj.info
        
        # Fundamental stats
        sector = info.get('sector', 'N/A')
        pe_ratio = info.get('forwardPE', 'N/A')
        pb_ratio = info.get('priceToBook', 'N/A')
        market_cap = info.get('marketCap', 'N/A')

        df = yf.download(ticker, period=period, interval='1d', progress=False)
        if df.empty or len(df) < 100:
            return None
        
        # Ensure we have a single column for 'Close' and 'Volume'
        # Modern yfinance returns MultiIndex if only one ticker is requested sometimes
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        close_prices = df['Close']
        volumes = df['Volume']
        
        # Calculate daily change
        df['Prev_Close'] = close_prices.shift(1)
        df['Daily_Change'] = (close_prices / df['Prev_Close']) - 1
        
        # Indicators
        df['Vol_SMA20'] = volumes.rolling(window=20).mean()
        df['Vol_Ratio'] = volumes / df['Vol_SMA20']
        
        # RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / loss)))
        
        # Identify Tavan events (Daily change > 9.8%)
        tavan_events = df[df['Daily_Change'] >= 0.098].copy()
        
        if tavan_events.empty:
            return None
            
        patterns = []
        for idx in tavan_events.index:
            # 1. Look at the 10 days BEFORE tavan
            loc = df.index.get_loc(idx)
            if loc < 10 or loc > len(df) - 11: continue
            
            pre_tavan = df.iloc[loc-10:loc]
            post_tavan = df.iloc[loc+1:loc+11] # Next 10 days
            
            # 2. Analyze PRE-patterns
            vol_spike_before = pre_tavan['Vol_Ratio'].max() > 1.5
            rsi_rising = pre_tavan['RSI'].iloc[-1] > pre_tavan['RSI'].iloc[0]
            price_steady = pre_tavan['Daily_Change'].std() < 0.03
            
            # 3. Analyze POST-performance (The Strategy)
            max_gain_5d = ((post_tavan['High'].iloc[:5].max() / float(df.iloc[loc]['Close'])) - 1) * 100
            max_gain_10d = ((post_tavan['High'].max() / float(df.iloc[loc]['Close'])) - 1) * 100
            drawdown_5d = ((post_tavan['Low'].iloc[:5].min() / float(df.iloc[loc]['Close'])) - 1) * 100
            
            patterns.append({
                'Ticker': ticker,
                'Sector': sector,
                'PE': pe_ratio,
                'Date': idx.strftime('%Y-%m-%d'),
                'Max_Gain_5D': round(max_gain_5d, 2),
                'Max_Gain_10D': round(max_gain_10d, 2),
                'Max_DD_5D': round(drawdown_5d, 2),
                'RSI_Entry': round(float(pre_tavan['RSI'].iloc[-1]), 2),
                'Vol_Ratio_Entry': round(float(pre_tavan['Vol_Ratio'].iloc[-1]), 2)
            })
            
        return patterns
    except Exception as e:
        logging.error(f"Error analyzing {ticker}: {e}")
        return None

def main():
    tickers = get_bist_tickers()
    all_patterns = []
    
    # Process only 20 for speed in initial run, or all if needed
    for ticker in tickers:
        p = analyze_ticker(ticker)
        if p:
            all_patterns.extend(p)
    
    if not all_patterns:
        print("Analiz için yeterli veri bulunamadı.")
        return

    results_df = pd.DataFrame(all_patterns)
    
    print("\n" + "="*50)
    print("5 YILLIK TAVAN ANALİZİ ÖZETİ")
    print("="*50)
    print(f"Toplam Tavan Olayı: {len(results_df)}")
    print(f"Sinyal Sonrası Ortalama % Kazan (5 Gün): %{round(results_df['Max_Gain_5D'].mean(), 2)}")
    print(f"Sinyal Sonrası Ortalama % Kazan (10 Gün): %{round(results_df['Max_Gain_10D'].mean(), 2)}")
    print(f"Sinyal Sonrası Ortalama Max Kayıp (5 Gün): %{round(results_df['Max_DD_5D'].mean(), 2)}")
    print("-" * 50)
    print(f"Ortalama Giriş RSI Değeri: {round(results_df['RSI_Entry'].mean(), 2)}")
    
    # Save results
    results_df.to_csv('tavan_analysis_results.csv', index=False)
    print("\nDetaylı analiz 'tavan_analysis_results.csv' dosyasına kaydedildi.")

if __name__ == "__main__":
    main()
