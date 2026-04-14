import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import scanner
import time

try:
    print("Starting Trend Hunter test...")
    start = time.time()
    results = scanner.scan_medium_term_trends()
    end = time.time()
    print(f"Success! Scan took {end-start:.2f} seconds.")
    print(f"Found {len(results)} potential trends.")
    for r in results[:5]:
        print(f"- {r['Ticker']}: Strength {r['Strength']} (Dist: {r['Distance%']}%)")
except Exception as e:
    print(f"Error: {e}")
