import io
import os
import yfinance as yf
import pandas as pd
import numpy as np
import datetime
import pytz
import logging
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from scanner import get_fundamentals, calculate_piotroski_score, calculate_volume_profile
import engine_viz

logger = logging.getLogger(__name__)

# Register Arial custom fonts for Turkish support
current_dir = os.path.dirname(os.path.abspath(__file__))
font_dir = os.path.join(current_dir, 'fonts')

regular_font_path = os.path.join(font_dir, 'Arial.ttf')
bold_font_path = os.path.join(font_dir, 'Arial-Bold.ttf')
italic_font_path = os.path.join(font_dir, 'Arial-Italic.ttf')

try:
    pdfmetrics.registerFont(TTFont('ArialCustom', regular_font_path))
    pdfmetrics.registerFont(TTFont('ArialCustom-Bold', bold_font_path))
    pdfmetrics.registerFont(TTFont('ArialCustom-Italic', italic_font_path))
    FONT_NAME = 'ArialCustom'
    FONT_NAME_BOLD = 'ArialCustom-Bold'
    FONT_NAME_ITALIC = 'ArialCustom-Italic'
except Exception as e:
    logger.error(f"Error registering custom Arial fonts: {e}. Falling back to Helvetica.")
    FONT_NAME = 'Helvetica'
    FONT_NAME_BOLD = 'Helvetica-Bold'
    FONT_NAME_ITALIC = 'Helvetica-Oblique'

def clean_pdf_text(text):
    if not text:
        return ""
    import re
    # Convert markdown **bold** to <b>bold</b>
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    
    # Emojis/special characters to remove or replace
    replacements = {
        "📈": "",
        "🟢": "<font color='#10B981'>▲</font>",
        "🔴": "<font color='#EF4444'>▼</font>",
        "🟡": "<font color='#F59E0B'>■</font>",
        "📊": "",
        "📐": "",
        "⚖️": "",
        "⚠️": "",
        "📢": "",
        "🤖": "",
    }
    for emoji, replacement in replacements.items():
        text = text.replace(emoji, replacement)
        
    return text.strip()


def get_dupont_data(ticker_name):
    """
    Calculates DuPont Analysis metrics for BIST tickers.
    Formula: ROE = Net Profit Margin * Asset Turnover * Leverage
    """
    ticker = ticker_name + ".IS" if not ticker_name.endswith(".IS") else ticker_name
    t = yf.Ticker(ticker)
    
    financials = t.financials
    balance_sheet = t.balance_sheet
    
    # Try quarterly fallback if annual financials are empty
    if financials is None or financials.empty or balance_sheet is None or balance_sheet.empty:
        financials = t.quarterly_financials
        balance_sheet = t.quarterly_balance_sheet
        
    if financials is None or financials.empty or balance_sheet is None or balance_sheet.empty:
        return None
        
    def get_val(df, keys, col_idx=0):
        for key in keys:
            for idx in df.index:
                if str(idx).strip().lower() == key.strip().lower():
                    val = df.loc[idx]
                    if isinstance(val, pd.Series):
                        if len(val) > col_idx:
                            val = val.iloc[col_idx]
                        else:
                            val = val.iloc[0]
                    if not pd.isna(val) and val is not None:
                        return float(val)
        return None

    net_income = get_val(financials, ['Net Income', 'Net Income Common Stockholders', 'NetIncome', 'Net Income from Continuing Operations'])
    revenue = get_val(financials, ['Total Revenue', 'TotalRevenue', 'Revenue', 'Operating Revenue'])
    assets = get_val(balance_sheet, ['Total Assets', 'TotalAssets'])
    equity = get_val(balance_sheet, ['Stockholders Equity', 'Total Equity Gross Minority Interest', 'Common Stock Equity', 'Equity', 'Total Stockholders Equity'])
    
    if not (net_income and revenue and assets and equity) or revenue == 0 or assets == 0 or equity == 0:
        return None
        
    net_profit_margin = net_income / revenue
    asset_turnover = revenue / assets
    leverage = assets / equity
    roe = net_profit_margin * asset_turnover * leverage
    
    return {
        'NetIncome': net_income,
        'Revenue': revenue,
        'TotalAssets': assets,
        'Equity': equity,
        'NetProfitMargin%': net_profit_margin * 100,
        'AssetTurnover': asset_turnover,
        'Leverage': leverage,
        'ROE%': roe * 100
    }

def format_number(val):
    if val is None or pd.isna(val):
        return "N/A"
    if val >= 1e9:
        return f"{val / 1e9:.2f} Milyar TL"
    elif val >= 1e6:
        return f"{val / 1e6:.2f} Milyon TL"
    return f"{val:,.2f} TL"

def generate_dupont_pdf(ticker_raw):
    """
    Generates a beautiful 1-page A4 PDF report for a BIST ticker.
    """
    ticker_is = ticker_raw + ".IS" if not ticker_raw.endswith(".IS") else ticker_raw
    ticker_clean = ticker_raw.replace(".IS", "")
    
    t = yf.Ticker(ticker_is)
    hist = t.history(period="1y")
    
    if hist.empty:
        raise ValueError(f"Hisse verisi bulunamadı: {ticker_clean}")
        
    last_price = round(hist['Close'].iloc[-1], 2)
    change = round(((hist['Close'].iloc[-1] / hist['Close'].iloc[-2]) - 1) * 100, 2)
    
    fund = get_fundamentals(ticker_is)
    poc, vah, val = calculate_volume_profile(hist)
    
    f_score, f_label = calculate_piotroski_score(ticker_is)
    f_score_str = f"{f_score}/9 ({clean_pdf_text(f_label)})" if f_score is not None else "Yetersiz Veri"
    
    dupont = get_dupont_data(ticker_clean)
    
    # Save Matplotlib chart from engine_viz to a temp file
    chart_buf = engine_viz.create_tech_chart(ticker_clean, hist)
    temp_img_path = f"temp_chart_{ticker_clean}.png"
    with open(temp_img_path, "wb") as f:
        f.write(chart_buf.getvalue())
        
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=A4,
        leftMargin=25,
        rightMargin=25,
        topMargin=25,
        bottomMargin=25
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'HeaderTitle',
        fontName=FONT_NAME_BOLD,
        fontSize=15,
        textColor=colors.white,
        spaceAfter=3
    )
    subtitle_style = ParagraphStyle(
        'HeaderSubtitle',
        fontName=FONT_NAME,
        fontSize=9,
        textColor=colors.HexColor('#E2E8F0')
    )
    right_header_style = ParagraphStyle(
        'HeaderRight',
        fontName=FONT_NAME_BOLD,
        fontSize=18,
        textColor=colors.white,
        alignment=2 # Right aligned
    )
    right_sub_header = ParagraphStyle(
        'HeaderRightSub',
        fontName=FONT_NAME_BOLD,
        fontSize=11,
        textColor=colors.white,
        alignment=2 # Right aligned
    )
    sec_title_style = ParagraphStyle(
        'SectionTitle',
        fontName=FONT_NAME_BOLD,
        fontSize=11,
        textColor=colors.HexColor('#1E3A8A'),
        spaceBefore=10,
        spaceAfter=5
    )
    body_bold = ParagraphStyle('BodyBold', fontName=FONT_NAME_BOLD, fontSize=8, textColor=colors.HexColor('#1E293B'))
    body_normal = ParagraphStyle('BodyNormal', fontName=FONT_NAME, fontSize=8, textColor=colors.HexColor('#475569'))
    comment_style = ParagraphStyle('CommentStyle', fontName=FONT_NAME_ITALIC, fontSize=8.5, textColor=colors.HexColor('#334155'), leading=12)
    
    story = []
    
    # 1. Header Banner Table
    tz = pytz.timezone('Europe/Istanbul')
    date_str = datetime.datetime.now(tz).strftime('%d.%m.%Y - %H:%M')
    
    change_sign = "+" if change > 0 else ""
    change_arrow = "▲" if change >= 0 else "▼"
    change_color_hex = "#10B981" if change >= 0 else "#EF4444"
    price_text = f"{last_price} TL <font color='{change_color_hex}'>({change_sign}{change}%) {change_arrow}</font>"
    
    header_data = [
        [
            Paragraph(f"BIST ANALİZ VE RASYOLAR RAPORU", title_style),
            Paragraph(f"{ticker_clean}", right_header_style)
        ],
        [
            Paragraph(f"Oluşturulma Tarihi: {date_str} | BIST Gelişmiş Komuta Botu", subtitle_style),
            Paragraph(price_text, right_sub_header)
        ]
    ]
    
    header_table = Table(header_data, colWidths=[385, 160])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#1E3A8A')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,1), (-1,1), 10),
    ]))
    
    story.append(header_table)
    story.append(Spacer(1, 10))
    
    # 2. Main Content Split: Left (Tables) & Right (Chart)
    # Prepare Left Column elements
    left_elements = []
    
    # Left Column Table 1: Key Ratios
    left_elements.append(Paragraph("<font color='#3B82F6'>■</font> TEMEL FİNANSAL GÖSTERGELER", sec_title_style))
    
    ratios_data = [
        [Paragraph("Sektör", body_bold), Paragraph(str(fund.get('Sector', 'N/A')), body_normal)],
        [Paragraph("Piyasa Değeri", body_bold), Paragraph(format_number(fund.get('MarketCap')), body_normal)],
        [Paragraph("F/K Oranı", body_bold), Paragraph(str(fund.get('FK', 'N/A')), body_normal)],
        [Paragraph("PD/DD Oranı", body_bold), Paragraph(str(fund.get('PD_DD', 'N/A')), body_normal)],
        [Paragraph("Piotroski F-Skoru", body_bold), Paragraph(f_score_str, body_normal)],
        [Paragraph("Temettü Verimi", body_bold), Paragraph(f"%{fund.get('DividendYield', 0):.2f}", body_normal)]
    ]
    
    ratios_table = Table(ratios_data, colWidths=[100, 150])
    ratios_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('PADDING', (0,0), (-1,-1), 4),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    left_elements.append(ratios_table)
    
    # Left Column Table 2: DuPont Analysis
    left_elements.append(Paragraph("<font color='#3B82F6'>■</font> DUPONT ANALİZİ (ROE KIRILIMI)", sec_title_style))
    
    if dupont:
        dupont_data = [
            [Paragraph("Özsermaye Kârlılığı (ROE)", body_bold), Paragraph(f"%{dupont['ROE%']:.2f}", body_bold)],
            [Paragraph("Net Kâr Marjı", body_bold), Paragraph(f"%{dupont['NetProfitMargin%']:.2f}", body_normal)],
            [Paragraph("Aktif Devir Hızı", body_bold), Paragraph(f"{dupont['AssetTurnover']:.4f}", body_normal)],
            [Paragraph("Finansal Kaldıraç", body_bold), Paragraph(f"{dupont['Leverage']:.4f}", body_normal)]
        ]
    else:
        dupont_data = [
            [Paragraph("Özsermaye Kârlılığı (ROE)", body_bold), Paragraph("N/A (Veri Yetersiz)", body_normal)],
            [Paragraph("Net Kâr Marjı", body_bold), Paragraph("N/A", body_normal)],
            [Paragraph("Aktif Devir Hızı", body_bold), Paragraph("N/A", body_normal)],
            [Paragraph("Finansal Kaldıraç", body_bold), Paragraph("N/A", body_normal)]
        ]
        
    dupont_table = Table(dupont_data, colWidths=[130, 120])
    dupont_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F1F5F9')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('PADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TEXTCOLOR', (1,0), (1,0), colors.HexColor('#1E3A8A')), # ROE bold color
    ]))
    left_elements.append(dupont_table)
    
    # Prepare Right Column elements (Matplotlib Chart)
    chart_image = Image(temp_img_path, width=275, height=230)
    
    # Outer layout table to split Left Column & Right Column
    layout_data = [[left_elements, chart_image]]
    layout_table = Table(layout_data, colWidths=[260, 285])
    layout_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (1,0), (1,0), 10),
        ('RIGHTPADDING', (0,0), (0,0), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    
    story.append(layout_table)
    story.append(Spacer(1, 10))
    
    # 3. Bottom Section: Volume Profile & Technical Comments
    story.append(Paragraph("<font color='#3B82F6'>■</font> HACİM PROFİLİ VE UZMAN ANALİZİ", sec_title_style))
    
    if poc is not None:
        poc_status = "üstünde <font color='#10B981'>▲</font>" if last_price >= poc else "altında <font color='#EF4444'>▼</font>"
        vp_status_text = f"Hisse anlık fiyatı olan {last_price} TL ile en yoğun maliyetlenme seviyesi (POC) olan {poc} TL {poc_status} hareket etmektedir. Güvenli Değer Alanı (Value Area) bandı {val} - {vah} TL aralığındadır."
    else:
        vp_status_text = "Hacim Profili analizi için yeterli işlem günü verisi bulunmamaktadır."
        
    # Simple expert commentary parsing from fundamentals
    from scanner import calculate_technical_rating, get_expert_commentary
    # Simulate a full df for rating
    df_full = hist.copy()
    df_full['SMA50'] = df_full['Close'].rolling(window=50).mean()
    df_full['SMA200'] = df_full['Close'].rolling(window=200).mean()
    exp1 = df_full['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df_full['Close'].ewm(span=26, adjust=False).mean()
    df_full['MACD'] = exp1 - exp2
    df_full['MACD_Signal'] = df_full['MACD'].ewm(span=9, adjust=False).mean()
    
    delta = df_full['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rsi_val = round(100 - (100 / (1 + (gain / loss))).iloc[-1], 2)
    df_full['RSI'] = rsi_val
    
    has_gc = False
    if len(df_full) >= 15:
        recent = df_full.tail(15)
        for i in range(1, len(recent)):
            if float(recent['SMA50'].iloc[i-1]) <= float(recent['SMA200'].iloc[i-1]) and float(recent['SMA50'].iloc[i]) > float(recent['SMA200'].iloc[i]):
                has_gc = True
                break
                
    tech_rating = calculate_technical_rating(df_full, golden_cross=has_gc)
    expert_comment = get_expert_commentary(ticker_clean, fund, last_price, rsi_val, tech_rating, golden_cross=has_gc)
    
    cleaned_expert_comment = clean_pdf_text(expert_comment)
    analysis_text = (
        f"<b>Hacim Profili Analizi:</b> {vp_status_text}<br/><br/>"
        f"<b>Teknik Sinyal:</b> {tech_rating} | <b>Uzman Görüşü:</b> {cleaned_expert_comment}"
    )
    
    analysis_paragraph = Paragraph(analysis_text, comment_style)
    
    analysis_table = Table([[analysis_paragraph]], colWidths=[540])
    analysis_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#E2E8F0')),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LINELEFT', (0,0), (0,-1), 4, colors.HexColor('#1E3A8A')), # Dark blue accent bar on left
    ]))
    
    story.append(analysis_table)
    story.append(Spacer(1, 15))
    
    # 4. Footer Table
    footer_text = Paragraph("<font color='#EF4444'>■</font> <font color='#64748B'><b>Yasal Uyarı:</b> Bu raporda yer alan analiz, rasyo ve grafikler tamamen bilgilendirme amaçlı olup yatırım tavsiyesi niteliği taşımaz. Veriler yfinance entegrasyonu ile sağlanmıştır.</font>", subtitle_style)
    footer_table = Table([[footer_text]], colWidths=[540])
    footer_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(footer_table)
    
    # Build Document
    doc.build(story)
    
    # Clean up Matplotlib temp image
    try:
        if os.path.exists(temp_img_path):
            os.remove(temp_img_path)
    except Exception as e:
        logger.error(f"Error removing temp image {temp_img_path}: {e}")
        
    pdf_data = pdf_buffer.getvalue()
    pdf_buffer.close()
    
    return pdf_data
