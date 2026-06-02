import yfinance as yf
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

def get_bist_tickers():
    tickers = [
        'THYAO', 'ASELS', 'EREGL', 'KCHOL', 'SISE', 'AKBNK', 'GARAN', 'ISCTR', 'YKBNK', 'BIMAS',
        'TUPRS', 'SAHOL', 'HEKTS', 'SASA', 'PETKM', 'TOASO', 'FROTO', 'ARCLK', 'TTKOM', 'TCELL',
        'HALKB', 'VAKBN', 'EKGYO', 'PGSUS', 'ENKAI', 'DOHOL', 'SOKM', 'AEFES', 'MGROS', 
        'TKFEN', 'GUBRF', 'VESTL', 'KARSN', 'OTKAR', 'ALARK', 'ODAS', 'ZOREN', 'CANTE', 'SMRTG',
        'KONTR', 'YEOTK', 'EUPWR', 'ASTOR', 'CWENE', 'ALFAS', 'BRYAT', 'QUAGR', 'MIATK', 'REEDR',
        'BTCIM', 'TMSN', 'SDTTR', 'AGROT', 'KOPOL', 'EBEBK', 'VAKKO', 'IZFAS', 'BORSK',
        'TABGD', 'TARKM', 'BORLS', 'MEGMT', 'SURGY', 'BINHO', 'EKOS', 'KBORU', 'TUREX', 'KRDMD',
        'KRDMA', 'KRDMB', 'BAGFS', 'GSDHO',  'PRKME', 'ULKER', 'CLEBI', 'AVOD', 'ALGYO',
        'GLYHO', 'TSKB', 'SKBNK', 'ALBRK',  'OYAKC', 'BUCIM', 'NUHCM', 'AFYON', 'CIMSA',
        'KONYA', 'INVEO', 'PENTA', 'SNGYO', 'TRGYO', 'HLGYO', 'VKGYO', 'MSGYO', 'ISGYO', 'TSGYO',
        'MAVI', 'MNDRS', 'NTGAZ', 'KCAER', 'TUKAS', 'TATGD', 'BRISA', 'GOODY', 'KORDS', 'PARSN',
        'EGEEN', 'ALCAR', 'BFREN', 'JANTS', 'KSTUR', 'BOSSA', 'YUNSA', 'KRVGD', 'KUVVA', 'DAPGM',
        'ASUZU',  'TRCAS',  'IHLAS', 'IHEVA', 'IHYAY', 'IHLGM', 'IHGZT', 'PRKAB',
         'ADESE',  'ZEDUR', 'EGEPO', 'MTRKS', 'INFO', 'OYYAT', 'ISMEN', 'GEDIK'
    ]
    return list(set([t.upper() + '.IS' for t in tickers if isinstance(t, str)]))

def get_fundamentals(ticker):
    try:
        t = yf.Ticker(ticker)
        info = t.info
        news = t.news[:3]
        
        fundamental_data = {
            'FK': info.get('forwardPE', info.get('trailingPE', 'N/A')),
            'PD_DD': info.get('priceToBook', 'N/A'),
            'MarketCap': info.get('marketCap', 'N/A'),
            'Sector': info.get('sector', 'N/A'),
            'DividendYield': info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0,
            'Beta': info.get('beta', 'N/A'),
            'News': [{'Title': n.get('title'), 'Link': n.get('link')} for n in news]
        }
        return fundamental_data
    except Exception:
        return {'FK': 'N/A', 'PD_DD': 'N/A', 'MarketCap': 'N/A', 'Sector': 'N/A', 'DividendYield': 0, 'Beta': 'N/A', 'News': []}

def get_kap_news():
    benchmarks = ["XU030.IS", "THYAO.IS", "ASELS.IS"]
    all_news = []
    
    for ticker in benchmarks:
        try:
            t = yf.Ticker(ticker)
            news = t.news
            if not news: continue
                
            for n in news[:5]:
                title = n.get('title') or n.get('Title') or 'Başlıksız Haber'
                link = n.get('link') or n.get('Link') or '#'
                publisher = n.get('publisher', 'Borsa Gündem/KAP')
                
                if not any(item['Title'] == title for item in all_news):
                    all_news.append({'Title': title, 'Link': link, 'Publisher': publisher})
            
            if len(all_news) >= 6: break
        except Exception as e:
            logger.error(f"News fetch error for {ticker}: {e}")
            
    return all_news[:10]

def get_akd_summary():
    try:
        benchmarks = ["THYAO.IS", "EREGL.IS", "TUPRS.IS", "SISE.IS"]
        summary = []
        for b in benchmarks:
            t = yf.Ticker(b)
            hist = t.history(period="5d")
            if len(hist) > 1:
                change = hist['Close'].iloc[-1] - hist['Close'].iloc[-2]
                volatility = hist['Close'].pct_change().std()
                avg_vol = hist['Volume'].mean()
                curr_vol = hist['Volume'].iloc[-1]
                
                status = "Alıcı / Güçlü" if change > 0 else "Satıcı / Zayıf"
                bot_trace = "Bot Topluyor" if curr_vol > avg_vol * 1.2 and volatility < 0.02 else ("Bot Boşaltıyor" if curr_vol > avg_vol * 1.2 and volatility > 0.04 else "Dengeli")
                
                summary.append({"Kurum": f"Piyasa Lideri ({b.split('.')[0]})", "Durum": status, "Hacim": bot_trace})
        
        return summary if summary else [{"Kurum": "Sistem", "Durum": "Veri Bekleniyor", "Hacim": "-"}]
    except:
        return [{"Kurum": "Sistem", "Durum": "Bağlantı Hatası", "Hacim": "-"}]

def get_social_sentiment():
    try:
        t = yf.Ticker("XU100.IS")
        news = t.news
        positive_keywords = ['artış', 'beklenti', 'rekor', 'alım', 'güçlü', 'yükseliş', 'up', 'buy', 'growth']
        negative_keywords = ['düşüş', 'kayıp', 'satış', 'zayıf', 'gerileme', 'down', 'sell', 'risk']
        
        score = 0
        for n in news:
            text = (n.get('title', '') + n.get('publisher', '')).lower()
            for w in positive_keywords: 
                if w in text: score += 1
            for w in negative_keywords: 
                if w in text: score -= 1
        
        trend = "Pozitif 🚀" if score > 0 else ("Negatif 📉" if score < 0 else "Nötr ⚖️")
        bot_density = "Yüksek" if score != 0 else "Düşük"
        
        return [
            {"Platform": "Genel Piyasa Duyarlılığı", "Trend": trend, "Bot_Yogunlugu": bot_density},
            {"Platform": "X (Twitter) Tahmini", "Trend": trend, "Bot_Yogunlugu": "Ölçülüyor..."}
        ]
    except:
        return [{"Platform": "Sistem", "Trend": "Veri Yok", "Bot_Yogunlugu": "-"}]

def calculate_technical_rating(df, golden_cross=False):
    if len(df) < 50:
        return "Nötr"
    
    last = df.iloc[-1]
    buy_signals = 0
    sell_signals = 0
    
    if golden_cross:
        buy_signals += 3

    rsi = last.get('RSI', 50)
    if pd.isna(rsi): rsi = 50
    if rsi < 30: buy_signals += 2
    elif rsi < 45: buy_signals += 1
    elif rsi > 70: sell_signals += 2
    elif rsi > 60: sell_signals += 1
    
    macd = last.get('MACD', 0)
    signal = last.get('MACD_Signal', 0)
    if not (pd.isna(macd) or pd.isna(signal)):
        if macd > signal and macd > 0: buy_signals += 2
        elif macd > signal: buy_signals += 1
        elif macd < signal and macd < 0: sell_signals += 2
        elif macd < signal: sell_signals += 1
    
    c = float(last['Close'])
    sma50 = last.get('SMA50', c)
    sma200 = last.get('SMA200', c)
    if not pd.isna(sma50) and c > sma50:
        buy_signals += 1
        if not pd.isna(sma200) and c > sma200: buy_signals += 1
    elif not pd.isna(sma50) and c < sma50:
        sell_signals += 1
        if not pd.isna(sma200) and c < sma200: sell_signals += 1
    
    lower = last.get('BB_Lower', c)
    upper = last.get('BB_Upper', c)
    if not (pd.isna(lower) or pd.isna(upper)):
        if c <= lower * 1.02: buy_signals += 2
        elif c >= upper * 0.98: sell_signals += 2

    net_score = buy_signals - sell_signals
    if net_score >= 4: return "Güçlü Al"
    elif net_score >= 1: return "Al"
    elif net_score <= -4: return "Güçlü Sat"
    elif net_score <= -1: return "Sat"
    else: return "Nötr"

def get_expert_commentary(ticker, fund, last_price, rsi, rating, golden_cross=False):
    comments = []
    if golden_cross:
        comments.append("📈 **Güçlü Trend Sinyali:** Hissede yeni bir Golden Cross gerçekleşti.")

    fk = fund.get('FK', 'N/A')
    if isinstance(fk, (int, float)):
        if fk < 8:
            comments.append(f"Değerleme açısından oldukça iskontolu (F/K: {round(fk, 1)}).")
        elif fk > 25:
            comments.append(f"Beklentiler önceden fiyatlanmış görünüyor (F/K: {round(fk, 1)}).")
            
    if rating == "Güçlü Al":
        if rsi < 40:
            comments.append("Aşırı satım bölgesinden sert dönüş sinyalleri veriyor.")
        else:
            comments.append("Hissede güçlü bir momentum var.")
    elif rating == "Güçlü Sat":
        if rsi > 70:
            comments.append("RSI aşırı alım bölgesinde, teknik düzeltme ihtimali yüksek.")
        else:
            comments.append("Teknik görünüm bozulmuş durumda.")
    elif rating == "Al":
        comments.append("Teknik toparlanma emareleri mevcut.")
    elif rating == "Sat":
        comments.append("Kısa vadeli göstergeler zayıf.")
    else:
        comments.append("Piyasa net bir yön tayin etmemiş.")
        
    div = fund.get('DividendYield', 0)
    if isinstance(div, (int, float)) and div > 4:
        comments.append(f"(Yıllık %{round(div, 1)} temettü verimi bir yastık görevi görebilir.)")

    if not comments:
        comments.append("Hisse özelinde parametreler nötr seviyede.")

    return " ".join(comments)

def scan_bist():
    tickers = get_bist_tickers()
    golden_cross_list = []
    momentum_list = []
    
    logger.info(f"Starting bulk download for {len(tickers)} tickers...")
    try:
        # Bulk download all tickers at once
        all_data = yf.download(tickers, period='1y', interval='1d', group_by='ticker', progress=False)
    except Exception as e:
        logger.error(f"Bulk download error: {e}")
        return [], []

    for ticker in tickers:
        try:
            # Extract data for specific ticker
            if len(tickers) > 1:
                df = all_data[ticker].dropna()
            else:
                df = all_data.dropna()

            if df.empty or len(df) < 50:
                continue
                
            df['SMA50'] = df['Close'].rolling(window=50).mean()
            df['SMA200'] = df['Close'].rolling(window=200).mean()
            
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            df['RSI'] = 100 - (100 / (1 + (gain / loss)))
            
            exp1 = df['Close'].ewm(span=12, adjust=False).mean()
            exp2 = df['Close'].ewm(span=26, adjust=False).mean()
            df['MACD'] = exp1 - exp2
            df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
            
            df['SMA20'] = df['Close'].rolling(window=20).mean()
            std_20 = df['Close'].rolling(window=20).std()
            df['BB_Upper'] = df['SMA20'] + (std_20 * 2)
            df['BB_Lower'] = df['SMA20'] - (std_20 * 2)
            df['VWAP20'] = calculate_rolling_vwap(df, window=20)
            
            recent = df.tail(15)
            for i in range(1, len(recent)):
                prev_row = recent.iloc[i-1]
                curr_row = recent.iloc[i]
                if float(prev_row['SMA50']) <= float(prev_row['SMA200']) and float(curr_row['SMA50']) > float(curr_row['SMA200']):
                    golden_cross_list.append({
                        'Ticker': ticker.replace('.IS', ''),
                        'CrossDate': curr_row.name.strftime('%Y-%m-%d'),
                        'CrossPrice': round(float(curr_row['Close']), 2),
                        'Price': round(float(df.iloc[-1]['Close']), 2) # Latest Price
                    })
                    break

            last = df.iloc[-1]
            prev = df.iloc[-2]
            avg_vol = df['Volume'].tail(20).mean()
            
            l_close = float(last['Close'])
            p_close = float(prev['Close'])
            l_vol = float(last['Volume'])
            l_rsi = float(last['RSI'])
            p_rsi = float(prev['RSI'])
            
            if l_close >= p_close and l_vol > avg_vol * 1.05 and 30 < l_rsi < 78:
                fund = get_fundamentals(ticker)
                score = 50 
                
                if l_vol > avg_vol * 3.0: score += 25 
                elif l_vol > avg_vol * 2.0: score += 15 
                elif l_vol > avg_vol * 1.5: score += 10
                
                if l_rsi > p_rsi: score += 10 
                if 45 < l_rsi < 65: score += 10 
                elif l_rsi < 35: score += 15 
                
                fk = fund['FK']
                if isinstance(fk, (int, float)):
                    if fk < 10: score += 15
                    elif fk < 20: score += 10
                
                if fund['Sector'] in ['Technology', 'Industrials', 'Energy']: score += 10
                if fund['DividendYield'] > 4: score += 5 
                
                # VWAP 20 Günlük Güç Bonusu
                l_vwap20 = float(last['VWAP20'])
                if l_close > l_vwap20:
                    score += 10

                bot_score = 0
                if l_vol > avg_vol * 2.5: bot_score += 40
                elif l_vol > avg_vol * 1.8: bot_score += 25
                
                daily_range = (float(last['High']) - float(last['Low'])) / float(last['Low'])
                if daily_range < 0.03: bot_score += 20 
                
                is_gc = any(gc['Ticker'] == ticker.replace('.IS', '') for gc in golden_cross_list)
                rating = calculate_technical_rating(df, golden_cross=is_gc)
                
                if score >= 65: 
                    momentum_list.append({
                        'Ticker': ticker.replace('.IS', ''),
                        'Price': round(l_close, 2),
                        'Change%': round(((l_close / p_close) - 1) * 100, 2),
                        'RSI': round(l_rsi, 2),
                        'Score': score,
                        'Bot_Score': bot_score,
                        'Target1': round(l_close * 1.10, 2),
                        'Stop': round(l_close * 0.93, 2),
                        'Tech_Rating': rating,
                        'Is_Golden_Cross': is_gc,
                        'VWAP20': round(l_vwap20, 2)
                    })
        except Exception as e:
            logger.error(f"Error scanning {ticker}: {e}")
            continue
            
    momentum_list = sorted(momentum_list, key=lambda x: x['Score'], reverse=True)
    return golden_cross_list, momentum_list

def calculate_atr(df, window=14):
    """Calculates Average True Range (ATR) for volatility measurement."""
    if len(df) < window + 1:
        return 0
    high_low = df['High'] - df['Low']
    high_close = (df['High'] - df['Close'].shift()).abs()
    low_close = (df['Low'] - df['Close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(window=window).mean().iloc[-1]
    return round(float(atr), 2)
    # Adding to end of scanner.py
    
def scan_ceiling_prospects():
    """
    Specifically hunts for 'Tavan' (Ceiling) series candidates.
    Focuses on: Volume Surge, Volatility Contraction (VCP), Small Cap.
    """
    tickers = get_bist_tickers()
    hunter_list = []
    
    logger.info(f"Starting Tavan Hunter scan for {len(tickers)} tickers...")
    try:
        all_data = yf.download(tickers, period='3mo', interval='1d', group_by='ticker', progress=False)
    except Exception as e:
        logger.error(f"Hunter download error: {e}")
        return []

    for ticker in tickers:
        try:
            if len(tickers) > 1:
                df = all_data[ticker].dropna()
            else:
                df = all_data.dropna()

            if len(df) < 30: continue
            
            last = df.iloc[-1]
            prev = df.iloc[-2]
            
            # 1. Volume Analysis
            avg_vol = df['Volume'].tail(22).mean() # 1 month avg
            vol_ratio = float(last['Volume']) / avg_vol
            
            # 2. VCP (Volatility Contraction) - Last 5 days range
            recent_5d = df.tail(6) # 5 days + 1 for baseline
            price_range_pct = (recent_5d['High'].max() - recent_5d['Low'].min()) / last['Close']
            
            # 3. Trend & RSI
            sma20 = df['Close'].rolling(window=20).mean().iloc[-1]
            sma50 = df['Close'].rolling(window=50).mean().iloc[-1]
            
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rsi = 100 - (100 / (1 + (gain / loss))).iloc[-1]
            
            # Scoring
            score = 0
            # Vol Score (Max 40)
            if vol_ratio > 4.0: score += 40
            elif vol_ratio > 2.5: score += 25
            elif vol_ratio > 1.5: score += 10
            
            # VCP Score (Max 30) - Tightness is good
            if price_range_pct < 0.035: score += 30
            elif price_range_pct < 0.06: score += 15
            
            # Trend Score (Max 20)
            if last['Close'] > sma20 > sma50: score += 15
            elif last['Close'] > sma20: score += 5
            
            # RSI Score (Max 10) - Sweet spot for breakout
            if 50 < rsi < 72: score += 10
            
            # Final Qualification
            if score >= 50:
                hunter_list.append({
                    'Ticker': ticker.replace('.IS', ''),
                    'Price': round(float(last['Close']), 2),
                    'Change%': round(((float(last['Close']) / float(prev['Close'])) - 1) * 100, 2),
                    'Score': score,
                    'VolRatio': round(vol_ratio, 1),
                    'Tightness%': round(price_range_pct * 100, 1),
                    'RSI': round(rsi, 1)
                })
        except:
            continue
            
    # Sort by score and return top 5
    return sorted(hunter_list, key=lambda x: x['Score'], reverse=True)[:5]
    # Adding to end of scanner.py
    
def scan_medium_term_trends():
    """
    Identifies sustainable medium-term (3-9 months) trends.
    Criteria: Price > SMA 200, SMA 50 > SMA 200, Consistent Hacim.
    """
    tickers = get_bist_tickers()
    trend_list = []
    
    logger.info(f"Starting Medium Term Trend scan for {len(tickers)} tickers...")
    try:
        # Download 1.5 years of data for accurate SMA 200
        all_data = yf.download(tickers, period='2y', interval='1d', group_by='ticker', progress=False)
    except Exception as e:
        logger.error(f"Trend download error: {e}")
        return []

    for ticker in tickers:
        try:
            if len(tickers) > 1:
                df = all_data[ticker].dropna()
            else:
                df = all_data.dropna()

            if len(df) < 210: continue # Need at least 200+ days for SMA 200
            
            # Indicator calculation
            df['SMA50'] = df['Close'].rolling(window=50).mean()
            df['SMA200'] = df['Close'].rolling(window=200).mean()
            
            last = df.iloc[-1]
            prev_10d = df.iloc[-10]
            
            price = float(last['Close'])
            sma50 = float(last['SMA50'])
            sma200 = float(last['SMA200'])
            
            # Mandatory: Price above 200d and 50d above 200d (Golden era)
            if price > sma200 and sma50 > sma200:
                # Calculate Trend Strength
                # Check if SMA 50 is sloping up
                sma50_slope = (sma50 - float(prev_10d['SMA50'])) / float(prev_10d['SMA50'])
                
                strength = "Orta"
                if price > sma50 and sma50_slope > 0:
                    strength = "Yüksek"
                elif price < sma50 and sma50_slope < 0:
                    strength = "Düşük (Düzeltmede)"
                
                # Distance from 200d (Value check)
                distance = ((price / sma200) - 1) * 100
                status = "Güvenli" if distance < 20 else "Genişlemiş (Pahalı)"
                
                trend_list.append({
                    'Ticker': ticker.replace('.IS', ''),
                    'Price': round(price, 2),
                    'SMA200': round(sma200, 2),
                    'Distance%': round(distance, 1),
                    'Strength': strength,
                    'Status': status
                })
        except:
            continue
            
    # Sort by strength (High first) and distance (Low first to find value)
    return sorted(trend_list, key=lambda x: (x['Strength'] != 'Yüksek', x['Distance%']))

def scan_all_golden_cross(lookback=5):
    """
    Scans BIST tickers for Golden Cross (SMA 50 crossing above SMA 200)
    across Daily, Weekly, 4h, and 2h intervals.
    """
    tickers = get_bist_tickers()
    results = {
        'weekly': [],
        'daily': [],
        '4h': [],
        '2h': []
    }
    
    # 1. Weekly scan
    logger.info("Scanning weekly Golden Cross...")
    try:
        w_data = yf.download(tickers, period='5y', interval='1wk', group_by='ticker', progress=False)
        for ticker in tickers:
            try:
                df = w_data[ticker].dropna() if len(tickers) > 1 else w_data.dropna()
                if len(df) < 200: continue
                df['SMA50'] = df['Close'].rolling(window=50).mean()
                df['SMA200'] = df['Close'].rolling(window=200).mean()
                
                recent = df.tail(lookback + 1)
                for i in range(1, len(recent)):
                    prev_row = recent.iloc[i-1]
                    curr_row = recent.iloc[i]
                    if float(prev_row['SMA50']) <= float(prev_row['SMA200']) and float(curr_row['SMA50']) > float(curr_row['SMA200']):
                        results['weekly'].append({
                            'Ticker': ticker.replace('.IS', ''),
                            'Time': curr_row.name.strftime('%Y-%m-%d'),
                            'CrossPrice': round(float(curr_row['Close']), 2),
                            'Price': round(float(df.iloc[-1]['Close']), 2)
                        })
                        break
            except Exception as e:
                logger.error(f"Weekly scan error for {ticker}: {e}")
    except Exception as e:
        logger.error(f"Weekly bulk download/scan error: {e}")

    # 2. Daily scan
    logger.info("Scanning daily Golden Cross...")
    try:
        d_data = yf.download(tickers, period='2y', interval='1d', group_by='ticker', progress=False)
        for ticker in tickers:
            try:
                df = d_data[ticker].dropna() if len(tickers) > 1 else d_data.dropna()
                if len(df) < 200: continue
                df['SMA50'] = df['Close'].rolling(window=50).mean()
                df['SMA200'] = df['Close'].rolling(window=200).mean()
                
                recent = df.tail(lookback + 1)
                for i in range(1, len(recent)):
                    prev_row = recent.iloc[i-1]
                    curr_row = recent.iloc[i]
                    if float(prev_row['SMA50']) <= float(prev_row['SMA200']) and float(curr_row['SMA50']) > float(curr_row['SMA200']):
                        results['daily'].append({
                            'Ticker': ticker.replace('.IS', ''),
                            'Time': curr_row.name.strftime('%Y-%m-%d'),
                            'CrossPrice': round(float(curr_row['Close']), 2),
                            'Price': round(float(df.iloc[-1]['Close']), 2)
                        })
                        break
            except Exception as e:
                logger.error(f"Daily scan error for {ticker}: {e}")
    except Exception as e:
        logger.error(f"Daily bulk download/scan error: {e}")

    # 3. 1h download for 4h & 2h
    logger.info("Downloading hourly data for 4h and 2h scans...")
    try:
        h_data = yf.download(tickers, period='1y', interval='1h', group_by='ticker', progress=False)
        for ticker in tickers:
            try:
                df_1h = h_data[ticker].dropna() if len(tickers) > 1 else h_data.dropna()
                if len(df_1h) < 200: continue
                
                # 4h Resample & Scan
                try:
                    df_4h = df_1h.resample('4h').agg({
                        'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
                    }).dropna()
                    if len(df_4h) >= 200:
                        df_4h['SMA50'] = df_4h['Close'].rolling(window=50).mean()
                        df_4h['SMA200'] = df_4h['Close'].rolling(window=200).mean()
                        recent = df_4h.tail(lookback + 1)
                        for i in range(1, len(recent)):
                            prev_row = recent.iloc[i-1]
                            curr_row = recent.iloc[i]
                            if float(prev_row['SMA50']) <= float(prev_row['SMA200']) and float(curr_row['SMA50']) > float(curr_row['SMA200']):
                                try:
                                    local_time = curr_row.name.tz_convert('Europe/Istanbul')
                                    cross_time = local_time.strftime('%Y-%m-%d %H:%M')
                                except:
                                    cross_time = curr_row.name.strftime('%Y-%m-%d %H:%M')
                                
                                results['4h'].append({
                                    'Ticker': ticker.replace('.IS', ''),
                                    'Time': cross_time,
                                    'CrossPrice': round(float(curr_row['Close']), 2),
                                    'Price': round(float(df_4h.iloc[-1]['Close']), 2)
                                })
                                break
                except Exception as e:
                    logger.error(f"4h resample/scan error for {ticker}: {e}")
                    
                # 2h Resample & Scan
                try:
                    df_2h = df_1h.resample('2h').agg({
                        'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
                    }).dropna()
                    if len(df_2h) >= 200:
                        df_2h['SMA50'] = df_2h['Close'].rolling(window=50).mean()
                        df_2h['SMA200'] = df_2h['Close'].rolling(window=200).mean()
                        recent = df_2h.tail(lookback + 1)
                        for i in range(1, len(recent)):
                            prev_row = recent.iloc[i-1]
                            curr_row = recent.iloc[i]
                            if float(prev_row['SMA50']) <= float(prev_row['SMA200']) and float(curr_row['SMA50']) > float(curr_row['SMA200']):
                                try:
                                    local_time = curr_row.name.tz_convert('Europe/Istanbul')
                                    cross_time = local_time.strftime('%Y-%m-%d %H:%M')
                                except:
                                    cross_time = curr_row.name.strftime('%Y-%m-%d %H:%M')
                                
                                results['2h'].append({
                                    'Ticker': ticker.replace('.IS', ''),
                                    'Time': cross_time,
                                    'CrossPrice': round(float(curr_row['Close']), 2),
                                    'Price': round(float(df_2h.iloc[-1]['Close']), 2)
                                })
                                break
                except Exception as e:
                    logger.error(f"2h resample/scan error for {ticker}: {e}")
            except Exception as e:
                logger.error(f"Hourly processing error for {ticker}: {e}")
    except Exception as e:
        logger.error(f"Hourly bulk download error: {e}")

    return results

def calculate_rolling_vwap(df, window=20):
    """Calculates a rolling Volume Weighted Average Price (VWAP) on daily data."""
    if len(df) < window:
        return df['Close']
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
    pv = typical_price * df['Volume']
    rolling_pv = pv.rolling(window=window).sum()
    rolling_vol = df['Volume'].rolling(window=window).sum()
    # Avoid division by zero by replacing 0 with NaN, then fillna
    vwap = rolling_pv / rolling_vol.replace(0, np.nan)
    return vwap.fillna(df['Close'])

def calculate_intraday_vwap(df_1h):
    """Calculates the intraday VWAP for the last trading session from hourly data."""
    if df_1h.empty:
        return 0
    # Group by the date portion of the datetime index
    last_date = df_1h.index[-1].date()
    df_last_day = df_1h[df_1h.index.date == last_date]
    if df_last_day.empty:
        return 0
    typical_price = (df_last_day['High'] + df_last_day['Low'] + df_last_day['Close']) / 3
    pv = (typical_price * df_last_day['Volume']).sum()
    total_vol = df_last_day['Volume'].sum()
    if total_vol == 0:
        return round(float(df_last_day['Close'].iloc[-1]), 2)
    return round(float(pv / total_vol), 2)

def check_reversal_signals(df):
    """
    Checks for bullish and bearish reversal signals on the given daily or hourly DataFrame.
    Returns a dict with lists of detected signals.
    """
    signals = {"bullish": [], "bearish": []}
    if len(df) < 20:
        return signals

    # Calculate indicators if they are not in the DataFrame
    if 'RSI' not in df.columns:
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / loss)))

    if 'MACD' not in df.columns or 'MACD_Signal' not in df.columns:
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()

    if 'SMA20' not in df.columns:
        df['SMA20'] = df['Close'].rolling(window=20).mean()

    # Get recent rows for crossover analysis (last 3 bars)
    recent = df.tail(3)
    if len(recent) < 3:
        return signals

    p2_rsi = float(recent['RSI'].iloc[0])
    p1_rsi = float(recent['RSI'].iloc[1])
    c_rsi = float(recent['RSI'].iloc[2])

    # RSI Crossovers (30 and 70 thresholds)
    if (p2_rsi < 30 or p1_rsi < 30) and c_rsi >= 30:
        signals["bullish"].append(f"RSI Aşırı Satımdan Yukarı Döndü ({round(c_rsi, 1)} 🟢)")
    elif (p2_rsi > 70 or p1_rsi > 70) and c_rsi <= 70:
        signals["bearish"].append(f"RSI Aşırı Alımdan Aşağı Döndü ({round(c_rsi, 1)} 🔴)")

    # MACD Crossovers
    p1_macd = float(recent['MACD'].iloc[1])
    p1_sig = float(recent['MACD_Signal'].iloc[1])
    c_macd = float(recent['MACD'].iloc[2])
    c_sig = float(recent['MACD_Signal'].iloc[2])

    if p1_macd <= p1_sig and c_macd > c_sig:
        signals["bullish"].append("MACD Al Sinyali (Yukarı Kesişim) 🟢")
    elif p1_macd >= p1_sig and c_macd < c_sig:
        signals["bearish"].append("MACD Sat Sinyali (Aşağı Kesişim) 🔴")

    # SMA20 Crossovers
    p1_close = float(recent['Close'].iloc[1])
    p1_sma = float(recent['SMA20'].iloc[1])
    c_close = float(recent['Close'].iloc[2])
    c_sma = float(recent['SMA20'].iloc[2])

    if p1_close <= p1_sma and c_close > c_sma:
        signals["bullish"].append("Fiyat SMA 20'yi Yukarı Kesti 🟢")
    elif p1_close >= p1_sma and c_close < c_sma:
        signals["bearish"].append("Fiyat SMA 20'yi Aşağı Kesti 🔴")

    return signals



