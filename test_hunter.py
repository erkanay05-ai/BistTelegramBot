import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import scanner
import time

try:
    print("Starting Tavan Hunter test...")
    start = time.time()
    results = scanner.scan_ceiling_prospects()
    end = time.time()
    print(f"Success! Scan took {end-start:.2f} seconds.")
    print(f"Found {len(results)} potential candidates.")
    for r in results:
        print(f"- {r['Ticker']}: Score {r['Score']} (Vol: {r['VolRatio']}x, Tightness: {r['Tightness%']}%)")
except Exception as e:
    print(f"Error: {e}")
