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

def calculate_rsi(series, period=14):
    """TradingView ve profesyonel platformlarla %100 uyumlu Wilder's RSI hesaplar."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    
    # Wilder's Smoothing: alpha = 1 / period
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def get_projected_volume_value(volume_val):
    """BIST seans saatlerine göre gün içi hacmi gün sonu eşdeğerine projekte eder."""
    import datetime
    import pytz
    tr_tz = pytz.timezone('Europe/Istanbul')
    now = datetime.datetime.now(tr_tz)
    if now.weekday() <= 4 and 10 <= now.hour < 18:
        elapsed_minutes = (now.hour - 10) * 60 + now.minute
        elapsed_minutes = max(15, min(elapsed_minutes, 480))
        return volume_val * (480.0 / elapsed_minutes)
    return volume_val

def get_fundamentals(ticker):
    try:
        t = yf.Ticker(ticker)
        info = t.info
        news = t.news[:3] if t.news else []
        
        parsed_news = []
        for n in news:
            if not isinstance(n, dict):
                continue
            title = None
            link = None
            
            content = n.get('content')
            if isinstance(content, dict):
                title = content.get('title')
                link = content.get('clickThroughUrl', {}).get('url') or content.get('canonicalUrl', {}).get('url')
            
            if not title:
                title = n.get('title') or n.get('Title')
            if not link:
                link = n.get('link') or n.get('Link')
                
            if title and link:
                parsed_news.append({'Title': title, 'Link': link})
        
        fundamental_data = {
            'FK': info.get('forwardPE', info.get('trailingPE', 'N/A')) if info else 'N/A',
            'PD_DD': info.get('priceToBook', 'N/A') if info else 'N/A',
            'MarketCap': info.get('marketCap', 'N/A') if info else 'N/A',
            'Sector': info.get('sector', 'N/A') if info else 'N/A',
            'DividendYield': info.get('dividendYield', 0) * 100 if info and info.get('dividendYield') else 0,
            'Beta': info.get('beta', 'N/A') if info else 'N/A',
            'News': parsed_news
        }
        return fundamental_data
    except Exception:
        return {'FK': 'N/A', 'PD_DD': 'N/A', 'MarketCap': 'N/A', 'Sector': 'N/A', 'DividendYield': 0, 'Beta': 'N/A', 'News': []}

import os

def calculate_volume_profile(df, bins=12):
    """
    Calculates Volume Profile (POC, VAH, VAL) from daily data.
    Takes last 30 trading days.
    """
    recent_df = df.tail(30)
    if len(recent_df) < 10:
        return None, None, None
        
    low_price = recent_df['Low'].min()
    high_price = recent_df['High'].max()
    
    if low_price == high_price:
        return low_price, low_price, low_price
        
    bin_edges = np.linspace(low_price, high_price, bins + 1)
    bin_volumes = np.zeros(bins)
    
    for _, row in recent_df.iterrows():
        tp = (row['High'] + row['Low'] + row['Close']) / 3.0
        vol = row['Volume']
        
        # Find which bin it belongs to
        bin_idx = np.digitize(tp, bin_edges) - 1
        bin_idx = max(0, min(bin_idx, bins - 1))
        bin_volumes[bin_idx] += vol
        
    # Point of Control (POC) - bin with highest volume
    poc_idx = np.argmax(bin_volumes)
    poc_price = (bin_edges[poc_idx] + bin_edges[poc_idx + 1]) / 2.0
    
    # Value Area (VA) - 70% of total volume around POC
    total_volume = bin_volumes.sum()
    target_volume = total_volume * 0.70
    
    # Expand from POC to find Value Area
    va_indices = {poc_idx}
    current_va_vol = bin_volumes[poc_idx]
    
    while current_va_vol < target_volume and len(va_indices) < bins:
        left_idx = min(va_indices) - 1
        right_idx = max(va_indices) + 1
        
        left_vol = bin_volumes[left_idx] if left_idx >= 0 else -1
        right_vol = bin_volumes[right_idx] if right_idx < bins else -1
        
        if left_vol == -1 and right_vol == -1:
            break
            
        if left_vol >= right_vol:
            va_indices.add(left_idx)
            current_va_vol += left_vol
        else:
            va_indices.add(right_idx)
            current_va_vol += right_vol
            
    val_idx = min(va_indices)
    vah_idx = max(va_indices)
    
    val = bin_edges[val_idx]
    vah = bin_edges[vah_idx + 1]
    
    return round(float(poc_price), 2), round(float(vah), 2), round(float(val), 2)

def summarize_kap_announcement(title):
    if not title:
        return "İçerik bulunamadı."
        
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt = (
                f"Aşağıdaki Borsa İstanbul KAP haber başlığını tek cümleyle, anlaşılır ve finansal özet olarak "
                f"Türkçe açıkla. Gereksiz detaylardan kaçın:\nBaşlık: {title}"
            )
            response = model.generate_content(prompt)
            summary = response.text.strip()
            if summary:
                return summary
        except Exception as e:
            logger.error(f"Gemini summarization error: {e}")
            
    # Fallback to rules-based Turkish NLP parser
    title_lower = title.lower()
    
    if any(k in title_lower for k in ["yeni iş", "sözleşme", "ihale", "sipariş", "iş ilişkisi"]):
        return "🤝 Şirket yeni bir iş anlaşması, sipariş veya ihale sözleşmesi imzaladı."
    elif any(k in title_lower for k in ["temettü", "kar payı", "kâr payı"]):
        return "💰 Şirket ortaklarına temettü (kâr payı) ödemesi yapacağını veya dağıtım detaylarını açıkladı."
    elif any(k in title_lower for k in ["bedelsiz", "sermaye artırım", "sermaye artış"]):
        if "bedelsiz" in title_lower:
            return "📈 Şirket iç kaynaklardan karşılanmak üzere bedelsiz sermaye artırımı gerçekleştirecek."
        elif "bedelli" in title_lower:
            return "📉 Şirket ortaklarından ek fon sağlamak amacıyla bedelli sermaye artırımına gidiyor."
        else:
            return "📊 Şirket sermaye artırım süreci hakkında bilgilendirmede bulundu."
    elif any(k in title_lower for k in ["geri alım", "payların geri", "hisselerin geri"]):
        return "🔄 Şirket kendi paylarını borsadan geri alacağını veya mevcut geri alım işlemlerini duyurdu."
    elif any(k in title_lower for k in ["yatırım", "fabrika", "tesis", "üretim", "kapasite"]):
        return "🏭 Şirket üretim kapasitesini artırmak veya yeni bir tesis kurmak için yatırım kararı aldı."
    elif any(k in title_lower for k in ["bilanço", "finansal rapor", "net kar", "net kâr", "hasılat", "faaliyet raporu"]):
        return "📊 Şirketin dönemsel finansal sonuçları, bilanço verileri veya kârlılık raporu açıklandı."
    elif any(k in title_lower for k in ["tedbir", "yasak", "vbts", "brüt takas", "depo şartı"]):
        return "⚠️ Borsa İstanbul tarafından hisseye volatilite bazlı işlem tedbiri (brüt takas vb.) uygulandı."
    elif any(k in title_lower for k in ["pay satışı", "hisse satışı", "ortaklık yapısı", "bloke"]):
        return "👥 Şirket ortakları veya ilişkili taraflarca pay satışı ya da ortaklık yapısında değişiklik bildirildi."
    elif any(k in title_lower for k in ["kredi", "borç", "finansman", "tahvil"]):
        return "💳 Şirket yeni bir kredi/borçlanma anlaşması yaptı veya tahvil ihraç belgesini yayınladı."
    elif any(k in title_lower for k in ["genel kurul", "olağan genel"]):
        return "🏛️ Şirketin genel kurul toplantısı, gündem maddeleri veya alınan kararlar paylaşıldı."
    else:
        return "📢 Şirket tarafından kamuyu aydınlatma platformuna özel durum veya genel bilgilendirme açıklaması yapıldı."

def get_kap_news():
    benchmarks = ["XU030.IS", "THYAO.IS", "ASELS.IS"]
    all_news = []
    
    for ticker in benchmarks:
        try:
            t = yf.Ticker(ticker)
            news = t.news
            if not news: continue
                
            for n in news[:5]:
                if not isinstance(n, dict):
                    continue
                title = None
                link = None
                publisher = None
                
                content = n.get('content')
                if isinstance(content, dict):
                    title = content.get('title')
                    link = content.get('clickThroughUrl', {}).get('url') or content.get('canonicalUrl', {}).get('url')
                    publisher = content.get('provider', {}).get('displayName')
                
                if not title:
                    title = n.get('title') or n.get('Title')
                if not link:
                    link = n.get('link') or n.get('Link')
                if not publisher:
                    publisher = n.get('publisher') or 'Borsa Gündem/KAP'
                    
                title = title or 'Başlıksız Haber'
                link = link or '#'
                
                if not any(item['Title'] == title for item in all_news):
                    summary = summarize_kap_announcement(title)
                    all_news.append({'Title': title, 'Link': link, 'Publisher': publisher, 'Summary': summary})
            
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
        news = t.news if t.news else []
        positive_keywords = ['artış', 'beklenti', 'rekor', 'alım', 'güçlü', 'yükseliş', 'up', 'buy', 'growth']
        negative_keywords = ['düşüş', 'kayıp', 'satış', 'zayıf', 'gerileme', 'down', 'sell', 'risk']
        
        score = 0
        for n in news:
            if not isinstance(n, dict):
                continue
            title = None
            publisher = None
            
            content = n.get('content')
            if isinstance(content, dict):
                title = content.get('title')
                publisher = content.get('provider', {}).get('displayName')
                
            if not title:
                title = n.get('title', '')
            if not publisher:
                publisher = n.get('publisher', '')
                
            text = (str(title) + str(publisher)).lower()
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
        # Bulk download all tickers at once (with auto_adjust=True for accurate splits/dividends)
        all_data = yf.download(tickers, period='1y', interval='1d', group_by='ticker', auto_adjust=True, progress=False)
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
            
            # Using mathematically correct Wilder's RSI
            df['RSI'] = calculate_rsi(df['Close'])
            
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
            
            # Average volume of past 20 trading days (excluding today's live/incomplete bar)
            avg_vol = df['Volume'].iloc[:-1].tail(20).mean() if len(df) > 1 else df['Volume'].mean()
            
            l_close = float(last['Close'])
            p_close = float(prev['Close'])
            
            # Project today's volume based on seans elapsed minutes if during market hours
            l_vol = get_projected_volume_value(float(last['Volume']))
            
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
    Focuses on: Volume Surge, Volatility Contraction (VCP) Squeeze, 
    Small Cap, High Close quality, and Short-term EMA alignment.
    """
    tickers = get_bist_tickers()
    hunter_list = []
    
    logger.info(f"Starting Enhanced Tavan Hunter scan for {len(tickers)} tickers...")
    try:
        all_data = yf.download(tickers, period='4mo', interval='1d', group_by='ticker', auto_adjust=True, progress=False)
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
            
            l_close = float(last['Close'])
            p_close = float(prev['Close'])
            l_high = float(last['High'])
            l_low = float(last['Low'])
            
            # price change pct today
            change_pct = ((l_close / p_close) - 1) * 100
            
            # Base filters: must have a solid positive breakout day
            if change_pct < 4.0:
                continue
            
            # Liquidity / Turnover Filter (Daily average turnover must be >= 15 Million TL)
            avg_vol = df['Volume'].iloc[:-1].tail(20).mean() if len(df) > 1 else df['Volume'].mean()
            avg_price = df['Close'].iloc[:-1].tail(20).mean() if len(df) > 1 else l_close
            avg_turnover = avg_vol * avg_price
            if avg_turnover < 15_000_000:
                continue
            
            # 1. Volume Analysis (using projected volume for today)
            l_vol = get_projected_volume_value(float(last['Volume']))
            vol_ratio = l_vol / avg_vol if avg_vol > 0 else 1.0
            
            if vol_ratio < 1.5:
                continue
                
            score = 0
            
            # Volume Score (Max 35 points)
            if vol_ratio >= 5.0:
                score += 35
            elif vol_ratio >= 3.0:
                score += 25
            elif vol_ratio >= 1.8:
                score += 15
            
            # 20-day Volume High Bonus (10 points)
            recent_20d_vol = df['Volume'].tail(21).iloc[:-1] # 20 days before today
            if l_vol > recent_20d_vol.max():
                score += 10
            
            # 2. Price Action & Close Strength (Max 30 points)
            if change_pct >= 9.5:
                score += 20
            elif change_pct >= 7.0:
                score += 15
            else:
                score += 8
                
            # Close Range Quality (Max 10 points)
            daily_range = l_high - l_low
            if daily_range > 0:
                close_pos = (l_high - l_close) / daily_range
                if close_pos <= 0.10: # Closed in top 10%
                    score += 10
                elif close_pos <= 0.20: # Closed in top 20%
                    score += 5

            # 3. Volatility Contraction Squeeze (VCP) (Max 20 points)
            # Check range of 10 days prior to today
            recent_10d_before = df.tail(11).iloc[:-1]
            tightness = 0.0
            if len(recent_10d_before) >= 10:
                past_high = recent_10d_before['High'].max()
                past_low = recent_10d_before['Low'].min()
                past_mean = recent_10d_before['Close'].mean()
                tightness = (past_high - past_low) / past_mean if past_mean > 0 else 0.0
                
                if 0.0 < tightness <= 0.05: # High consolidation (5%)
                    score += 20
                elif 0.0 < tightness <= 0.08: # Moderate consolidation (8%)
                    score += 10

            # 4. Small-Cap / Low Float Bonus (Max 15 points)
            fund = get_fundamentals(ticker)
            market_cap = fund.get('MarketCap', 'N/A')
            if isinstance(market_cap, (int, float)):
                if market_cap < 3_000_000_000: # Under 3B TL
                    score += 15
                elif market_cap < 8_000_000_000: # Under 8B TL
                    score += 10
                elif market_cap < 20_000_000_000: # Under 20B TL
                    score += 5

            # 5. RSI Sweet-Spot (Max 10 points) - using correct Wilder's RSI
            df['RSI'] = calculate_rsi(df['Close'])
            rsi = float(df['RSI'].iloc[-1])
            
            if 55 <= rsi <= 76:
                score += 10
            elif 76 < rsi <= 82:
                score += 5
                
            # 6. EMA Alignment (Max 10 points)
            df['EMA9'] = df['Close'].ewm(span=9, adjust=False).mean()
            df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()
            df['SMA50'] = df['Close'].rolling(window=50).mean()
            
            last_ema9 = float(df['EMA9'].iloc[-1])
            last_ema21 = float(df['EMA21'].iloc[-1])
            last_sma50 = float(df['SMA50'].iloc[-1]) if not pd.isna(df['SMA50'].iloc[-1]) else 0
            
            if l_close > last_ema9 > last_ema21:
                score += 10
            elif l_close > last_ema21 > last_sma50:
                score += 5
                
            if score >= 55:
                hunter_list.append({
                    'Ticker': ticker.replace('.IS', ''),
                    'Price': round(l_close, 2),
                    'Change%': round(change_pct, 2),
                    'Score': score,
                    'VolRatio': round(vol_ratio, 1),
                    'Tightness%': round(tightness * 100, 1),
                    'RSI': round(rsi, 1)
                })
        except Exception as ex:
            logger.error(f"Hunter scan error for {ticker}: {ex}")
            continue
            
    # Return top 5 ceiling prospects
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
        all_data = yf.download(tickers, period='2y', interval='1d', group_by='ticker', auto_adjust=True, progress=False)
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
        w_data = yf.download(tickers, period='5y', interval='1wk', group_by='ticker', auto_adjust=True, progress=False)
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
        d_data = yf.download(tickers, period='2y', interval='1d', group_by='ticker', auto_adjust=True, progress=False)
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
        h_data = yf.download(tickers, period='1y', interval='1h', group_by='ticker', auto_adjust=True, progress=False)
        for ticker in tickers:
            try:
                df_1h = h_data[ticker].dropna() if len(tickers) > 1 else h_data.dropna()
                if len(df_1h) < 200: continue
                
                # 4h Resample & Scan
                try:
                    df_4h = df_1h.resample('4h', origin='10:00').agg({
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
                    df_2h = df_1h.resample('2h', origin='10:00').agg({
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
        df['RSI'] = calculate_rsi(df['Close'])

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

def calculate_piotroski_score(ticker_name):
    """
    Calculates the 9-point Piotroski F-Score for fundamental strength.
    Returns: (score, label) or (None, error_msg)
    """
    try:
        t = yf.Ticker(ticker_name)
        
        financials = t.financials
        balance_sheet = t.balance_sheet
        cashflow = t.cashflow
        
        if (financials is None or financials.empty or 
            balance_sheet is None or balance_sheet.empty or 
            cashflow is None or cashflow.empty):
            return None, "Yetersiz Mali Veri"
            
        cols = list(financials.columns)
        if len(cols) < 2:
            return None, "Yetersiz Geçmiş Veri (2 Yıl Gerekli)"
            
        year_curr = cols[0]
        year_prev = cols[1]
        
        def get_val(df, key, col, default=0):
            if df is None or df.empty or key not in df.index:
                return default
            val = df.loc[key, col]
            if isinstance(val, pd.Series):
                val = val.iloc[0]
            if pd.isna(val) or val is None:
                return default
            return float(val)

        # 1. Profitability
        net_inc_curr = get_val(financials, 'Net Income', year_curr)
        net_inc_prev = get_val(financials, 'Net Income', year_prev)
        
        assets_curr = get_val(balance_sheet, 'Total Assets', year_curr)
        assets_prev = get_val(balance_sheet, 'Total Assets', year_prev)
        
        roa_curr = net_inc_curr / assets_curr if assets_curr > 0 else 0
        roa_prev = net_inc_prev / assets_prev if assets_prev > 0 else 0
        
        cfo_curr = get_val(cashflow, 'Operating Cash Flow', year_curr)
        
        # F1: ROA > 0
        f1 = 1 if roa_curr > 0 else 0
        # F2: CFO > 0
        f2 = 1 if cfo_curr > 0 else 0
        # F3: CFO > Net Income (Accrual check)
        f3 = 1 if cfo_curr > net_inc_curr else 0
        # F4: Change in ROA
        f4 = 1 if roa_curr > roa_prev else 0
        
        # 2. Leverage, Liquidity, Source of Funds
        lt_debt_curr = get_val(balance_sheet, 'Long Term Debt', year_curr, 0)
        lt_debt_prev = get_val(balance_sheet, 'Long Term Debt', year_prev, 0)
        
        lev_curr = lt_debt_curr / assets_curr if assets_curr > 0 else 0
        lev_prev = lt_debt_prev / assets_prev if assets_prev > 0 else 0
        
        # F5: Leverage decrease or constant zero
        f5 = 1 if lev_curr < lev_prev or (lev_curr == 0 and lev_prev == 0) else 0
        
        curr_assets_curr = get_val(balance_sheet, 'Current Assets', year_curr)
        curr_assets_prev = get_val(balance_sheet, 'Current Assets', year_prev)
        curr_liab_curr = get_val(balance_sheet, 'Current Liabilities', year_curr)
        curr_liab_prev = get_val(balance_sheet, 'Current Liabilities', year_prev)
        
        cr_curr = curr_assets_curr / curr_liab_curr if curr_liab_curr > 0 else 0
        cr_prev = curr_assets_prev / curr_liab_prev if curr_liab_prev > 0 else 0
        
        # F6: Current Ratio increase
        f6 = 1 if cr_curr > cr_prev else 0
        
        shares_curr = get_val(balance_sheet, 'Ordinary Shares Number', year_curr, None)
        if shares_curr is None:
            shares_curr = get_val(balance_sheet, 'Share Issued', year_curr, 0)
        shares_prev = get_val(balance_sheet, 'Ordinary Shares Number', year_prev, None)
        if shares_prev is None:
            shares_prev = get_val(balance_sheet, 'Share Issued', year_prev, 0)
            
        # F7: No equity dilution
        f7 = 1 if shares_curr <= shares_prev else 0
        
        # 3. Operating Efficiency
        gp_curr = get_val(financials, 'Gross Profit', year_curr)
        gp_prev = get_val(financials, 'Gross Profit', year_prev)
        rev_curr = get_val(financials, 'Total Revenue', year_curr)
        rev_prev = get_val(financials, 'Total Revenue', year_prev)
        
        gm_curr = gp_curr / rev_curr if rev_curr > 0 else 0
        gm_prev = gp_prev / rev_prev if rev_prev > 0 else 0
        
        # F8: Gross Margin increase
        f8 = 1 if gm_curr > gm_prev else 0
        
        at_curr = rev_curr / assets_curr if assets_curr > 0 else 0
        at_prev = rev_prev / assets_prev if assets_prev > 0 else 0
        
        # F9: Asset Turnover increase
        f9 = 1 if at_curr > at_prev else 0
        
        score = f1 + f2 + f3 + f4 + f5 + f6 + f7 + f8 + f9
        
        if score >= 8:
            label = "Mükemmel 🟢"
        elif score >= 5:
            label = "Stabil 🟡"
        else:
            label = "Zayıf 🔴"
            
        return score, label
    except Exception as e:
        logger.error(f"Error calculating Piotroski score for {ticker_name}: {e}")
        return None, "Hesaplama Hatası"

def calculate_stoch_rsi(series_close, stoch_period=14, rsi_period=14, k_smooth=3, d_smooth=3):
    """Calculates Stochastic RSI (K and D) matching TradingView."""
    rsi = calculate_rsi(series_close, rsi_period)
    lowest_rsi = rsi.rolling(window=stoch_period).min()
    highest_rsi = rsi.rolling(window=stoch_period).max()
    stoch_rsi = (rsi - lowest_rsi) / (highest_rsi - lowest_rsi.replace(0, np.nan)) * 100
    stoch_rsi = stoch_rsi.fillna(50)
    k = stoch_rsi.rolling(window=k_smooth).mean()
    d = k.rolling(window=d_smooth).mean()
    return k, d

def calculate_aroon_up(series_high, window=14):
    """Calculates Aroon Up indicator matching TradingView."""
    def get_days_since_high(x):
        return window - np.argmax(x)
    days_since_high = series_high.rolling(window=window + 1).apply(get_days_since_high, raw=True)
    aroon_up = (window - days_since_high) / window * 100
    return aroon_up

def scan_dip_taramasi():
    """
    Dip Taraması:
    - Universe: BIST 100 or liquid BIST tickers
    - ROC(9) >= 1%
    - Rel Vol > 1.2
    - MACD Line < 0
    """
    tickers = get_bist_tickers()
    results = []
    try:
        df_batch = yf.download(tickers, period='60d', group_by='ticker', auto_adjust=True, progress=False)
    except Exception as e:
        logger.error(f"Error downloading batch in scan_dip_taramasi: {e}")
        return []
        
    for ticker_is in tickers:
        ticker_raw = ticker_is.replace(".IS", "")
        try:
            if len(tickers) > 1:
                if ticker_is not in df_batch.columns.levels[0]:
                    continue
                df = df_batch[ticker_is].dropna(subset=['Close'])
            else:
                df = df_batch.dropna(subset=['Close'])
                
            if len(df) < 30:
                continue
                
            close = df['Close']
            volume = df['Volume']
            
            roc9 = ((close.iloc[-1] / close.iloc[-10]) - 1) * 100 if len(close) >= 10 else 0
            
            vol_ma20 = volume.rolling(window=20).mean()
            proj_vol = get_projected_volume_value(float(volume.iloc[-1]))
            rel_vol = proj_vol / float(vol_ma20.iloc[-1]) if vol_ma20.iloc[-1] > 0 else 0
            
            exp1 = close.ewm(span=12, adjust=False).mean()
            exp2 = close.ewm(span=26, adjust=False).mean()
            macd_line = exp1 - exp2
            last_macd = float(macd_line.iloc[-1])
            
            if roc9 >= 1.0 and rel_vol > 1.2 and last_macd < 0:
                results.append({
                    'Ticker': ticker_raw,
                    'Price': round(float(close.iloc[-1]), 2),
                    'ROC9': round(roc9, 2),
                    'RelVol': round(rel_vol, 2),
                    'MACD': round(last_macd, 3)
                })
        except Exception as ex:
            logger.error(f"Error checking dip_taramasi for {ticker_raw}: {ex}")
            
    return sorted(results, key=lambda x: x['RelVol'], reverse=True)

def scan_tawrama():
    """
    Tawrama:
    - Universe: All BIST tickers
    - Stochastic RSI K crosses up 20
    - Aroon Up (14) is between 10% and 30%
    """
    tickers = get_bist_tickers()
    results = []
    try:
        df_batch = yf.download(tickers, period='60d', group_by='ticker', auto_adjust=True, progress=False)
    except Exception as e:
        logger.error(f"Error downloading batch in scan_tawrama: {e}")
        return []
        
    for ticker_is in tickers:
        ticker_raw = ticker_is.replace(".IS", "")
        try:
            if len(tickers) > 1:
                if ticker_is not in df_batch.columns.levels[0]:
                    continue
                df = df_batch[ticker_is].dropna(subset=['Close'])
            else:
                df = df_batch.dropna(subset=['Close'])
                
            if len(df) < 35:
                continue
                
            close = df['Close']
            high = df['High']
            
            k, d = calculate_stoch_rsi(close, stoch_period=14, rsi_period=14, k_smooth=3, d_smooth=3)
            k_curr = float(k.iloc[-1])
            k_prev = float(k.iloc[-2])
            
            aroon_up = calculate_aroon_up(high, window=14)
            aroon_curr = float(aroon_up.iloc[-1])
            
            if k_prev < 20 and k_curr >= 20 and (10.0 <= aroon_curr <= 30.0):
                results.append({
                    'Ticker': ticker_raw,
                    'Price': round(float(close.iloc[-1]), 2),
                    'StochK': round(k_curr, 2),
                    'AroonUp': round(aroon_curr, 2)
                })
        except Exception as ex:
            logger.error(f"Error checking tawrama for {ticker_raw}: {ex}")
            
    return results

def scan_haco():
    """
    Haco:
    - Universe: BIST 100 or liquid BIST tickers
    - MACD Line (12, 26) is between -5 and 5
    - RSI(14) is between 45 and 60
    - Stochastic RSI K is between 20 and 70
    - Daily price change is between 1.0 and 5.0 TRY
    - Hacim: Volume * Close >= 20 Million TL or Volume >= 100k shares
    """
    tickers = get_bist_tickers()
    results = []
    try:
        df_batch = yf.download(tickers, period='60d', group_by='ticker', auto_adjust=True, progress=False)
    except Exception as e:
        logger.error(f"Error downloading batch in scan_haco: {e}")
        return []
        
    for ticker_is in tickers:
        ticker_raw = ticker_is.replace(".IS", "")
        try:
            if len(tickers) > 1:
                if ticker_is not in df_batch.columns.levels[0]:
                    continue
                df = df_batch[ticker_is].dropna(subset=['Close'])
            else:
                df = df_batch.dropna(subset=['Close'])
                
            if len(df) < 30:
                continue
                
            close = df['Close']
            volume = df['Volume']
            
            last_price = float(close.iloc[-1])
            prev_price = float(close.iloc[-2])
            price_change = last_price - prev_price
            
            exp1 = close.ewm(span=12, adjust=False).mean()
            exp2 = close.ewm(span=26, adjust=False).mean()
            macd_line = exp1 - exp2
            last_macd = float(macd_line.iloc[-1])
            
            rsi = calculate_rsi(close, 14)
            last_rsi = float(rsi.iloc[-1])
            
            k, d = calculate_stoch_rsi(close, stoch_period=14, rsi_period=14, k_smooth=3, d_smooth=3)
            last_stoch_k = float(k.iloc[-1])
            
            proj_vol = get_projected_volume_value(float(volume.iloc[-1]))
            turnover = proj_vol * last_price
            
            if (-5.0 <= last_macd <= 5.0) and (45.0 <= last_rsi <= 60.0) and (20.0 <= last_stoch_k <= 70.0) and (1.0 <= price_change <= 5.0) and (turnover >= 20_000_000 or proj_vol >= 100_000):
                results.append({
                    'Ticker': ticker_raw,
                    'Price': round(last_price, 2),
                    'Change': round(price_change, 2),
                    'MACD': round(last_macd, 3),
                    'RSI': round(last_rsi, 2),
                    'StochK': round(last_stoch_k, 2),
                    'Turnover': round(turnover, 2)
                })
        except Exception as ex:
            logger.error(f"Error checking haco for {ticker_raw}: {ex}")
            
    return results

def scan_mum_taramasi():
    """
    Mum Taraması:
    - Universe: All BIST tickers
    - Detects Marubozu White (Bullish) and Spinning Top White patterns
    """
    tickers = get_bist_tickers()
    results = []
    try:
        df_batch = yf.download(tickers, period='10d', group_by='ticker', auto_adjust=True, progress=False)
    except Exception as e:
        logger.error(f"Error downloading batch in scan_mum_taramasi: {e}")
        return []
        
    for ticker_is in tickers:
        ticker_raw = ticker_is.replace(".IS", "")
        try:
            if len(tickers) > 1:
                if ticker_is not in df_batch.columns.levels[0]:
                    continue
                df = df_batch[ticker_is].dropna(subset=['Close'])
            else:
                df = df_batch.dropna(subset=['Close'])
                
            if len(df) < 3:
                continue
                
            last_row = df.iloc[-1]
            open_p = float(last_row['Open'])
            high_p = float(last_row['High'])
            low_p = float(last_row['Low'])
            close_p = float(last_row['Close'])
            
            if high_p == low_p:
                continue
                
            body = close_p - open_p
            total_range = high_p - low_p
            
            if close_p > open_p:
                upper_shadow = high_p - close_p
                lower_shadow = open_p - low_p
                
                is_marubozu = (
                    (lower_shadow <= 0.05 * total_range) and 
                    (upper_shadow <= 0.05 * total_range) and 
                    (body / close_p >= 0.01)
                )
                
                is_spinning_top = (
                    (body / total_range <= 0.3) and 
                    (upper_shadow / total_range >= 0.2) and 
                    (lower_shadow / total_range >= 0.2)
                )
                
                pattern = ""
                if is_marubozu:
                    pattern = "Marubozu (Boğa) ⬜🟢"
                elif is_spinning_top:
                    pattern = "Spinning Top (Fırıldak) 🌪️⬜"
                    
                if pattern:
                    results.append({
                        'Ticker': ticker_raw,
                        'Price': round(close_p, 2),
                        'Change%': round(((close_p / open_p) - 1) * 100, 2),
                        'Pattern': pattern
                    })
        except Exception as ex:
            logger.error(f"Error checking mum_taramasi for {ticker_raw}: {ex}")
            
    return results

def calculate_aroon_down(series_low, window=14):
    """Calculates Aroon Down indicator matching TradingView."""
    def get_days_since_low(x):
        return window - np.argmax(x)
    days_since_low = series_low.rolling(window=window + 1).apply(get_days_since_low, raw=True)
    aroon_down = (window - days_since_low) / window * 100
    return aroon_down

def calculate_wma(series, window):
    """Calculates Weighted Moving Average matching TradingView."""
    weights = np.arange(1, window + 1)
    return series.rolling(window).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)

def calculate_hma(series, window):
    """Calculates Hull Moving Average matching TradingView."""
    half_len = int(window / 2)
    sqrt_len = int(np.sqrt(window))
    wma_half = calculate_wma(series, half_len)
    wma_full = calculate_wma(series, window)
    diff = 2 * wma_half - wma_full
    hma = calculate_wma(diff, sqrt_len)
    return hma

def calculate_sar(df, af_start=0.02, af_step=0.02, af_max=0.20):
    """Calculates Parabolic SAR matching TradingView."""
    high = df['High'].values
    low = df['Low'].values
    close = df['Close'].values
    n = len(df)
    sar = np.zeros(n)
    trend = np.zeros(n)
    ep = np.zeros(n)
    af = np.zeros(n)
    
    if n < 2:
        return pd.Series(sar, index=df.index)
        
    if close[1] > close[0]:
        trend[1] = 1
        sar[1] = low[0]
        ep[1] = high[1]
        af[1] = af_start
    else:
        trend[1] = -1
        sar[1] = high[0]
        ep[1] = low[1]
        af[1] = af_start
        
    for i in range(2, n):
        sar_cand = sar[i-1] + af[i-1] * (ep[i-1] - sar[i-1])
        if trend[i-1] == 1:
            sar[i] = min(sar_cand, low[i-1], low[i-2])
            if low[i] < sar[i]:
                trend[i] = -1
                sar[i] = ep[i-1]
                ep[i] = low[i]
                af[i] = af_start
            else:
                trend[i] = 1
                if high[i] > ep[i-1]:
                    ep[i] = high[i]
                    af[i] = min(af[i-1] + af_step, af_max)
                else:
                    ep[i] = ep[i-1]
                    af[i] = af[i-1]
        else:
            sar[i] = max(sar_cand, high[i-1], high[i-2])
            if high[i] > sar[i]:
                trend[i] = 1
                sar[i] = ep[i-1]
                ep[i] = high[i]
                af[i] = af_start
            else:
                trend[i] = -1
                if low[i] < ep[i-1]:
                    ep[i] = low[i]
                    af[i] = min(af[i-1] + af_step, af_max)
                else:
                    ep[i] = ep[i-1]
                    af[i] = af[i-1]
    return pd.Series(sar, index=df.index)

def scan_goreceli():
    """
    Göreceli Taraması:
    - Universe: All BIST tickers
    - Rel Vol > 2.0
    """
    tickers = get_bist_tickers()
    results = []
    try:
        df_batch = yf.download(tickers, period='35d', group_by='ticker', auto_adjust=True, progress=False)
    except Exception as e:
        logger.error(f"Error downloading batch in scan_goreceli: {e}")
        return []
        
    for ticker_is in tickers:
        ticker_raw = ticker_is.replace(".IS", "")
        try:
            if len(tickers) > 1:
                if ticker_is not in df_batch.columns.levels[0]:
                    continue
                df = df_batch[ticker_is].dropna(subset=['Close'])
            else:
                df = df_batch.dropna(subset=['Close'])
                
            if len(df) < 20:
                continue
                
            close = df['Close']
            volume = df['Volume']
            
            vol_ma20 = volume.rolling(window=20).mean()
            proj_vol = get_projected_volume_value(float(volume.iloc[-1]))
            rel_vol = proj_vol / float(vol_ma20.iloc[-1]) if vol_ma20.iloc[-1] > 0 else 0
            
            if rel_vol > 2.0:
                results.append({
                    'Ticker': ticker_raw,
                    'Price': round(float(close.iloc[-1]), 2),
                    'Change%': round(((close.iloc[-1] / close.iloc[-2]) - 1) * 100, 2),
                    'RelVol': round(rel_vol, 2)
                })
        except Exception as ex:
            logger.error(f"Error checking goreceli for {ticker_raw}: {ex}")
            
    return sorted(results, key=lambda x: x['RelVol'], reverse=True)

def scan_oncu_taramasi():
    """
    Öncü Taraması:
    - Universe: All BIST tickers
    - 30% <= Aroon Down (14) <= 50%
    - Parabolic SAR < Price
    - Hull MA (9) > Price
    """
    tickers = get_bist_tickers()
    results = []
    try:
        df_batch = yf.download(tickers, period='40d', group_by='ticker', auto_adjust=True, progress=False)
    except Exception as e:
        logger.error(f"Error downloading batch in scan_oncu_taramasi: {e}")
        return []
        
    for ticker_is in tickers:
        ticker_raw = ticker_is.replace(".IS", "")
        try:
            if len(tickers) > 1:
                if ticker_is not in df_batch.columns.levels[0]:
                    continue
                df = df_batch[ticker_is].dropna(subset=['Close'])
            else:
                df = df_batch.dropna(subset=['Close'])
                
            if len(df) < 25:
                continue
                
            close = df['Close']
            low = df['Low']
            high = df['High']
            
            aroon_down = calculate_aroon_down(low, window=14)
            aroon_curr = float(aroon_down.iloc[-1])
            
            sar = calculate_sar(df)
            sar_curr = float(sar.iloc[-1])
            
            hma9 = calculate_hma(close, 9)
            hma_curr = float(hma9.iloc[-1])
            
            last_price = float(close.iloc[-1])
            
            if (30.0 <= aroon_curr <= 50.0) and (sar_curr < last_price) and (hma_curr > last_price):
                results.append({
                    'Ticker': ticker_raw,
                    'Price': round(last_price, 2),
                    'Change%': round(((close.iloc[-1] / close.iloc[-2]) - 1) * 100, 2),
                    'AroonDown': round(aroon_curr, 2),
                    'SAR': round(sar_curr, 2),
                    'HMA9': round(hma_curr, 2)
                })
        except Exception as ex:
            logger.error(f"Error checking oncu_taramasi for {ticker_raw}: {ex}")
            
    return results

def scan_hacim_taramasi():
    """
    Hacim Taraması:
    - Universe: All BIST tickers
    - Rel Vol > 2.0
    - Parabolic SAR crosses down Low today (SAR_prev >= Low_prev and SAR_curr < Low_curr)
    """
    tickers = get_bist_tickers()
    results = []
    try:
        df_batch = yf.download(tickers, period='40d', group_by='ticker', auto_adjust=True, progress=False)
    except Exception as e:
        logger.error(f"Error downloading batch in scan_hacim_taramasi: {e}")
        return []
        
    for ticker_is in tickers:
        ticker_raw = ticker_is.replace(".IS", "")
        try:
            if len(tickers) > 1:
                if ticker_is not in df_batch.columns.levels[0]:
                    continue
                df = df_batch[ticker_is].dropna(subset=['Close'])
            else:
                df = df_batch.dropna(subset=['Close'])
                
            if len(df) < 25:
                continue
                
            close = df['Close']
            volume = df['Volume']
            low = df['Low']
            
            vol_ma20 = volume.rolling(window=20).mean()
            proj_vol = get_projected_volume_value(float(volume.iloc[-1]))
            rel_vol = proj_vol / float(vol_ma20.iloc[-1]) if vol_ma20.iloc[-1] > 0 else 0
            
            sar = calculate_sar(df)
            sar_curr = float(sar.iloc[-1])
            sar_prev = float(sar.iloc[-2])
            
            low_curr = float(low.iloc[-1])
            low_prev = float(low.iloc[-2])
            
            if rel_vol > 2.0 and (sar_prev >= low_prev) and (sar_curr < low_curr):
                results.append({
                    'Ticker': ticker_raw,
                    'Price': round(float(close.iloc[-1]), 2),
                    'Change%': round(((close.iloc[-1] / close.iloc[-2]) - 1) * 100, 2),
                    'RelVol': round(rel_vol, 2),
                    'SAR': round(sar_curr, 2)
                })
        except Exception as ex:
            logger.error(f"Error checking hacim_taramasi for {ticker_raw}: {ex}")
            
    return sorted(results, key=lambda x: x['RelVol'], reverse=True)

# Helper functions for CANAVAR & nazlıv10 indicators
def calculate_rma(series, period):
    return series.ewm(alpha=1/period, min_periods=period, adjust=False).mean()

def calculate_cci(high, low, close, period=10):
    tp = (high + low + close) / 3.0
    sma_tp = tp.rolling(window=period).mean()
    mad = tp.rolling(window=period).apply(lambda x: np.mean(np.abs(x - x.mean())), raw=True)
    cci = (tp - sma_tp) / (0.015 * mad.replace(0, np.nan))
    return cci.fillna(0)

def calculate_obv(close, volume):
    direction = np.sign(close.diff())
    if len(direction) > 0:
        direction.iloc[0] = 0
    obv = (direction * volume).cumsum()
    return obv

def calculate_mfi(high, low, close, volume, period=14):
    tp = (high + low + close) / 3.0
    raw_money_flow = tp * volume
    mfi_direction = np.sign(tp.diff())
    if len(mfi_direction) > 0:
        mfi_direction.iloc[0] = 0
    pos_flow = raw_money_flow.where(mfi_direction > 0, 0)
    neg_flow = raw_money_flow.where(mfi_direction < 0, 0)
    pos_mf = pos_flow.rolling(window=period).sum()
    neg_mf = neg_flow.rolling(window=period).sum()
    mfi_ratio = pos_mf / neg_mf.replace(0, np.nan)
    mfi = 100 - (100 / (1 + mfi_ratio))
    return mfi.fillna(50)

def calculate_vwma(close, volume, period):
    pv = close * volume
    rolling_pv = pv.rolling(window=period).sum()
    rolling_vol = volume.rolling(window=period).sum()
    vwma = rolling_pv / rolling_vol.replace(0, np.nan)
    return vwma.fillna(close)

def calculate_cmf(high, low, close, volume, period=21):
    range_hl = (high - low).replace(0, np.nan)
    cmfm = ((close - low) - (high - close)) / range_hl
    cmfm = cmfm.fillna(0)
    cmfv = cmfm * volume
    cmf = cmfv.rolling(window=period).sum() / volume.rolling(window=period).sum().replace(0, np.nan)
    return cmf.fillna(0)

def calculate_wavetrend(close, high, low, chlen=9, avg=12, malen=3):
    hlc3 = (high + low + close) / 3.0
    esa = hlc3.ewm(span=chlen, adjust=False).mean()
    de = (hlc3 - esa).abs().ewm(span=chlen, adjust=False).mean()
    ci = (hlc3 - esa) / (0.015 * de.replace(0, np.nan))
    ci = ci.fillna(0)
    wt1 = ci.ewm(span=avg, adjust=False).mean()
    wt2 = wt1.rolling(window=malen).mean()
    wt_vwap = wt1 - wt2
    return wt1, wt2, wt_vwap

def normalize_nazli(value_series, avg_series):
    ratio = value_series / avg_series.replace(0, np.nan)
    ratio = ratio.fillna(0)
    nor = pd.Series(0.1, index=ratio.index)
    nor.loc[ratio > 0.20] = 0.25
    nor.loc[ratio > 0.40] = 0.50
    nor.loc[ratio > 0.60] = 0.60
    nor.loc[ratio > 0.80] = 0.70
    nor.loc[ratio > 1.00] = 0.80
    nor.loc[ratio > 1.20] = 0.90
    nor.loc[ratio > 1.50] = 1.00
    return nor

def calculate_nazli_rrof(df, lookback=20, length=10, smooth=3):
    close = df['Close']
    open_p = df['Open']
    high = df['High']
    low = df['Low']
    volume = df['Volume']
    
    vola_avg = volume.rolling(window=lookback).mean()
    vola_n = normalize_nazli(volume, vola_avg) * 100.0
    
    bar_range = (high - low).replace(0, np.nan)
    barclosing = 2 * (close - low) / bar_range * 100 - 100
    barclosing = barclosing.fillna(0)
    
    bar_spread = close - open_p
    s2r = bar_spread / bar_range * 100
    s2r = s2r.fillna(0)
    
    bar_spread_abs = bar_spread.abs()
    bar_spread_avg = bar_spread_abs.rolling(window=lookback).mean()
    bar_spread_ratio_n = normalize_nazli(bar_spread_abs, bar_spread_avg) * 100.0 * np.sign(bar_spread)
    
    r2 = (df['High'].rolling(2).max() - df['Low'].rolling(2).min()).replace(0, np.nan)
    barclosing_2 = 2 * (close - df['Low'].rolling(2).min()) / r2 * 100 - 100
    barclosing_2 = barclosing_2.fillna(0)
    
    src_shift = close.diff()
    shift_2bar_to_r2 = src_shift / r2 * 100
    shift_2bar_to_r2 = shift_2bar_to_r2.fillna(0)
    
    src_shift_abs = src_shift.abs()
    src_shift_avg = src_shift_abs.rolling(window=lookback).mean()
    src_shift_ratio_n = normalize_nazli(src_shift_abs, src_shift_avg) * 100.0 * np.sign(src_shift)
    
    pricea_n = (barclosing + s2r + bar_spread_ratio_n + barclosing_2 + shift_2bar_to_r2 + src_shift_ratio_n) / 6.0
    bar_flow = pricea_n * vola_n / 100.0
    
    bulls = bar_flow.clip(lower=0)
    bears = -1 * bar_flow.clip(upper=0)
    
    bulls_avg = calculate_wma(bulls, length)
    bears_avg = calculate_wma(bears, length)
    
    dx = bulls_avg / bears_avg.replace(0, np.nan)
    rrof = 2.0 * (100.0 - 100.0 / (1.0 + dx)) - 100.0
    rrof = rrof.fillna(0)
    
    rrof_s = calculate_wma(rrof, smooth)
    signal = calculate_wma(rrof_s, 5)
    
    ev_ratio = 100.0 * pricea_n.abs() / vola_n.replace(0, np.nan)
    ev_ratio = ev_ratio.fillna(0)
    
    is_positive = pricea_n > 0
    is_compression = ev_ratio <= 50.0
    is_eom = ev_ratio >= 120.0
    
    return rrof_s, signal, is_compression, is_eom, is_positive, pricea_n, vola_n

def check_divergence_v4(df, prd=5, maxpp=10, maxbars=100, dontconfirm=False):
    close = df['Close']
    high = df['High']
    low = df['Low']
    volume = df['Volume']
    
    indicators = {}
    
    # 1. MACD
    exp1 = close.ewm(span=12, adjust=False).mean()
    exp2 = close.ewm(span=26, adjust=False).mean()
    indicators['MACD'] = exp1 - exp2
    
    # 2. Hist
    macd_signal = indicators['MACD'].ewm(span=9, adjust=False).mean()
    indicators['Hist'] = indicators['MACD'] - macd_signal
    
    # 3. RSI
    indicators['RSI'] = calculate_rsi(close, 14)
    
    # 4. Stoch
    lowest_low = low.rolling(window=14).min()
    highest_high = high.rolling(window=14).max()
    stoch = (close - lowest_low) / (highest_high - lowest_low.replace(0, np.nan)) * 100.0
    stoch = stoch.fillna(50)
    indicators['Stoch'] = stoch.rolling(window=3).mean()
    
    # 5. CCI
    indicators['CCI'] = calculate_cci(high, low, close, 10)
    
    # 6. MOM
    indicators['MOM'] = close - close.shift(10)
    
    # 7. OBV
    indicators['OBV'] = calculate_obv(close, volume)
    
    # 8. VWMACD
    ma_fast = calculate_vwma(close, volume, 12)
    ma_slow = calculate_vwma(close, volume, 26)
    indicators['VWMACD'] = ma_fast - ma_slow
    
    # 9. CMF
    indicators['CMF'] = calculate_cmf(high, low, close, volume, 21)
    
    # 10. MFI
    indicators['MFI'] = calculate_mfi(high, low, close, volume, 14)
    
    n = len(df)
    startpoint = 0 if dontconfirm else 1
    curr_idx = n - 1 - startpoint
    
    pl_indices = []
    for i in range(prd, n - 1 - prd):
        val = close.iloc[i]
        is_pl = True
        for j in range(1, prd + 1):
            if close.iloc[i - j] < val or close.iloc[i + j] <= val:
                is_pl = False
                break
        if is_pl:
            pl_indices.append(i)
            
    ph_indices = []
    for i in range(prd, n - 1 - prd):
        val = close.iloc[i]
        is_ph = True
        for j in range(1, prd + 1):
            if close.iloc[i - j] > val or close.iloc[i + j] >= val:
                is_ph = False
                break
        if is_ph:
            ph_indices.append(i)
            
    pl_indices = pl_indices[::-1]
    ph_indices = ph_indices[::-1]
    
    pos_div_list = []
    neg_div_list = []
    
    for name, ind_series in indicators.items():
        # Check Pos Regular
        for pl_idx in pl_indices[:maxpp]:
            dist = curr_idx - pl_idx
            if dist > maxbars:
                break
            if dist > 5:
                price_curr = close.iloc[curr_idx]
                price_prev = close.iloc[pl_idx]
                ind_curr = ind_series.iloc[curr_idx]
                ind_prev = ind_series.iloc[pl_idx]
                
                if ind_curr > ind_prev and price_curr < price_prev:
                    slope_ind = (ind_curr - ind_prev) / float(dist)
                    slope_price = (price_curr - price_prev) / float(dist)
                    arrived = True
                    for step in range(1, dist):
                        y_idx = pl_idx + step
                        virt_ind = ind_prev + slope_ind * step
                        virt_price = price_prev + slope_price * step
                        if ind_series.iloc[y_idx] < virt_ind or close.iloc[y_idx] < virt_price:
                            arrived = False
                            break
                    if arrived:
                        pos_div_list.append(name)
                        break
                        
        # Check Neg Regular
        for ph_idx in ph_indices[:maxpp]:
            dist = curr_idx - ph_idx
            if dist > maxbars:
                break
            if dist > 5:
                price_curr = close.iloc[curr_idx]
                price_prev = close.iloc[ph_idx]
                ind_curr = ind_series.iloc[curr_idx]
                ind_prev = ind_series.iloc[ph_idx]
                
                if ind_curr < ind_prev and price_curr > price_prev:
                    slope_ind = (ind_curr - ind_prev) / float(dist)
                    slope_price = (price_curr - price_prev) / float(dist)
                    arrived = True
                    for step in range(1, dist):
                        y_idx = ph_idx + step
                        virt_ind = ind_prev + slope_ind * step
                        virt_price = price_prev + slope_price * step
                        if ind_series.iloc[y_idx] > virt_ind or close.iloc[y_idx] > virt_price:
                            arrived = False
                            break
                    if arrived:
                        neg_div_list.append(name)
                        break
                        
    return pos_div_list, neg_div_list

def scan_canavar_nazli():
    tickers = get_bist_tickers()
    results = []
    
    logger.info(f"Starting CANAVAR-Nazli Hybrid scan for {len(tickers)} tickers...")
    try:
        df_batch = yf.download(tickers, period='1y', group_by='ticker', auto_adjust=True, progress=False)
    except Exception as e:
        logger.error(f"Error downloading batch in scan_canavar_nazli: {e}")
        return []
        
    for ticker_is in tickers:
        ticker_raw = ticker_is.replace(".IS", "")
        try:
            if len(tickers) > 1:
                if ticker_is not in df_batch.columns.levels[0]:
                    continue
                df = df_batch[ticker_is].dropna(subset=['Close'])
            else:
                df = df_batch.dropna(subset=['Close'])
                
            if len(df) < 100:
                continue
                
            # 1. CANAVAR WaveTrend
            wt1, wt2, wt_vwap = calculate_wavetrend(df['Close'], df['High'], df['Low'])
            wt_prev1 = float(wt1.iloc[-2])
            wt_prev2 = float(wt2.iloc[-2])
            wt_curr1 = float(wt1.iloc[-1])
            wt_curr2 = float(wt2.iloc[-1])
            
            wt_cross_up = wt_prev1 <= wt_prev2 and wt_curr1 > wt_curr2
            wt_cross_down = wt_prev1 >= wt_prev2 and wt_curr1 < wt_curr2
            wt_oversold = wt_curr2 <= -53.0
            wt_overbought = wt_curr2 >= 53.0
            
            # CANAVAR Money Flow
            range_hl = (df['High'] - df['Low']).replace(0, np.nan)
            mf_base = ((df['Close'] - df['Open']) / range_hl) * 150.0
            rsi_mfi = mf_base.rolling(window=60).mean() - 2.5
            rsi_mfi = rsi_mfi.fillna(0)
            mfi_curr = float(rsi_mfi.iloc[-1])
            
            # 2. nazli RROF & EV_Ratio
            rrof_s, rrof_signal, is_comp, is_eom, is_pos, n_price, n_vol = calculate_nazli_rrof(df)
            rrof_curr = float(rrof_s.iloc[-1])
            rrof_prev = float(rrof_s.iloc[-2])
            rrof_cross_up = rrof_prev <= 0 and rrof_curr > 0
            
            comp_curr = bool(is_comp.iloc[-1])
            eom_curr = bool(is_eom.iloc[-1])
            pos_curr = bool(is_pos.iloc[-1])
            
            # 3. Divergence v4
            pos_divs, neg_divs = check_divergence_v4(df)
            
            # Unified Scoring
            score = 0
            triggers = []
            
            # WT Cross Up
            if wt_cross_up:
                score += 30
                if wt_oversold:
                    score += 10
                    triggers.append("🌊 WaveTrend Aşırı Satım Kesişimi")
                else:
                    triggers.append("🌊 WaveTrend Kesişimi")
            elif wt_curr1 > wt_curr2 and wt_curr2 < -30.0:
                score += 15
                triggers.append("📈 WaveTrend Yukarı Dönüş")
                
            # RROF Cross Up / Positive
            if rrof_cross_up:
                score += 30
                triggers.append("⚡ RROF Sıfır Kesişimi")
            elif rrof_curr > 0 and rrof_curr > rrof_prev:
                score += 15
                triggers.append("⚡ RROF Pozitif Akış")
                
            # Divergences
            div_count = len(pos_divs)
            if div_count > 0:
                score += min(30, div_count * 10)
                triggers.append(f"🔍 {div_count} Göstergede Pozitif Uyumsuzluk ({', '.join(pos_divs)})")
                
            # MFI Area
            if mfi_curr > 0:
                score += 10
                triggers.append("💸 Pozitif Para Girişi (MFI)")
                
            # nazli compression / Ease of Move
            if eom_curr and pos_curr:
                score += 10
                triggers.append("🚀 Ease of Move Hareketi")
            elif comp_curr and pos_curr:
                score += 10
                triggers.append("🧱 Mal Toplama Sıkışması (Compression)")
                
            rating = "Nötr"
            if score >= 60:
                rating = "Güçlü Al 🚀"
            elif score >= 40:
                rating = "Al 🟢"
            elif wt_cross_down and wt_overbought:
                rating = "Güçlü Sat 🚨"
                score = -50
            elif rrof_prev > 0 and rrof_curr <= 0:
                rating = "Sat 🔴"
                score = -30
                
            if score >= 35 or rating in ["Al 🟢", "Güçlü Al 🚀"]:
                results.append({
                    'Ticker': ticker_raw,
                    'Price': round(float(df['Close'].iloc[-1]), 2),
                    'Change%': round(((df['Close'].iloc[-1] / df['Close'].iloc[-2]) - 1) * 100, 2),
                    'Score': score,
                    'Rating': rating,
                    'Triggers': triggers,
                    'WT2': round(wt_curr2, 2),
                    'RROF': round(rrof_curr, 2),
                    'MFI': round(mfi_curr, 2)
                })
        except Exception as ex:
            logger.error(f"Error checking CANAVAR-Nazli for {ticker_raw}: {ex}")
            
    return sorted(results, key=lambda x: x['Score'], reverse=True)




