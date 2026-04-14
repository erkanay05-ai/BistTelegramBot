import pandas as pd

def summarize_analysis(file_path='tavan_analysis_results.csv'):
    try:
        df = pd.read_csv(file_path)
        print(f"📊 **ANALİZ ÖZETİ: {file_path}**")
        print(f"Toplam Tavan Olayı: {len(df)}")
        print("-" * 30)
        
        # Performance metrics
        avg_gain_5d = df['Max_Gain_5D'].mean()
        avg_gain_10d = df['Max_Gain_10D'].mean()
        avg_dd_5d = df['Max_DD_5D'].mean()
        
        print(f"📈 5 Günlük Ort. Max Getiri: %{avg_gain_5d:.2f}")
        print(f"📈 10 Günlük Ort. Max Getiri: %{avg_gain_10d:.2f}")
        print(f"📉 5 Günlük Ort. Max Kayıp: %{avg_dd_5d:.2f}")
        print("-" * 30)
        
        # Indicator analysis
        avg_rsi = df['RSI_Entry'].mean()
        avg_vol = df['Vol_Ratio_Entry'].mean()
        
        print(f"📏 İdeal Giriş RSI (Ortalama): {avg_rsi:.2f}")
        print(f"🔊 İdeal Hacim Oranı (Ortalama): {avg_vol:.2f}")
        
        # Sector analysis
        print("\n🏢 **Sektörel Dağılım Top 5:**")
        print(df['Sector'].value_counts().head(5))
        
    except Exception as e:
        print(f"❌ Hata: {e}")

if __name__ == "__main__":
    summarize_analysis()
