import os

def exhaustive_fix():
    paths = [r"c:\Projects\BistTelegramBot\scanner.py", r"c:\Projects\BistTelegramBot\main.py"]
    
    # Mapping of mangled patterns to correct Turkish characters
    # These are common Double-UTF8 / Mojibake patterns
    maps = {
        "Ã„Â±": "ı",
        "Ã…Å¸": "ş",
        "Ã„Å¸": "ğ",
        "ÃƒÂ¼": "ü",
        "ÃƒÂ¶": "ö",
        "Ãƒâ€¡": "Ç",
        "Ã„Â°": "İ",
        "Ã…Â¸": "Ş",
        "Ã–": "Ö",
        "Ãœ": "Ü",
        "Ã§": "ç",
        "Ã¶": "ö",
        "Ã¼": "ü",
        "ÃŸ": "ş",
        "Ã²": "ğ",
        "Ã³": "ı"
    }

    for path in paths:
        if not os.path.exists(path): continue
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        
        orig_len = len(content)
        for mangled, clean in maps.items():
            content = content.replace(mangled, clean)
        
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Repaired: {path}")

if __name__ == "__main__":
    exhaustive_fix()
