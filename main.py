import os
import logging
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
from dotenv import load_dotenv
import datetime
import pytz
from scanner import (
    scan_bist, scan_ceiling_prospects, scan_medium_term_trends,
    get_fundamentals, get_kap_news, get_akd_summary, 
    get_social_sentiment, calculate_atr, calculate_piotroski_score,
    calculate_volume_profile
)
import engine_risk
import engine_viz
import yfinance as yf
import pandas as pd

WATCHLIST_ALERTS_FILE = "watchlist_alerts.json"

from database import (
    init_db, db_add_user, db_get_users, db_get_watchlists, db_get_user_watchlist,
    db_add_to_watchlist, db_remove_from_watchlist, db_get_alarms, db_get_user_alarms,
    db_add_alarm, db_remove_alarm, db_deactivate_alarm, db_get_signal_tracks,
    db_get_user_signal_tracks, db_add_signal_track, db_remove_signal_track,
    db_get_portfolios, db_get_user_portfolio, db_add_portfolio_item,
    db_remove_portfolio_item, db_clear_portfolio, db_save_signal_tracks,
    db_save_alarms, db_save_portfolios
)

# Initialize database
init_db()

# Legacy mappings to prevent breaking external dependencies if any
def get_portfolios():
    return db_get_portfolios()

def save_portfolios(data):
    db_save_portfolios(data)

def get_watchlists():
    return db_get_watchlists()

def save_watchlists(data):
    pass

def get_alarms():
    return db_get_alarms()

def save_alarms(data):
    db_save_alarms(data)

def get_signal_tracks():
    return db_get_signal_tracks()

def save_signal_tracks(data):
    db_save_signal_tracks(data)

def save_user(chat_id):
    db_add_user(chat_id)

def get_users():
    return db_get_users()


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
    
    first_name = user.first_name if user else "Kanal"
    welcome_msg = (
        f"Merhaba {first_name}! 👋\n\n"
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
        "/pdf - DuPont PDF Raporu\n"
        "/portfoy - Sanal Portföy Takip Raporu\n"
        "/help - Bilgi"
    )
    
    # Check if start command has arguments (deep linking)
    if context.args:
        arg = context.args[0].lower()
        if arg == "scan":
            await scan(update, context)
            return
        elif arg == "avci":
            await avci_command(update, context)
            return
        elif arg == "trend":
            await trend_command(update, context)
            return

        elif arg == "gcross":
            await gcross_command(update, context)
            return
        elif arg == "portfoy":
            await portfoy_command(update, context)
            return
            
    if update.effective_chat and update.effective_chat.type == "channel":
        bot_info = await context.bot.get_me()
        bot_username = bot_info.username
        inline_keyboard = [
            [
                InlineKeyboardButton("🔎 Tarama Yap", url=f"https://t.me/{bot_username}?start=scan"),
                InlineKeyboardButton("🎯 Tavan Avcısı", url=f"https://t.me/{bot_username}?start=avci")
            ],
            [
                InlineKeyboardButton("📋 Takip Listem", url=f"https://t.me/{bot_username}?start=takip"),
                InlineKeyboardButton("📢 KAP Haberleri", url=f"https://t.me/{bot_username}?start=kap")
            ],
            [
                InlineKeyboardButton("💸 AKD Para Akışı", url=f"https://t.me/{bot_username}?start=para"),
                InlineKeyboardButton("💼 Portföyüm", url=f"https://t.me/{bot_username}?start=portfoy")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard)
        await update.message.reply_text(welcome_msg, reply_markup=reply_markup)
    else:
        keyboard = [
            [KeyboardButton("🔎 Tarama Yap"), KeyboardButton("🎯 Tavan Avcısı")],
            [KeyboardButton("📋 Takip Listem"), KeyboardButton("📢 KAP Haberleri")],
            [KeyboardButton("💸 AKD Para Akışı"), KeyboardButton("💼 Portföyüm")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(welcome_msg, reply_markup=reply_markup)

 
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

        # Calculate Volume Profile (POC)
        poc, vah, val = calculate_volume_profile(hist)
        if poc is not None:
            poc_status = "üstünde 🟢" if last_price >= poc else "altında 🔴"
            vp_status = f"📊 Hacim Profili (POC): {poc} TL (Fiyat POC {poc_status}) | VA: {val} - {vah} TL"
        else:
            vp_status = "📊 Hacim Profili (POC): Veri Yetersiz ⚠️"

        # Calculate Piotroski F-Score
        f_score, f_label = calculate_piotroski_score(ticker)
        if f_score is not None:
            f_score_str = f"{f_score}/9 ({f_label})"
        else:
            f_score_str = f"Veri Yetersiz ⚠️"

        msg = f"📊 **DETAYLI ANALİZ: {ticker_raw}**\n\n"
        msg += f"💰 **Fiyat:** {last_price} TL (%{change})\n"
        msg += f"📐 **20 Günlük VWAP:** {last_vwap20} TL\n"
        msg += f"⚡ **Gün İçi Yön:** {vwap_status}\n"
        msg += f"{vp_status}\n"
        msg += f"📏 **RSI (14):** {rsi}\n"
        msg += f"🏔 **52H En Düşük/Yüksek:** {low_52} - {high_52}\n"
        msg += f"🏗 **Sektör:** {fund['Sector']}\n"
        msg += f"📈 **F/K:** {fund['FK']} | **PD/DD:** {fund['PD_DD']}\n"
        msg += f"🛡️ **Piotroski F-Skoru:** {f_score_str}\n"
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
        
        user_name = update.effective_user.name if update.effective_user else "Channel"
        logger.info(f"Detail check for {ticker_raw} by {user_name}")
        keyboard = [
            [
                InlineKeyboardButton("📈 Teknik Grafik", callback_data=f"graph_{ticker_raw}"),
                InlineKeyboardButton("📄 DuPont PDF Raporu", callback_data=f"pdf_{ticker_raw}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await status_msg.edit_text(msg, parse_mode='Markdown', reply_markup=reply_markup, disable_web_page_preview=True)
        
    except Exception as e:
        logger.error(f"Error in detay_command for {ticker_raw}: {e}")
        await status_msg.edit_text(f"❌ Analiz sırasında bir hata oluştu: {e}")

async def pdf_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import io
    if not context.args:
        await update.message.reply_text("❌ Lütfen bir hisse kodu yazın. Örn: `/pdf THYAO`", parse_mode='Markdown')
        return
    ticker = context.args[0].upper().replace(".IS", "")
    status_msg = await update.message.reply_text(f"📄 **{ticker}** için DuPont analizli PDF rapor üretiliyor...")
    try:
        from engine_pdf import generate_dupont_pdf
        pdf_data = generate_dupont_pdf(ticker)
        pdf_file = io.BytesIO(pdf_data)
        pdf_file.name = f"{ticker}_DuPont_Analiz_Raporu.pdf"
        
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=pdf_file,
            filename=pdf_file.name,
            caption=f"📄 **{ticker}** için hazırlanan DuPont Analiz ve Rasyolar Raporu hazırdır. Yatırım Tavsiyesi Değildir.",
            parse_mode='Markdown'
        )
        await status_msg.delete()
    except Exception as e:
        logger.error(f"Error generating PDF command: {e}")
        await status_msg.edit_text(f"❌ PDF Raporu üretilirken hata oluştu: {e}")

async def portfoy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    user_portfolio = db_get_user_portfolio(chat_id)
    
    if not user_portfolio:
        await update.message.reply_text(
            "💼 **Sanal Portföyünüz şu an boş.**\n\n"
            "Portföyünüze hisse eklemek için:\n"
            "`/portfoy_ekle <hisse> <adet> <maliyet>`\n"
            "*Örn:* `/portfoy_ekle THYAO 100 295.5`",
            parse_mode='Markdown'
        )
        return
        
    status_msg = await update.message.reply_text("💼 Portföyünüz analiz ediliyor, güncel fiyatlar çekiliyor...")
    
    try:
        tickers = list(user_portfolio.keys())
        tickers_is = [t + ".IS" for t in tickers]
        
        # Download batch data
        df_batch = yf.download(tickers_is, period='5d', progress=False)
        
        report = "💼 **SANAL PORTFÖY RAPORU**\n"
        report += "───────────────────\n"
        
        total_cost = 0.0
        total_value = 0.0
        
        for t in tickers:
            data = user_portfolio[t]
            qty = data['quantity']
            avg_price = data['avg_price']
            ticker_is = t + ".IS"
            
            try:
                # Extract current price
                if len(tickers) > 1:
                    current_price = float(df_batch['Close'][ticker_is].dropna().iloc[-1])
                else:
                    current_price = float(df_batch['Close'].dropna().iloc[-1])
                
                cost = qty * avg_price
                value = qty * current_price
                pnl_val = value - cost
                pnl_pct = ((current_price / avg_price) - 1) * 100 if avg_price > 0 else 0
                
                total_cost += cost
                total_value += value
                
                pnl_sign = "+" if pnl_val >= 0 else ""
                pnl_emoji = "🟢" if pnl_val >= 0 else "🔴"
                
                report += (
                     f"🚀 **{t}** | {qty} Lot\n"
                     f"  ↳ Maliyet: {avg_price:,.2f} TL | Güncel: {current_price:,.2f} TL\n"
                     f"  ↳ K/Z: {pnl_sign}{pnl_val:,.2f} TL ({pnl_sign}{pnl_pct:.2f}%) {pnl_emoji}\n\n"
                )
            except Exception as e:
                logger.error(f"Error calculating portfolio for {t}: {e}")
                report += f"❌ **{t}**: Güncel fiyat verisi alınamadı.\n\n"
                
        total_pnl = total_value - total_cost
        total_pnl_pct = ((total_value / total_cost) - 1) * 100 if total_cost > 0 else 0
        total_pnl_sign = "+" if total_pnl >= 0 else ""
        
        report += "───────────────────\n"
        report += "📊 **PORTFÖY ÖZETİ**\n"
        report += f"💰 **Toplam Maliyet:** {total_cost:,.2f} TL\n"
        report += f"💵 **Güncel Değer:** {total_value:,.2f} TL\n"
        report += f"🍀 **Net Kâr/Zarar:** {total_pnl_sign}{total_pnl:,.2f} TL ({total_pnl_sign}{total_pnl_pct:.2f}%)\n\n"
        report += "💡 _Hisse eklemek için:_ `/portfoy_ekle <hisse> <adet> <maliyet>`\n"
        report += "_Hisse silmek için:_ `/portfoy_sil <hisse>`"
        await status_msg.edit_text(report, parse_mode='Markdown')
    except Exception as ex:
        logger.error(f"Error compiling portfolio report: {ex}")
        await status_msg.edit_text(f"❌ Portföy raporu oluşturulurken hata oluştu: {ex}")

async def portfoy_ekle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 3:
        await update.message.reply_text(
            "❌ **Kullanım:** `/portfoy_ekle <hisse> <adet> <maliyet>`\n"
            "*Örn:* `/portfoy_ekle THYAO 100 295.5`",
            parse_mode='Markdown'
        )
        return
        
    ticker = context.args[0].upper().replace(".IS", "")
    chat_id = str(update.effective_chat.id)
    
    try:
        qty = int(context.args[1])
        price = float(context.args[2].replace(",", "."))
        if qty <= 0 or price <= 0:
            raise ValueError()
    except:
        await update.message.reply_text("❌ Lütfen adet ve maliyeti geçerli pozitif sayılar olarak girin.")
        return
        
    status_msg = await update.message.reply_text(f"⏳ **{ticker}** portföyünüze ekleniyor...")
    
    try:
        # Verify ticker exists
        t_is = ticker + ".IS"
        t = yf.Ticker(t_is)
        hist = t.history(period="1d")
        if hist.empty:
            await status_msg.edit_text("❌ Hisse verisi bulunamadı. Lütfen kodu kontrol edin.")
            return
            
        portfolios = get_portfolios()
        user_portfolio = portfolios.get(chat_id, {})
        
        if ticker in user_portfolio:
            old_data = user_portfolio[ticker]
            old_qty = old_data['quantity']
            old_avg = old_data['avg_price']
            
            new_qty = old_qty + qty
            new_avg = ((old_qty * old_avg) + (qty * price)) / new_qty
            
            user_portfolio[ticker] = {
                "quantity": new_qty,
                "avg_price": round(new_avg, 2)
            }
            avg_text = f"Ortalama maliyet güncellendi: {round(new_avg, 2)} TL"
        else:
            user_portfolio[ticker] = {
                "quantity": qty,
                "avg_price": price
            }
            avg_text = f"Maliyet: {price} TL"
            
        portfolios[chat_id] = user_portfolio
        save_portfolios(portfolios)
        
        await status_msg.edit_text(
            f"✅ **Ekleme Başarılı!**\n\n"
            f"📈 **Hisse:** {ticker}\n"
            f"📦 **Eklenen Adet:** {qty} Lot\n"
            f"💼 **Yeni Toplam Adet:** {user_portfolio[ticker]['quantity']} Lot\n"
            f"💳 {avg_text}"
        )
    except Exception as e:
        logger.error(f"Error adding to portfolio: {e}")
        await status_msg.edit_text(f"❌ Portföye ekleme yapılırken hata oluştu: {e}")

async def portfoy_sil_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "❌ **Kullanım:** `/portfoy_sil <hisse> [adet]`\n"
            "*Örn:* `/portfoy_sil THYAO` (Tümünü siler)\n"
            "*Örn:* `/portfoy_sil THYAO 50` (50 lot çıkarır)",
            parse_mode='Markdown'
        )
        return
        
    ticker = context.args[0].upper().replace(".IS", "")
    chat_id = str(update.effective_chat.id)
    
    portfolios = get_portfolios()
    user_portfolio = portfolios.get(chat_id, {})
    
    if ticker not in user_portfolio:
        await update.message.reply_text(f"❌ **{ticker}** portföyünüzde bulunamadı.")
        return
        
    subtract_qty = None
    if len(context.args) > 1:
        try:
            subtract_qty = int(context.args[1])
            if subtract_qty <= 0:
                raise ValueError()
        except:
            await update.message.reply_text("❌ Lütfen geçerli pozitif bir adet girin.")
            return
            
    if subtract_qty is None or subtract_qty >= user_portfolio[ticker]['quantity']:
        del user_portfolio[ticker]
        msg = f"🗑 **{ticker}** portföyünüzden tamamen çıkarıldı."
    else:
        user_portfolio[ticker]['quantity'] -= subtract_qty
        msg = f"📉 **{ticker}** portföyünüzden {subtract_qty} Lot azaltıldı. (Yeni Adet: {user_portfolio[ticker]['quantity']} Lot)"
        
    portfolios[chat_id] = user_portfolio
    save_portfolios(portfolios)
    await update.message.reply_text(msg)

async def portfoy_sifirla_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    portfolios = get_portfolios()
    
    if chat_id in portfolios:
        del portfolios[chat_id]
        save_portfolios(portfolios)
        await update.message.reply_text("🗑 **Sanal portföyünüz tamamen sıfırlandı.**")
    else:
        await update.message.reply_text("❌ Sıfırlanacak aktif bir portföyünüz bulunamadı.")

async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import io
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if not data:
        return
        
    parts = data.split('_', 1)
    if len(parts) < 2:
        return
        
    action, ticker = parts[0], parts[1]
    chat_id = query.message.chat_id
    
    if action == "graph":
        status_msg = await query.message.reply_text(f"🎨 **{ticker}** için teknik grafik çiziliyor...")
        try:
            t = yf.Ticker(ticker + ".IS")
            df = t.history(period="1y")
            if df.empty:
                await status_msg.edit_text("❌ Veri bulunamadı.")
                return
            chart_buf = engine_viz.create_tech_chart(ticker, df)
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=chart_buf,
                caption=f"📈 **{ticker}** - Teknik Görünüm (1 Yıllık)\nSMA 50 (Sarı), SMA 200 (Pembe) ve RSI göstergeleri dahildir.",
                parse_mode='Markdown'
            )
            await status_msg.delete()
        except Exception as e:
            await status_msg.edit_text(f"❌ Grafik oluşturulurken hata: {e}")
            
    elif action == "pdf":
        status_msg = await query.message.reply_text(f"📄 **{ticker}** için DuPont analizli PDF rapor üretiliyor...")
        try:
            from engine_pdf import generate_dupont_pdf
            pdf_data = generate_dupont_pdf(ticker)
            pdf_file = io.BytesIO(pdf_data)
            pdf_file.name = f"{ticker}_DuPont_Analiz_Raporu.pdf"
            
            await context.bot.send_document(
                chat_id=chat_id,
                document=pdf_file,
                filename=pdf_file.name,
                caption=f"📄 **{ticker}** için hazırlanan DuPont Analiz ve Rasyolar Raporu hazırdır. Yatırım Tavsiyesi Değildir.",
                parse_mode='Markdown'
            )
            await status_msg.delete()
        except Exception as e:
            logger.error(f"Error generating PDF callback: {e}")
            await status_msg.edit_text(f"❌ PDF Rapor üretilirken hata oluştu: {e}")

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    mapping = {
        "🔎 Tarama Yap": scan,
        "🎯 Tavan Avcısı": avci_command,
        "📋 Takip Listem": takip_command,
        "📢 KAP Haberleri": kap_command,
        "💸 AKD Para Akışı": para_command,
        "💼 Portföyüm": portfoy_command
    }
    if text in mapping:
        await mapping[text](update, context)

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

class ChannelUpdateWrapper:
    def __init__(self, update: Update):
        self._update = update
        self.message = update.channel_post
        self.channel_post = update.channel_post
        
    def __getattr__(self, name):
        return getattr(self._update, name)

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
            'detay': detay_command,
            'grafik': grafik_command,
            'avci': avci_command,
            'trend': trend_command,
            'gcross': gcross_command,
            'takipsinyal': takipsinyal_command,
            'takipsinyal_liste': takipsinyal_liste_command,
            'takipsinyal_sil': takipsinyal_sil_command,
            'sinyal': sinyal_command,
            'pdf': pdf_command,
            'portfoy': portfoy_command,
            'portfoy_ekle': portfoy_ekle_command,
            'portfoy_sil': portfoy_sil_command,
            'portfoy_sifirla': portfoy_sifirla_command
        }
        
        if cmd in handlers:
            mock_update = ChannelUpdateWrapper(update)
            try:
                await handlers[cmd](mock_update, context)
            except Exception as e:
                logger.error(f"Error executing command {cmd} in channel: {e}")

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
            
    watchlists = get_watchlists()
    for user_list in watchlists.values():
        for t in user_list:
            active_tickers.add(t)
            
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
                if isinstance(df_batch_d.columns, pd.MultiIndex):
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

    # 2. Watchlist Support & Resistance Breakout Checks
    watchlist_alerts = {}
    try:
        if os.path.exists(WATCHLIST_ALERTS_FILE):
            with open(WATCHLIST_ALERTS_FILE, "r") as f:
                watchlist_alerts = json.load(f)
    except Exception as e:
        logger.error(f"Error loading watchlist alerts: {e}")

    alerts_changed = False
    today_str = now_tr.strftime('%Y-%m-%d')
    
    for chat_id, user_list in watchlists.items():
        user_alerts = watchlist_alerts.get(chat_id, {})
        for t in user_list:
            ticker_is = t + ".IS"
            try:
                # Extract ticker dataframe from batch
                if isinstance(df_batch_d.columns, pd.MultiIndex):
                    if ticker_is not in df_batch_d.columns.levels[0]:
                        continue
                    df_t = df_batch_d[ticker_is].dropna(subset=['Close'])
                else:
                    df_t = df_batch_d.dropna(subset=['Close'])
                
                if len(df_t) < 5:
                    continue
                
                # Current price (latest close)
                current_price = float(df_t['Close'].dropna().iloc[-1])
                
                # Exclude last row (today's candle) for support/resistance levels
                df_hist = df_t.iloc[:-1] if len(df_t) > 1 else df_t
                
                # 20-day high and low (Donchian channel boundaries)
                resistance = float(df_hist['High'].tail(20).max())
                support = float(df_hist['Low'].tail(20).min())
                
                # Check if triggered today
                t_alerts = user_alerts.get(t, {"support": "", "resistance": ""})
                
                if current_price >= resistance and t_alerts.get("resistance") != today_str:
                    t_alerts["resistance"] = today_str
                    user_alerts[t] = t_alerts
                    watchlist_alerts[chat_id] = user_alerts
                    alerts_changed = True
                    
                    msg = (
                        f"🚨 **DİRENÇ KIRILIMI! (Takip Listesi)**\n\n"
                        f"📈 **Hisse:** {t}\n"
                        f"🔥 **Direnç Seviyesi:** {resistance:.2f} TL (20 Günlük Zirve)\n"
                        f"⚡ **Mevcut Fiyat:** {current_price:.2f} TL (Yukarı Kırıldı!)\n"
                        f"💡 _Hissenin yükseliş trendi güçleniyor olabilir._"
                    )
                    try:
                        await context.bot.send_message(chat_id=int(chat_id), text=msg, parse_mode='Markdown')
                    except Exception as err:
                        logger.error(f"Cannot send watchlist alert to {chat_id}: {err}")
                        
                elif current_price <= support and t_alerts.get("support") != today_str:
                    t_alerts["support"] = today_str
                    user_alerts[t] = t_alerts
                    watchlist_alerts[chat_id] = user_alerts
                    alerts_changed = True
                    
                    msg = (
                        f"⚠️ **DESTEK KIRILIMI! (Takip Listesi)**\n\n"
                        f"📈 **Hisse:** {t}\n"
                        f"📉 **Destek Seviyesi:** {support:.2f} TL (20 Günlük Dip)\n"
                        f"⚡ **Mevcut Fiyat:** {current_price:.2f} TL (Aşağı Kırıldı!)\n"
                        f"💡 _Hissede satış baskısı artıyor olabilir. Risk yönetimine dikkat ediniz._"
                    )
                    try:
                        await context.bot.send_message(chat_id=int(chat_id), text=msg, parse_mode='Markdown')
                    except Exception as err:
                        logger.error(f"Cannot send watchlist alert to {chat_id}: {err}")
            except Exception as ex:
                logger.error(f"Error checking watchlist support/resistance for {t}: {ex}")
                
    if alerts_changed:
        try:
            with open(WATCHLIST_ALERTS_FILE, "w") as f:
                json.dump(watchlist_alerts, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving watchlist alerts: {e}")

    from scanner import check_reversal_signals
    tracks_changed = False
    for chat_id, user_tracks in list(tracks.items()):
        new_user_tracks = []
        for t in user_tracks:
            ticker = t['ticker']
            ticker_is = ticker + ".IS"
            try:
                if isinstance(df_batch_d.columns, pd.MultiIndex):
                    df_d = df_batch_d[ticker_is].dropna()
                else:
                    df_d = df_batch_d.dropna()
                    
                if isinstance(df_batch_h.columns, pd.MultiIndex):
                    df_h = df_batch_h[ticker_is].dropna()
                else:
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
    application.add_handler(CommandHandler('detay', detay_command))
    application.add_handler(CommandHandler('grafik', grafik_command))
    application.add_handler(CommandHandler('avci', avci_command))
    application.add_handler(CommandHandler('trend', trend_command))
    application.add_handler(CommandHandler('gcross', gcross_command))
    application.add_handler(CommandHandler('takipsinyal', takipsinyal_command))
    application.add_handler(CommandHandler('takipsinyal_liste', takipsinyal_liste_command))
    application.add_handler(CommandHandler('takipsinyal_sil', takipsinyal_sil_command))
    application.add_handler(CommandHandler('sinyal', sinyal_command))
    application.add_handler(CommandHandler('pdf', pdf_command))
    application.add_handler(CommandHandler('portfoy', portfoy_command))
    application.add_handler(CommandHandler('portfoy_ekle', portfoy_ekle_command))
    application.add_handler(CommandHandler('portfoy_sil', portfoy_sil_command))
    application.add_handler(CommandHandler('portfoy_sifirla', portfoy_sifirla_command))
    application.add_handler(CallbackQueryHandler(button_callback_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    application.add_handler(MessageHandler(filters.ChatType.CHANNEL, channel_post_handler))
    
    print("Gelişmiş Bot Başlatıldı (Zamanlanmış görevler aktif)...")
    application.run_polling()
