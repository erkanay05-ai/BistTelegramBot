import os
import logging
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from dotenv import load_dotenv
import datetime
import pytz
from scanner import (
    scan_bist, scan_ceiling_prospects, scan_medium_term_trends,
    get_fundamentals, get_kap_news, get_akd_summary, 
    get_social_sentiment, calculate_atr
)
import engine_risk
import engine_viz
import yfinance as yf
import pandas as pd

USERS_FILE = "users.txt"
WATCHLIST_FILE = "watchlists.json"
ALARMS_FILE = "alarms.json"
SIGNAL_TRACKS_FILE = "signal_tracks.json"

def get_watchlists():
    if os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE, "r") as f:
            try: return json.load(f)
            except: return {}
    return {}

def save_watchlists(data):
    with open(WATCHLIST_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_alarms():
    if os.path.exists(ALARMS_FILE):
        with open(ALARMS_FILE, "r") as f:
            try: return json.load(f)
            except: return {}
    return {}

def save_alarms(data):
    with open(ALARMS_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_signal_tracks():
    if os.path.exists(SIGNAL_TRACKS_FILE):
        with open(SIGNAL_TRACKS_FILE, "r") as f:
            try: return json.load(f)
            except: return {}
    return {}

def save_signal_tracks(data):
    with open(SIGNAL_TRACKS_FILE, "w") as f:
        json.dump(data, f, indent=4)

def save_user(chat_id):
    chat_id = str(chat_id)
    users = set()
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            users = set(f.read().splitlines())
    if chat_id not in users:
        users.add(chat_id)
        with open(USERS_FILE, "w") as f:
            f.write("\n".join(users))

def get_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return f.read().splitlines()
    return []


# Load environment variables
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    save_user(chat_id)
    
    welcome_msg = (
        f"Merhaba {user.first_name}! 👋\n\n"
        "BIST Gelişmiş Komuta Botu'na hoş geldin.\n\n"
        "Komutlar:\n"
        "/scan - Hassas Hibrit Tarama\n"
        "/avci - Tavan Avcısı (Agresif)\n"
        "/trend - Orta Vade Trend Analizi\n"
        "/risk - Pozisyon & Stop-Loss Hesaplama\n"
        "/grafik - Teknik Analiz Grafiği\n"
        "/detay - Hisse Detaylı Analizi & Haberler\n"
        "/alarm - Fiyat Alarmı Kurma\n"
        "/alarm_liste - Aktif Alarmları Listele\n"
        "/alarm_sil - Fiyat Alarmını Sil\n"
        "/takipsinyal - Hisseyi Dönüş Sinyal Takibine Al\n"
        "/takipsinyal_liste - Sinyal Takiplerini Listele\n"
        "/takipsinyal_sil - Sinyal Takibini Durdur\n"
        "/sinyal - Anlık Dönüş Sinyalleri Analizi\n"
        "/ekle - Takip Listesine Ekle\n"
        "/sil - Takip Listesinden Sil\n"
        "/takip - Kişisel Takip Raporu\n"
        "/haber - Sosyal Medya Duyarlılığı\n"
        "/kap - Son KAP Bildirimleri\n"
        "/para - Aracı Kurum Dağılımı (AKD)\n"
        "/gcross - Golden Cross Taraması (Çoklu Periyot)\n"
        "/help - Bilgi"
    )
    await update.message.reply_text(welcome_msg)
 
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🚀 **Komut Kılavuzu:**\n\n"
        "• `/scan`: Teknik + Temel harmanlanmış tavan adayları.\n"
        "• `/avci`: Patlamaya hazır, tavan serisi potansiyeli yüksekler.\n"
        "• `/trend`: Orta vadeli, güvenli yükseliş trendindeki hisseler.\n"
        "• `/risk <ticker> <capital>`: Profesyonel pozisyon büyüklüğü ve stop önerisi.\n"
        "• `/grafik <ticker>`: Hareketli ortalamalar ve RSI içeren görsel grafik.\n"
        "• `/ekle <ticker>`: Hisseyi kişisel takip listenize ekler.\n"
        "• `/sil <ticker>`: Hisseyi takip listenizden çıkarır.\n"
        "• `/takip`: Takip listenizdeki hisselerin güncel durumlarını listeler.\n"
        "• `/detay <ticker>`: Belirli bir hissenin röntgenini çekin.\n"
        "• `/alarm <ticker> <hedef_fiyat>`: Belirli bir fiyata alarm kurun.\n"
        "• `/alarm_liste`: Aktif fiyat alarmlarını görün.\n"
        "• `/alarm_sil <ticker> <hedef_fiyat>`: Alarmı silin.\n"
        "• `/takipsinyal <ticker>`: Hisseyi dönüş sinyalleri için takibe alın.\n"
        "• `/takipsinyal_liste`: Takipteki sinyal listesini görün.\n"
        "• `/takipsinyal_sil <ticker>`: Hisseyi sinyal takibinden çıkarın.\n"
        "• `/sinyal <ticker>`: Hisse için güncel (RSI/MACD/SMA20) dönüş sinyallerini sorgulayın.\n"
        "• `/haber`: Sosyal mecralardaki 'bot sesini' ve trendi ölçer.\n"
        "• `/kap`: Borsa gündemini belirleyen sıcak gelişmeleri listeler.\n"
        "• `/para`: Kurumsal botların (BofA vb.) o anki yönünü özetler.\n"
        "• `/gcross`: Çoklu zaman diliminde (2s, 4s, Günlük, Haftalık) Golden Cross taraması."
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def kap_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("📢 Son KAP bildirimleri toplanıyor...")
    try:
        news = get_kap_news()
        if not news:
            await status_msg.edit_text("❌ Şu an haber akışı boş veya teknik bir sorun var.")
            return
        
        msg = "📢 **SON KAP BİLDİRİMLERİ**\n\n"
        for n in news:
            title = n.get('Title', 'Başlıksız Haber')
            link = n.get('Link', '#')
            msg += f"• [{title[:50]}...]({link})\n"
        
        await status_msg.edit_text(msg, parse_mode='Markdown', disable_web_page_preview=True)
    except Exception as e:
        logger.error(f"KAP Error: {e}")
        await status_msg.edit_text(f"❌ Haberler alınırken hata oluştu: {e}")

async def haber_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("🌐 Sosyal ağlar taranıyor...")
    sentiment = get_social_sentiment()
    
    msg = "🌐 **SOSYAL AĞ HABERLEŞMESİ**\n\n"
    for s in sentiment:
        msg += f"🔹 **{s['Platform']}**\nTrend: {s['Trend']} | Bot Yoğunluğu: {s['Bot_Yogunlugu']}\n"
    
    msg += "\n*Bot sesinin yüksekliği spekülatif harekete işaret edebilir.*"
    await status_msg.edit_text(msg, parse_mode='Markdown')

async def para_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("💸 Kurumsal para akışı analiz ediliyor...")
    akd = get_akd_summary()
    
    msg = "💸 **ARACI KURUM DAĞILIMI (AKD)**\n\n"
    for a in akd:
        msg += f"🏛 **{a['Kurum']}**\nYön: {a['Durum']} | **Bot İzi:** {a['Hacim']}\n"
    
    msg += "\n⚠️ *Gecikmeli veridir, sadece yön tayini içindir.*"
    await status_msg.edit_text(msg, parse_mode='Markdown')

async def ekle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Kullanım: `/ekle <hisse>`\nÖrn: `/ekle THYAO`", parse_mode='Markdown')
        return
    
    ticker = context.args[0].upper().replace(".IS", "")
    chat_id = str(update.effective_chat.id)
    
    data = get_watchlists()
    user_list = data.get(chat_id, [])
    
    if ticker not in user_list:
        user_list.append(ticker)
        data[chat_id] = user_list
        save_watchlists(data)
        await update.message.reply_text(f"✅ **{ticker}** takip listenize eklendi.")
    else:
        await update.message.reply_text(f"ℹ️ **{ticker}** zaten listenizde var.")

async def sil_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Kullanım: `/sil <hisse>`\nÖrn: `/sil THYAO`", parse_mode='Markdown')
        return
    
    ticker = context.args[0].upper().replace(".IS", "")
    chat_id = str(update.effective_chat.id)
    
    data = get_watchlists()
    user_list = data.get(chat_id, [])
    
    if ticker in user_list:
        user_list.remove(ticker)
        data[chat_id] = user_list
        save_watchlists(data)
        await update.message.reply_text(f"🗑 **{ticker}** listenizden çıkarıldı.")
    else:
        await update.message.reply_text(f"❌ **{ticker}** listenizde bulunamadı.")

async def takip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    data = get_watchlists()
    user_list = data.get(chat_id, [])
    
    if not user_list:
        await update.message.reply_text("🛒 Takip listeniz şu an boş. `/ekle` komutuyla hisse ekleyebilirsiniz.")
        return
    
    status_msg = await update.message.reply_text("📈 Takip listenizdeki hisseler analiz ediliyor...")
    
    try:
        tickers_is = [t + ".IS" for t in user_list]
        # Download data at once for speed
        df_batch = yf.download(tickers_is, period='5d', progress=False)
        
        report = "📋 **KİŞİSEL TAKİP RAPORU**\n"
        report += "───────────────────\n"
        
        for t in user_list:
            try:
                # Handle single ticker results vs batch dataframe
                if len(user_list) > 1:
                    price = df_batch['Close'][t + ".IS"].iloc[-1]
                    prev_close = df_batch['Close'][t + ".IS"].iloc[-2]
                else:
                    price = df_batch['Close'].iloc[-1]
                    prev_close = df_batch['Close'].iloc[-2]
                
                change = ((price / prev_close) - 1) * 100
                emoji = "🚀" if change > 0 else "📉"
                report += f"{emoji} **{t}**: {price:.2f} TL (%{change:+.2f})\n"
            except:
                report += f"❌ **{t}**: Veri alınamadı.\n"
        
        report += "───────────────────\n"
        report += "💡 _Daha detaylı analiz için `/grafik <hisse>` yazabilirsiniz._"
        await status_msg.edit_text(report, parse_mode='Markdown')
    except Exception as e:
        await status_msg.edit_text(f"❌ Rapor oluşturulurken hata: {e}")

async def grafik_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Kullanım: `/grafik <ticker>`\nÖrn: `/grafik THYAO`", parse_mode='Markdown')
        return
    
    ticker_raw = context.args[0].upper()
    ticker = ticker_raw + ".IS" if not ticker_raw.endswith(".IS") else ticker_raw
    status_msg = await update.message.reply_text(f"🎨 **{ticker_raw}** için teknik grafik çiziliyor...")
    
    try:
        t = yf.Ticker(ticker)
        df = t.history(period="1y")
        if df.empty:
            await status_msg.edit_text("❌ Veri bulunamadı.")
            return

        # Create chart using new engine
        chart_buf = engine_viz.create_tech_chart(ticker_raw, df)
        
        # Send photo
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=chart_buf,
            caption=f"📈 **{ticker_raw}** - Teknik Görünüm (1 Yıllık)\nSMA 50 (Sarı), SMA 200 (Pembe) ve RSI göstergeleri dahildir.",
            parse_mode='Markdown'
        )
        await status_msg.delete()
        
    except Exception as e:
        await status_msg.edit_text(f"❌ Grafik oluşturulurken hata: {e}")

async def risk_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("❌ Kullanım: `/risk <ticker> <sermaye>`\nÖrn: `/risk THYAO 50000`", parse_mode='Markdown')
        return
    
    ticker_raw = context.args[0].upper()
    ticker = ticker_raw + ".IS" if not ticker_raw.endswith(".IS") else ticker_raw
    try:
        capital = float(context.args[1])
    except:
        await update.message.reply_text("❌ Lütfen geçerli bir sermaye tutarı girin.")
        return

    status_msg = await update.message.reply_text(f"🛡️ **{ticker_raw}** için risk analizi yapılıyor...")
    
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="1mo")
        if hist.empty:
            await status_msg.edit_text("❌ Veri bulunamadı.")
            return

        price = round(hist['Close'].iloc[-1], 2)
        atr = calculate_atr(hist)
        
        # Calculate risk
        risk_calc = engine_risk.calculate_atr_risk(price, atr, capital)
        
        msg = (
            f"🛡️ **RİSK YÖNETİMİ: {ticker_raw}**\n\n"
            f"💰 **Anlık Fiyat:** {price} TL\n"
            f"💵 **Sermaye:** {capital:,.2f} TL\n"
            f"📦 **Önerilen Adet:** {risk_calc['num_shares']} Lot\n"
            f"💳 **Toplam Maliyet:** {risk_calc['total_cost']:,.2f} TL\n"
            f"⛔ **Stop-Loss (2-ATR):** {risk_calc['stop_loss_price']} TL (-%{risk_calc['stop_loss_pct']})\n"
            f"⚠️ **İşlem Başı Risk:** {risk_calc['risk_amount']} TL (%1)\n\n"
            f"⚖️ *Unutmayın: Risk yönetimi, kazanç stratejisinden daha önemlidir.*"
        )
        await status_msg.edit_text(msg, parse_mode='Markdown')
    except Exception as e:
        await status_msg.edit_text(f"❌ Hata: {e}")

async def detay_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Lütfen bir hisse kodu yazın. Örn: `/detay THYAO`", parse_mode='Markdown')
        return
    
    ticker_raw = context.args[0].upper()
    ticker = ticker_raw + ".IS" if not ticker_raw.endswith(".IS") else ticker_raw
    status_msg = await update.message.reply_text(f"📊 **{ticker_raw}** verileri analiz ediliyor...")
    
    try:
        # Get fundamental and technical data
        fund = get_fundamentals(ticker)
        t = yf.Ticker(ticker)
        hist = t.history(period="1y")
        
        if hist.empty:
            await status_msg.edit_text("❌ Veri bulunamadı. Kodun doğruluğunu kontrol edin.")
            return

        last_price = round(hist['Close'].iloc[-1], 2)
        change = round(((hist['Close'].iloc[-1] / hist['Close'].iloc[-2]) - 1) * 100, 2)
        low_52 = round(hist['Low'].min(), 2)
        high_52 = round(hist['High'].max(), 2)
        
        # Calculate VWAP
        from scanner import calculate_rolling_vwap, calculate_intraday_vwap
        vwap20_series = calculate_rolling_vwap(hist, window=20)
        last_vwap20 = round(vwap20_series.iloc[-1], 2)
        
        try:
            hist_1h = t.history(period="5d", interval="1h")
            intraday_vwap = calculate_intraday_vwap(hist_1h)
        except Exception as e:
            logger.error(f"Error fetching hourly data for VWAP: {e}")
            intraday_vwap = 0
            
        if intraday_vwap > 0:
            if last_price >= intraday_vwap:
                vwap_status = f"🟢 Alıcılar Üstün (Fiyat {intraday_vwap} TL üstünde)"
            else:
                vwap_status = f"🔴 Satıcılar Üstün (Fiyat {intraday_vwap} TL altında)"
        else:
            vwap_status = "Veri Yok ⚖️"
        
        # Simple RSI calculation for detail
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rsi = round(100 - (100 / (1 + (gain / loss))).iloc[-1], 2)
        
        # Technical Rating and Expert Commentary
        from scanner import calculate_technical_rating, get_expert_commentary
        # Calculate full df features to get accurate rating
        df = hist.copy()
        df['SMA50'] = df['Close'].rolling(window=50).mean()
        df['SMA200'] = df['Close'].rolling(window=200).mean()
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['RSI'] = rsi
        
        # Golden Cross check
        has_gc = False
        if len(df) >= 15:
            recent = df.tail(15)
            for i in range(1, len(recent)):
                if float(recent['SMA50'].iloc[i-1]) <= float(recent['SMA200'].iloc[i-1]) and float(recent['SMA50'].iloc[i]) > float(recent['SMA200'].iloc[i]):
                    has_gc = True
                    break
                    
        rating = calculate_technical_rating(df, golden_cross=has_gc)
        expert_comment = get_expert_commentary(ticker_raw, fund, last_price, rsi, rating, golden_cross=has_gc)

        msg = f"📊 **DETAYLI ANALİZ: {ticker_raw}**\n\n"
        msg += f"💰 **Fiyat:** {last_price} TL (%{change})\n"
        msg += f"📐 **20 Günlük VWAP:** {last_vwap20} TL\n"
        msg += f"⚡ **Gün İçi Yön:** {vwap_status}\n"
        msg += f"📏 **RSI (14):** {rsi}\n"
        msg += f"🏔 **52H En Düşük/Yüksek:** {low_52} - {high_52}\n"
        msg += f"🏗 **Sektör:** {fund['Sector']}\n"
        msg += f"📈 **F/K:** {fund['FK']} | **PD/DD:** {fund['PD_DD']}\n"
        msg += f"💵 **Temettü Verimi:** %{fund['DividendYield']}\n\n"
        
        msg += f"🎛 **Teknik Sinyal:** **{rating}**\n"
        msg += f"🧑‍💼 **Uzman Görüşü:** {expert_comment}\n"
        
        valid_news = [n for n in fund.get('News', []) if isinstance(n, dict) and n.get('Title') and n.get('Link')]
        if valid_news:
            msg += "\n📰 **SON HABERLER:**\n"
            for n in valid_news[:2]:
                title = n['Title']
                link = n['Link']
                safe_title = title[:45] if title else "Haber"
                msg += f"• [{safe_title}...]({link})\n"
        
        logger.info(f"Detail check for {ticker_raw} by {update.effective_user.name}")
        await status_msg.edit_text(msg, parse_mode='Markdown', disable_web_page_preview=True)
        
    except Exception as e:
        logger.error(f"Error in detay_command for {ticker_raw}: {e}")
        await status_msg.edit_text(f"❌ Analiz sırasında bir hata oluştu: {e}")

async def gcross_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text(
        "🔍 **Golden Cross Kesişim Taraması Başlatıldı...**\n"
        "Haftalık, Günlük, 4 Saatlik ve 2 Saatlik periyotlar taranıyor.\n"
        "Bu işlem yaklaşık 15-20 saniye sürebilir, lütfen bekleyin.",
        parse_mode='Markdown'
    )
    try:
        from scanner import scan_all_golden_cross
        results = scan_all_golden_cross(lookback=5)
        
        msg = "⭐ **BIST MULTI-TIMEFRAME GOLDEN CROSS RAPORU** ⭐\n"
        msg += "📅 *Son 5 mum içerisinde SMA 50/200 yukarı yönlü kesişen hisseler:*\n\n"
        
        sections = [
            ('weekly', '📈 Haftalık (Weekly)'),
            ('daily', '📅 Günlük (Daily)'),
            ('4h', '⏱ 4 Saatlik (4H)'),
            ('2h', '⏱ 2 Saatlik (2H)')
        ]
        
        for key, title in sections:
            msg += f"**{title}**\n"
            items = results.get(key, [])
            if items:
                for item in items:
                    msg += f"• **{item['Ticker']}** | {item['CrossPrice']} ➔ {item['Price']} TL | {item['Time']}\n"
            else:
                msg += "• *Crossover tespit edilmedi.*\n"
            msg += "\n"
            
        msg += "⚠️ *Not: Golden Cross boğa sinyalidir, ancak diğer teknik verilerle doğrulanmalıdır.*"
        
        await status_msg.edit_text(msg, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in gcross_command: {e}")
        await status_msg.edit_text(f"❌ Tarama sırasında bir hata oluştu: {e}")

async def trend_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("🔎 **Orta Vadeli Trend Taraması Başlatıldı.**\n200 günlük ortalamalar ve trend güçleri analiz ediliyor...")
    try:
        results = scan_medium_term_trends()
        if not results:
            await status_msg.edit_text("❌ Kriterlere uygun güvenli bir trend bulunamadı.")
            return

        msg = "📈 **ORTA VADELİ TREND LİDERLERİ**\n"
        msg += "───────────────────\n"
        for item in results[:8]: # Top 8 trends
            emoji = "✅" if item['Strength'] == "Yüksek" else "🟡"
            safe_emoji = "🛡️" if item['Status'] == "Güvenli" else "⚠️"
            
            msg += f"{emoji} **{item['Ticker']}** | Güç: {item['Strength']}\n"
            msg += f"  Fiyat: {item['Price']} | 200 Ort: {item['SMA200']}\n"
            msg += f"  Mesafe: %{item['Distance%']} {safe_emoji}\n\n"
        
        msg += "───────────────────\n"
        msg += "🛡️: SMA 200'e yakın, güvenli bölge.\n"
        msg += "⚠️: SMA 200'den çok uzaklaşmış, düzeltme riski."
        
        await status_msg.edit_text(msg, parse_mode='Markdown')
    except Exception as e:
        await status_msg.edit_text(f"❌ Trend taraması sırasında hata: {e}")

async def avci_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("🎯 **Tavan Avcısı Modülü Devreye Girdi.**\nHacim ve sıkışma paternleri taranıyor...")
    try:
        results = scan_ceiling_prospects()
        if not results:
            await status_msg.edit_text("❌ Kriterlere uygun agresif aday bulunamadı.")
            return

        msg = "🎯 **TAVAN AVCISI (POTANSİYEL SERİ ADAYLARI)**\n"
        msg += "───────────────────\n"
        for item in results:
            fire = "🔥" * (item['Score'] // 20)
            msg += f"• **{item['Ticker']}** | Skor: {item['Score']} {fire}\n"
            msg += f"  Fiyat: {item['Price']} | Hacim Artışı: x{item['VolRatio']}\n"
            msg += f"  Sıkışma: %{item['Tightness%']} | RSI: {item['RSI']}\n\n"
        
        msg += "───────────────────\n"
        msg += "⚠️ *Yüksek riskli taramadır. 2-3 gün tavan serisi potansiyeli olan hacim odaklı adaylardır.*"
        
        await status_msg.edit_text(msg, parse_mode='Markdown')
    except Exception as e:
        await status_msg.edit_text(f"❌ Avcı taraması sırasında hata: {e}")

async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("🔎 Hassas tarama başlatıldı. Toplu veri indiriliyor, lütfen bekleyin...")
    try:
        gc, mom = scan_bist()
        final_msg = "📈 **GOLDEN CROSS (YENİ)**\n"
        if gc:
            for item in gc: final_msg += f"• {item['Ticker']}: {item['Price']} TL\n"
        else: final_msg += "Yeni kesişim yok.\n"
            
        final_msg += "\n🚀 **GELİŞMİŞ TEKNİK TARAMA (Potansiyeli Yüksekler)**\n"
        if mom:
            # Sadece en yüksek skorlu ilk 10 hisseyi göster
            for item in mom[:10]:
                fire = "🔥" * (item['Score'] // 25)
                bot_icon = "🤖" if item.get('Bot_Score', 0) > 30 else ""
                gc_icon = "📈" if item.get('Is_Golden_Cross', False) else ""
                rating = item.get('Tech_Rating', 'Nötr')
                
                final_msg += f"• **{item['Ticker']}** | {rating} {gc_icon} | Skor: {item['Score']} {fire} {bot_icon}\n"
                final_msg += f"  Fiyat: {item['Price']} | Hedef: {item['Target1']}\n"
        else: final_msg += "Kriterlere uygun hisse bulunamadı."
        
        await status_msg.edit_text(final_msg, parse_mode='Markdown')
    except Exception as e:
        await status_msg.edit_text(f"❌ Hata: {e}")

async def send_daily_report(context: ContextTypes.DEFAULT_TYPE):
    logger.info("Günlük 09:55 raporu hazırlanıyor...")
    
    # 1. Tavan Tarama
    msg = "🌞 **GÜNLÜK SABAH BÜLTENİ (09:55)** 🌞\n\n"
    
    try:
        gc, mom = scan_bist()
        msg += "📈 **YENİ GOLDEN CROSS (50/200)**\n"
        if gc:
            for item in gc: msg += f"• {item['Ticker']} ({item['Price']} TL)\n"
        else: msg += "Yok\n"
        
        msg += "\n🚀 **TAVAN & PATLAMA ADAYLARI**\n"
        if mom:
            for item in mom[:5]:
                fire = "🔥" * (item['Score'] // 25)
                msg += f"• **{item['Ticker']}** | {item['Price']} TL | Skor: {item['Score']} {fire}\n"
        else: msg += "Liste boş.\n"
    except Exception as e:
        logger.error(f"Daily tarama hatası: {e}")
        msg += "Taramada geçici bir hata oluştu.\n"

    # 2. Sosyal Medya Bot ve Duyarlılık
    msg += "\n🌐 **SOSYAL MEDYA & BOT TRENDİ**\n"
    try:
        sentiment = get_social_sentiment()
        for s in sentiment:
            if "Genel" in s['Platform'] or "Twitter" in s['Platform']:
                msg += f"• {s['Platform'].split()[0]}: {s['Trend']} (Bot: {s['Bot_Yogunlugu']})\n"
    except Exception as e:
        msg += "Sosyal veri alınamadı.\n"
        
    # 3. AKD Özeti (Para Girişi)
    msg += "\n💸 **PARA GİRİŞİ (AKD LİDERLER)**\n"
    try:
        akd = get_akd_summary()
        for a in akd[:3]:
            msg += f"• {a['Kurum'].split()[0]}: {a['Durum']} | İzi: {a['Hacim']}\n"
    except Exception as e:
        msg += "AKD veri alınamadı.\n"
        
    users = get_users()
    logger.info(f"{len(users)} kullanıcıya sabah raporu gönderiliyor.")
    for chat_id in users:
        try:
            await context.bot.send_message(chat_id=int(chat_id), text=msg, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Cannot send message to {chat_id}: {e}")

# Helper functions and command handlers for alarms & signal tracking
async def alarm_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("❌ Kullanım: `/alarm <hisse> <hedef_fiyat>`\nÖrn: `/alarm THYAO 310`", parse_mode='Markdown')
        return
    
    ticker_raw = context.args[0].upper().replace(".IS", "")
    ticker = ticker_raw + ".IS"
    chat_id = str(update.effective_chat.id)
    
    try:
        target = float(context.args[1].replace(",", "."))
    except:
        await update.message.reply_text("❌ Lütfen geçerli bir hedef fiyat girin.")
        return
        
    status_msg = await update.message.reply_text(f"⏳ **{ticker_raw}** için alarm kuruluyor...")
    
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="1d")
        if hist.empty:
            await status_msg.edit_text("❌ Hisse verisi bulunamadı. Lütfen kodu kontrol edin.")
            return
        
        current_price = round(float(hist['Close'].iloc[-1]), 2)
        condition = "above" if target > current_price else "below"
        cond_text = "yukarı kesmesini" if condition == "above" else "aşağı kesmesini"
        
        alarms = get_alarms()
        user_alarms = alarms.get(chat_id, [])
        
        for a in user_alarms:
            if a['ticker'] == ticker_raw and abs(a['target'] - target) < 0.01:
                await status_msg.edit_text(f"ℹ️ **{ticker_raw}** için **{target} TL** seviyesinde zaten aktif bir alarmınız var.")
                return
                
        user_alarms.append({
            "ticker": ticker_raw,
            "target": target,
            "condition": condition,
            "created_price": current_price,
            "active": True
        })
        alarms[chat_id] = user_alarms
        save_alarms(alarms)
        
        await status_msg.edit_text(
            f"🔔 **Alarm Kuruldu!**\n"
            f"📈 **Hisse:** {ticker_raw}\n"
            f"💵 **Anlık Fiyat:** {current_price} TL\n"
            f"🎯 **Hedef Fiyat:** {target} TL ({cond_text} bekliyor.)"
        )
    except Exception as e:
        logger.error(f"Error in alarm_command: {e}")
        await status_msg.edit_text(f"❌ Alarm kurulurken hata oluştu: {e}")

async def alarm_liste_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    alarms = get_alarms()
    user_alarms = alarms.get(chat_id, [])
    
    if not user_alarms:
        await update.message.reply_text("🔔 Aktif fiyat alarmınız bulunmamaktadır.")
        return
        
    msg = "📋 **AKTİF FİYAT ALARMLARINIZ**\n\n"
    for i, a in enumerate(user_alarms, 1):
        cond_emoji = "📈" if a['condition'] == "above" else "📉"
        msg += f"{i}. {cond_emoji} **{a['ticker']}** ➔ {a['target']} TL (Kurulum: {a['created_price']} TL)\n"
        
    msg += "\n*Alarmı silmek için: `/alarm_sil <hisse> <hedef_fiyat>`*"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def alarm_sil_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("❌ Kullanım: `/alarm_sil <hisse> <hedef_fiyat>`\nÖrn: `/alarm_sil THYAO 310`", parse_mode='Markdown')
        return
        
    ticker_raw = context.args[0].upper().replace(".IS", "")
    chat_id = str(update.effective_chat.id)
    try:
        target = float(context.args[1].replace(",", "."))
    except:
        await update.message.reply_text("❌ Lütfen geçerli bir hedef fiyat girin.")
        return
        
    alarms = get_alarms()
    user_alarms = alarms.get(chat_id, [])
    
    found = False
    new_alarms = []
    for a in user_alarms:
        if a['ticker'] == ticker_raw and abs(a['target'] - target) < 0.01:
            found = True
        else:
            new_alarms.append(a)
            
    if found:
        alarms[chat_id] = new_alarms
        save_alarms(alarms)
        await update.message.reply_text(f"🗑 **{ticker_raw}** için **{target} TL** alarmı silindi.")
    else:
        await update.message.reply_text(f"❌ **{ticker_raw}** için **{target} TL** alarmı bulunamadı.")

async def takipsinyal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Kullanım: `/takipsinyal <hisse>`\nÖrn: `/takipsinyal THYAO`", parse_mode='Markdown')
        return
        
    ticker_raw = context.args[0].upper().replace(".IS", "")
    ticker = ticker_raw + ".IS"
    chat_id = str(update.effective_chat.id)
    
    status_msg = await update.message.reply_text(f"⏳ **{ticker_raw}** sinyal takibine alınıyor...")
    
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="1mo")
        if hist.empty:
            await status_msg.edit_text("❌ Hisse verisi bulunamadı. Lütfen kodu kontrol edin.")
            return
            
        tracks = get_signal_tracks()
        user_tracks = tracks.get(chat_id, [])
        
        if any(tr['ticker'] == ticker_raw for tr in user_tracks):
            await status_msg.edit_text(f"ℹ️ **{ticker_raw}** zaten sinyal takip listenizde var.")
            return
            
        df = hist.copy()
        df['SMA20'] = df['Close'].rolling(window=20).mean()
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / loss)))
        
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        
        last = df.iloc[-1]
        
        user_tracks.append({
            "ticker": ticker_raw,
            "last_rsi": float(last['RSI']) if not pd.isna(last['RSI']) else 50.0,
            "last_macd_diff": float(last['MACD'] - last['MACD_Signal']) if not (pd.isna(last['MACD']) or pd.isna(last['MACD_Signal'])) else 0.0,
            "last_above_sma20": bool(last['Close'] > last['SMA20']) if not (pd.isna(last['Close']) or pd.isna(last['SMA20'])) else True
        })
        tracks[chat_id] = user_tracks
        save_signal_tracks(tracks)
        
        await status_msg.edit_text(
            f"🔄 **{ticker_raw} Sinyal Takibinde!**\n"
            f"Bot, bu hissede günlük/saatlik periyotta RSI dönüşleri veya MACD kesişimleri gibi **yukarı/aşağı dönüş sinyalleri** oluştuğunda size otomatik olarak bildirim gönderecektir. 🤖📈"
        )
    except Exception as e:
        logger.error(f"Error in takipsinyal_command: {e}")
        await status_msg.edit_text(f"❌ Takip başlatılırken hata oluştu: {e}")

async def takipsinyal_liste_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    tracks = get_signal_tracks()
    user_tracks = tracks.get(chat_id, [])
    
    if not user_tracks:
        await update.message.reply_text("🔄 Sinyal takibinde hisseniz bulunmamaktadır.")
        return
        
    msg = "📋 **SİNYAL TAKİP LİSTENİZ**\n\n"
    for i, t in enumerate(user_tracks, 1):
        msg += f"{i}. 🔄 **{t['ticker']}**\n"
        
    msg += "\n*Takip listesinden çıkarmak için: `/takipsinyal_sil <hisse>`*"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def takipsinyal_sil_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Kullanım: `/takipsinyal_sil <hisse>`\nÖrn: `/takipsinyal_sil THYAO`", parse_mode='Markdown')
        return
        
    ticker_raw = context.args[0].upper().replace(".IS", "")
    chat_id = str(update.effective_chat.id)
    
    tracks = get_signal_tracks()
    user_tracks = tracks.get(chat_id, [])
    
    found = False
    new_tracks = []
    for t in user_tracks:
        if t['ticker'] == ticker_raw:
            found = True
        else:
            new_tracks.append(t)
            
    if found:
        tracks[chat_id] = new_tracks
        save_signal_tracks(tracks)
        await update.message.reply_text(f"🗑 **{ticker_raw}** sinyal takip listesinden çıkarıldı.")
    else:
        await update.message.reply_text(f"❌ **{ticker_raw}** sinyal takip listenizde bulunamadı.")

async def sinyal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Kullanım: `/sinyal <hisse>`\nÖrn: `/sinyal THYAO`", parse_mode='Markdown')
        return
        
    ticker_raw = context.args[0].upper().replace(".IS", "")
    ticker = ticker_raw + ".IS"
    status_msg = await update.message.reply_text(f"🔍 **{ticker_raw}** için dönüş sinyalleri taranıyor...")
    
    try:
        t = yf.Ticker(ticker)
        hist_d = t.history(period="1mo", interval="1d")
        hist_h = t.history(period="5d", interval="1h")
        
        if hist_d.empty:
            await status_msg.edit_text("❌ Veri bulunamadı. Lütfen kodu kontrol edin.")
            return
            
        from scanner import check_reversal_signals
        sig_d = check_reversal_signals(hist_d)
        sig_h = check_reversal_signals(hist_h) if not hist_h.empty else {"bullish": [], "bearish": []}
        
        msg = f"🔍 **DÖNÜŞ SİNYAL RAPORU: {ticker_raw}**\n\n"
        
        msg += "📅 **Günlük Grafikte (1D):**\n"
        if sig_d["bullish"]:
            for s in sig_d["bullish"]: msg += f"• {s}\n"
        if sig_d["bearish"]:
            for s in sig_d["bearish"]: msg += f"• {s}\n"
        if not sig_d["bullish"] and not sig_d["bearish"]:
            msg += "• *Herhangi bir günlük dönüş sinyali yok.*\n"
            
        msg += "\n⏱ **Saatlik Grafikte (1H):**\n"
        if sig_h["bullish"]:
            for s in sig_h["bullish"]: msg += f"• {s}\n"
        if sig_h["bearish"]:
            for s in sig_h["bearish"]: msg += f"• {s}\n"
        if not sig_h["bullish"] and not sig_h["bearish"]:
            msg += "• *Herhangi bir saatlik dönüş sinyali yok.*\n"
            
        await status_msg.edit_text(msg, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error in sinyal_command: {e}")
        await status_msg.edit_text(f"❌ Sinyal analizi sırasında hata: {e}")

async def channel_post_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.channel_post:
        return
        
    chat_id = str(update.channel_post.chat.id)
    save_user(chat_id)
    
    text = update.channel_post.text
    if text and text.startswith('/'):
        parts = text.split()
        cmd = parts[0][1:].split('@')[0].lower()
        context.args = parts[1:]
        
        handlers = {
            'start': start,
            'help': help_command,
            'scan': scan,
            'kap': kap_command,
            'haber': haber_command,
            'para': para_command,
            'detay': detay_command,
            'risk': risk_command,
            'grafik': grafik_command,
            'avci': avci_command,
            'trend': trend_command,
            'ekle': ekle_command,
            'sil': sil_command,
            'takip': takip_command,
            'gcross': gcross_command,
            'alarm': alarm_command,
            'alarm_liste': alarm_liste_command,
            'alarm_sil': alarm_sil_command,
            'takipsinyal': takipsinyal_command,
            'takipsinyal_liste': takipsinyal_liste_command,
            'takipsinyal_sil': takipsinyal_sil_command,
            'sinyal': sinyal_command
        }
        
        if cmd in handlers:
            original_message = update.message
            update.message = update.channel_post
            try:
                await handlers[cmd](update, context)
            except Exception as e:
                logger.error(f"Error executing command {cmd} in channel: {e}")
            finally:
                update.message = original_message

async def check_alarms_and_signals_job(context: ContextTypes.DEFAULT_TYPE):
    try:
        tr_tz = pytz.timezone('Europe/Istanbul')
        now_tr = datetime.datetime.now(tr_tz)
        if now_tr.weekday() > 4:
            return  # Weekend, don't check
            
        current_time = now_tr.time()
        start_time = datetime.time(hour=9, minute=55)
        end_time = datetime.time(hour=18, minute=20)
        
        if not (start_time <= current_time <= end_time):
            return  # Outside trading hours
    except Exception as tz_err:
        logger.error(f"Error checking timezone for job: {tz_err}")
        pass

    logger.info("Running background alarms and signals check...")
    
    alarms = get_alarms()
    active_tickers = set()
    for user_alarms in alarms.values():
        for a in user_alarms:
            if a.get('active', True):
                active_tickers.add(a['ticker'])
                
    tracks = get_signal_tracks()
    for user_tracks in tracks.values():
        for t in user_tracks:
            active_tickers.add(t['ticker'])
            
    if not active_tickers:
        return
        
    tickers_is = [tk + ".IS" for tk in active_tickers]
    try:
        df_batch_d = yf.download(tickers_is, period='1mo', interval='1d', group_by='ticker', progress=False)
        df_batch_h = yf.download(tickers_is, period='5d', interval='1h', group_by='ticker', progress=False)
    except Exception as e:
        logger.error(f"Background check download error: {e}")
        return

    alarms_changed = False
    for chat_id, user_alarms in list(alarms.items()):
        new_alarms = []
        for a in user_alarms:
            ticker = a['ticker']
            ticker_is = ticker + ".IS"
            try:
                if len(tickers_is) > 1:
                    price = float(df_batch_d[ticker_is]['Close'].dropna().iloc[-1])
                else:
                    price = float(df_batch_d['Close'].dropna().iloc[-1])
                
                price = round(price, 2)
                target = a['target']
                condition = a['condition']
                
                triggered = False
                if condition == "above" and price >= target:
                    triggered = True
                elif condition == "below" and price <= target:
                    triggered = True
                    
                if triggered:
                    alarms_changed = True
                    cond_msg = "YUKARI" if condition == "above" else "AŞAĞI"
                    alert_emoji = "🚨" if condition == "below" else "🔔"
                    alert_msg = (
                        f"{alert_emoji} **FİYAT ALARMI TETİKLENDİ!**\n\n"
                        f"📈 **Hisse:** {ticker}\n"
                        f"🎯 **Hedef Seviye:** {target} TL\n"
                        f"⚡ **Mevcut Fiyat:** {price} TL ({cond_msg} kırıldı!)\n"
                    )
                    try:
                        await context.bot.send_message(chat_id=int(chat_id), text=alert_msg, parse_mode='Markdown')
                    except Exception as err:
                        logger.error(f"Cannot send alarm alert to {chat_id}: {err}")
                else:
                    new_alarms.append(a)
            except Exception as ex:
                logger.error(f"Error checking alarm for {ticker}: {ex}")
                new_alarms.append(a)
        if len(user_alarms) != len(new_alarms):
            alarms[chat_id] = new_alarms
            alarms_changed = True
            
    if alarms_changed:
        save_alarms(alarms)

    from scanner import check_reversal_signals
    tracks_changed = False
    for chat_id, user_tracks in list(tracks.items()):
        new_user_tracks = []
        for t in user_tracks:
            ticker = t['ticker']
            ticker_is = ticker + ".IS"
            try:
                if len(tickers_is) > 1:
                    df_d = df_batch_d[ticker_is].dropna()
                    df_h = df_batch_h[ticker_is].dropna()
                else:
                    df_d = df_batch_d.dropna()
                    df_h = df_batch_h.dropna()
                
                # Exclude the active (unclosed) live candle to prevent whipsaws/spam
                if len(df_d) > 1:
                    df_d = df_d.iloc[:-1]
                if len(df_h) > 1:
                    df_h = df_h.iloc[:-1]
                
                sig_d = check_reversal_signals(df_d) if not df_d.empty else {"bullish": [], "bearish": []}
                
                last_rsi = t.get('last_rsi', 50.0)
                last_macd_diff = t.get('last_macd_diff', 0.0)
                last_above_sma20 = t.get('last_above_sma20', True)
                
                c_rsi = float(df_d['RSI'].iloc[-1]) if 'RSI' in df_d.columns else 50.0
                c_macd = float(df_d['MACD'].iloc[-1]) if 'MACD' in df_d.columns else 0.0
                c_sig = float(df_d['MACD_Signal'].iloc[-1]) if 'MACD_Signal' in df_d.columns else 0.0
                c_macd_diff = c_macd - c_sig
                c_close = float(df_d['Close'].iloc[-1])
                c_sma20 = float(df_d['SMA20'].iloc[-1]) if 'SMA20' in df_d.columns else c_close
                c_above_sma20 = c_close > c_sma20
                
                alerts = []
                
                if last_rsi < 30 and c_rsi >= 30:
                    alerts.append(f"🟢 **{ticker}**: Günlük RSI aşırı satım bölgesinden yukarı döndü (%{round(c_rsi, 1)})!")
                elif last_rsi > 70 and c_rsi <= 70:
                    alerts.append(f"🔴 **{ticker}**: Günlük RSI aşırı alım bölgesinden aşağı döndü (%{round(c_rsi, 1)})!")
                    
                if last_macd_diff <= 0 and c_macd_diff > 0:
                    alerts.append(f"🟢 **{ticker}**: Günlük MACD yukarı yönlü kesişti (Al Sinyali)!")
                elif last_macd_diff >= 0 and c_macd_diff < 0:
                    alerts.append(f"🔴 **{ticker}**: Günlük MACD aşağı yönlü kesişti (Sat Sinyali)!")
                    
                if not last_above_sma20 and c_above_sma20:
                    alerts.append(f"🟢 **{ticker}**: Fiyat 20 günlük hareketli ortalamayı (SMA 20) yukarı kırdı!")
                elif last_above_sma20 and not c_above_sma20:
                    alerts.append(f"🔴 **{ticker}**: Fiyat 20 günlük hareketli ortalamayı (SMA 20) aşağı kırdı!")
                    
                if not df_h.empty:
                    c_rsi_h = float(df_h['RSI'].iloc[-1]) if 'RSI' in df_h.columns else 50.0
                    p_rsi_h = float(df_h['RSI'].iloc[-2]) if 'RSI' in df_h.columns else 50.0
                    
                    if p_rsi_h < 30 and c_rsi_h >= 30:
                        alerts.append(f"🟢 **{ticker}**: Saatlik grafikte RSI yukarı döndü (%{round(c_rsi_h, 1)})!")
                    elif p_rsi_h > 70 and c_rsi_h <= 70:
                        alerts.append(f"🔴 **{ticker}**: Saatlik grafikte RSI aşağı döndü (%{round(c_rsi_h, 1)})!")
                
                if alerts:
                    tracks_changed = True
                    alert_msg = f"🔄 **DÖNÜŞ SİNYALİ UYARISI: {ticker}** 🔄\n\n"
                    alert_msg += "\n".join(alerts)
                    try:
                        await context.bot.send_message(chat_id=int(chat_id), text=alert_msg, parse_mode='Markdown')
                    except Exception as err:
                        logger.error(f"Cannot send signal alert to {chat_id}: {err}")
                
                new_user_tracks.append({
                    "ticker": ticker,
                    "last_rsi": c_rsi,
                    "last_macd_diff": c_macd_diff,
                    "last_above_sma20": c_above_sma20
                })
            except Exception as ex:
                logger.error(f"Error checking signals for {ticker}: {ex}")
                new_user_tracks.append(t)
        tracks[chat_id] = new_user_tracks
        
    if tracks_changed:
        save_signal_tracks(tracks)

if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    
    # Zamanlanmış Görevi Ayarla (Hergün 09:55 - TSİ time zone göre TR genelde UTC+3)
    tz = pytz.timezone('Europe/Istanbul')
    t = datetime.time(hour=9, minute=55, tzinfo=tz)
    
    job_queue = application.job_queue
    job_queue.run_daily(send_daily_report, time=t, days=(1, 2, 3, 4, 5)) # Mon-Fri
    
    # Her 2 dakikada bir alarmları ve dönüş sinyallerini kontrol et
    job_queue.run_repeating(check_alarms_and_signals_job, interval=120, first=10)
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('scan', scan))
    application.add_handler(CommandHandler('kap', kap_command))
    application.add_handler(CommandHandler('haber', haber_command))
    application.add_handler(CommandHandler('para', para_command))
    application.add_handler(CommandHandler('detay', detay_command))
    application.add_handler(CommandHandler('risk', risk_command))
    application.add_handler(CommandHandler('grafik', grafik_command))
    application.add_handler(CommandHandler('avci', avci_command))
    application.add_handler(CommandHandler('trend', trend_command))
    application.add_handler(CommandHandler('ekle', ekle_command))
    application.add_handler(CommandHandler('sil', sil_command))
    application.add_handler(CommandHandler('takip', takip_command))
    application.add_handler(CommandHandler('gcross', gcross_command))
    application.add_handler(CommandHandler('alarm', alarm_command))
    application.add_handler(CommandHandler('alarm_liste', alarm_liste_command))
    application.add_handler(CommandHandler('alarm_sil', alarm_sil_command))
    application.add_handler(CommandHandler('takipsinyal', takipsinyal_command))
    application.add_handler(CommandHandler('takipsinyal_liste', takipsinyal_liste_command))
    application.add_handler(CommandHandler('takipsinyal_sil', takipsinyal_sil_command))
    application.add_handler(CommandHandler('sinyal', sinyal_command))
    application.add_handler(MessageHandler(filters.ChatType.CHANNEL, channel_post_handler))
    
    print("Gelişmiş Bot Başlatıldı (Zamanlanmış görevler aktif)...")
    application.run_polling()
