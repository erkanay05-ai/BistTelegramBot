import os

def fix_files():
    scanner_path = r"c:\Projects\BistTelegramBot\scanner.py"
    main_path = r"c:\Projects\BistTelegramBot\main.py"

    # 1. READ SCANNER.PY
    with open(scanner_path, "r", encoding="utf-8", errors="ignore") as f:
        scanner_content = f.read()

    # Define common mangled patterns found in scanner.py
    replacements = {
        "BaÃ…Å¸lÃ„Â±ksÃ„Â±z Haber": "Başlıksız Haber",
        "Borsa GÃƒÂ¼ndem/KAP": "Borsa Gündem/KAP",
        "AlÃ„Â±cÃ„Â± / GÃƒÂ¼ÃƒÂ§lÃƒÂ¼": "Alıcı / Güçlü",
        "SatÃ„Â±cÃ„Â± / ZayÃ„Â±f": "Satıcı / Zayıf",
        "Bot BoÃ…Å¸altÃ„Â±yor": "Bot Boşaltıyor",
        "Dengeli": "Dengeli",
        "BaÃ„Å¸lantÃ„Â± HatasÃ„Â±": "Bağlantı Hatası",
        "Genel Piyasa DuyarlÃ„Â±lÃ„Â±Ã„Å¸Ã„Â±": "Genel Piyasa Duyarlılığı",
        "Ãƒâ€“lÃƒÂ§ÃƒÂ¼lÃƒÂ¼yor...": "Ölçülüyor...",
        "NÃƒÂ¶tr": "Nötr",
        "GÃƒÂ¼ÃƒÂ§lÃƒÂ¼ Al": "Güçlü Al",
        "GÃƒÂ¼ÃƒÂ§lÃƒÂ¼ Sat": "Güçlü Sat",
        "ÄŸÅ¸â€œË†": "📈",
        "GÃƒÂ¼ÃƒÂ§lÃƒÂ¼ Trend Sinyali": "Güçlü Trend Sinyali",
        "gerÃƒÂ§ekleÃ…Å¸ti": "gerçekleşti",
        "DeÃ„Å¸erleme aÃƒÂ§Ã„Â±sÃ„Â±ndan": "Değerleme açısından",
        "oldukÃƒÂ§a iskontolu": "oldukça iskontolu",
        "fiyatlanmÃ„Â±Ã…Å¸ gÃƒÂ¶rÃƒÂ¼nÃƒÂ¼yor": "fiyatlanmış görünüyor",
        "AÃ…Å¸Ã„Â±rÃ„Â± satÃ„Â±m bÃƒÂ¶lgesinden": "Aşırı satım bölgesinden",
        "dÃƒÂ¶nÃƒÂ¼Ã…Å¸ sinyalleri": "dönüş sinyalleri",
        "gÃƒÂ¼ÃƒÂ§lÃƒÂ¼ bir momentum": "güçlü bir momentum",
        "aÃ…Å¸Ã„Â±rÃ„Â± alÃ„Â±m bÃƒÂ¶lgesinde": "aşırı alım bölgesinde",
        "dÃƒÂ¼zeltme ihtimali yÃƒÂ¼ksek": "düzeltme ihtimali yüksek",
        "gÃƒÂ¶rÃƒÂ¼nÃƒÂ¼m bozulmuÃ…Å¸": "görünüm bozulmuş",
        "Teknik toparlanma emareleri": "Teknik toparlanma emareleri",
        "wadeli gÃƒÂ¶stergeler zayÃ„Â±f": "vadeli göstergeler zayıf",
        "Piyasa net bir yÃƒÂ¶n tayin etmemiÃ…Å¸": "Piyasa net bir yön tayin etmemiş",
        "YÃ„Â±llÃ„Â±k %": "Yıllık %",
        "temettÃƒÂ¼ verimi": "temettü verimi",
        "yastÃ„Â±k gÃƒÂ¶revi gÃƒÂ¶rebilir": "yastık görevi görebilir",
        "Hisse ÃƒÂ¶zelinde": "Hisse özelinde",
        "nÃƒÂ¶tr seviyede": "nötr seviyede"
    }

    for mangled, clean in replacements.items():
        scanner_content = scanner_content.replace(mangled, clean)

    # 2. READ MAIN.PY
    with open(main_path, "r", encoding="utf-8", errors="ignore") as f:
        main_content = f.read()

    main_replacements = {
        "Hassas tarama yapÃ„Â±lÃ„Â±yor": "Hassas tarama yapılıyor",
        "LÃƒÂ¼tfen geÃƒÂ§erli": "Lütfen geçerli",
        "risk analizi yapÃ„Â±lÃ„Â±yor": "risk analizi yapılıyor",
        "Veri bulunamadÃ„Â±": "Veri bulunamadı",
        "LÃƒÂ¼tfen bir hisse kodu yazÃ„Â±n": "Lütfen bir hisse kodu yazın",
        "verileri analiz ediliyor": "verileri analiz ediliyor",
        "Hisse detaylarÃ„Â± alÃ„Â±nÃ„Â±yor": "Hisse detayları alınıyor",
        "Teknik Sinyal": "Teknik Sinyal",
        "Uzman GÃƒÂ¶rÃƒÂ¼Ã…Å¸ÃƒÂ¼": "Uzman Görüşü"
    }

    for mangled, clean in main_replacements.items():
        main_content = main_content.replace(mangled, clean)

    # 3. WRITE BACK CLEAN UTF-8
    with open(scanner_path, "w", encoding="utf-8") as f:
        f.write(scanner_content)
    
    with open(main_path, "w", encoding="utf-8") as f:
        f.write(main_content)

    print("Success: Files repaired with clean UTF-8 encoding.")

if __name__ == "__main__":
    fix_files()
