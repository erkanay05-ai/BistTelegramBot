import os
import logging
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
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

USERS_FILE = "users.txt"
WATCHLIST_FILE = "watchlists.json"

def get_watchlists():
    if os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE, "r") as f:
            try: return json.load(f)
            except: return {}
    return {}

def save_watchlists(data):
    with open(WATCHLIST_FILE, "w") as f:
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
        "/ekle - Takip Listesine Ekle\n"
        "/sil - Takip Listesinden Sil\n"
        "/takip - Kişisel Takip Raporu\n"
        "/haber - Sosyal Medya Duyarlılığı\n"
        "/kap - Son KAP Bildirimleri\n"
        "/para - Aracı Kurum Dağılımı (AKD)\n"
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
        "• `/haber`: Sosyal mecralardaki 'bot sesini' ve trendi ölçer.\n"
        "• `/kap`: Borsa gündemini belirleyen sıcak gelişmeleri listeler.\n"
        "• `/para`: Kurumsal botların (BofA vb.) o anki yönünü özetler."
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
        msg += f"📏 **RSI (14):** {rsi}\n"
        msg += f"🏔 **52H En Düşük/Yüksek:** {low_52} - {high_52}\n"
        msg += f"🏗 **Sektör:** {fund['Sector']}\n"
        msg += f"📈 **F/K:** {fund['FK']} | **PD/DD:** {fund['PD_DD']}\n"
        msg += f"💵 **Temettü Verimi:** %{fund['DividendYield']}\n\n"
        
        msg += f"🎛 **Teknik Sinyal:** **{rating}**\n"
        msg += f"🧑‍💼 **Uzman Görüşü:** {expert_comment}\n"
        
        if fund['News']:
            msg += "\n📰 **SON HABERLER:**\n"
            for n in fund['News'][:2]:
                msg += f"• [{n['Title'][:45]}...]({n['Link']})\n"
        
        logger.info(f"Detail check for {ticker_raw} by {update.effective_user.name}")
        await status_msg.edit_text(msg, parse_mode='Markdown', disable_web_page_preview=True)
        
    except Exception as e:
        logger.error(f"Error in detay_command for {ticker_raw}: {e}")
        await status_msg.edit_text(f"❌ Analiz sırasında bir hata oluştu: {e}")

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

if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    
    # Zamanlanmış Görevi Ayarla (Hergün 09:55 - TSİ time zone göre TR genelde UTC+3)
    tz = pytz.timezone('Europe/Istanbul')
    t = datetime.time(hour=9, minute=55, tzinfo=tz)
    
    job_queue = application.job_queue
    job_queue.run_daily(send_daily_report, time=t, days=(1, 2, 3, 4, 5)) # Mon-Fri
    
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
    
    print("Gelişmiş Bot Başlatıldı (Zamanlanmış görevler aktif)...")
    application.run_polling()
