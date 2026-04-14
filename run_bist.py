import sys
import os

sys.path.append('c:\\Projects\\BistTelegramBot')

from scanner import scan_bist

def main():
    try:
        gc, mom = scan_bist()
        print("\n=== GOLDEN CROSS ===")
        if gc:
            for item in gc: 
                print(f"- {item['Ticker']}: {item['Price']} TL")
        else: 
            print("Yeni kesişim yok.")
            
        print("\n=== MOMENTUM GÜÇLÜ OLANLAR ===")
        if mom:
            for item in mom[:15]:
                bot_icon = "BOT" if item.get('Bot_Score', 0) > 30 else ""
                print(f"- {item['Ticker']} | Skor: {item['Score']} {bot_icon}")
                print(f"  Fiyat: {item['Price']} | Hedef: {item['Target1']} | Bot İzi: {item.get('Bot_Score', 0)}")
        else: 
            print("Kriterlere uygun hisse bulunamadı.")
    except Exception as e:
        print(f"Hata: {e}")

if __name__ == '__main__':
    main()
