import matplotlib.pyplot as plt
plt.switch_backend('Agg') # GUI olmayan sunucular için uyumluluk
import matplotlib.dates as mdates
import io
import pandas as pd

def create_tech_chart(ticker, df):
    """
    Creates a professional technical analysis chart.
    df: DataFrame with Date index and Open, High, Low, Close columns.
    """
    # Create copy to avoid modifying original
    data = df.tail(250).copy() # Last ~1 year
    
    # Calculate indicators if missing
    if 'SMA50' not in data.columns:
        data['SMA50'] = data['Close'].rolling(window=50).mean()
    if 'SMA200' not in data.columns:
        data['SMA200'] = data['Close'].rolling(window=200).mean()
        
    if 'RSI' not in data.columns:
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        data['RSI'] = 100 - (100 / (1 + rs))

    # Set Style
    plt.style.use('dark_background')
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), gridspec_kw={'height_ratios': [3, 1]})
    fig.patch.set_facecolor('#121212')
    ax1.set_facecolor('#121212')
    ax2.set_facecolor('#121212')

    # Plot Price and SMAs
    ax1.plot(data.index, data['Close'], label='Fiyat', color='#00d1ff', linewidth=1.5, alpha=0.8)
    ax1.plot(data.index, data['SMA50'], label='SMA 50', color='#ffbe0b', linewidth=1.2)
    ax1.plot(data.index, data['SMA200'], label='SMA 200', color='#ff006e', linewidth=1.2)
    
    # Shade Golden Cross / Death Cross areas
    ax1.fill_between(data.index, data['SMA50'], data['SMA200'], 
                     where=(data['SMA50'] >= data['SMA200']), color='green', alpha=0.1, interpolate=True)
    ax1.fill_between(data.index, data['SMA50'], data['SMA200'], 
                     where=(data['SMA50'] < data['SMA200']), color='red', alpha=0.1, interpolate=True)

    ax1.set_title(f"{ticker} Teknik Analiz Görünümü", fontsize=16, color='white', pad=20)
    ax1.legend(loc='upper left', frameon=False)
    ax1.grid(color='grey', linestyle='--', linewidth=0.3, alpha=0.5)
    ax1.tick_params(axis='x', colors='white')
    ax1.tick_params(axis='y', colors='white')

    # Plot RSI
    ax2.plot(data.index, data['RSI'], color='#8338ec', linewidth=1.2)
    ax2.axhline(70, color='#fb5607', linestyle='--', linewidth=0.8, alpha=0.7)
    ax2.axhline(30, color='#3a86ff', linestyle='--', linewidth=0.8, alpha=0.7)
    ax2.fill_between(data.index, 70, 30, color='#8338ec', alpha=0.05)
    
    ax2.set_ylabel('RSI', color='white')
    ax2.set_ylim(0, 100)
    ax2.grid(color='grey', linestyle='--', linewidth=0.3, alpha=0.5)
    ax2.tick_params(axis='x', colors='white')
    ax2.tick_params(axis='y', colors='white')

    # Date formatting
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%Y'))
    plt.xticks(rotation=45)

    plt.tight_layout()
    
    # Save to buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=120, facecolor=fig.get_facecolor())
    buf.seek(0)
    plt.close(fig)
    return buf
