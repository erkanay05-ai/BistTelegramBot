import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import scanner
import time

try:
    print("Starting Multi-Timeframe Golden Cross Scan Test...")
    print("This will download weekly, daily, and hourly data to scan for crossovers in the last 5 bars.")
    
    start_time = time.time()
    results = scanner.scan_all_golden_cross(lookback=5)
    end_time = time.time()
    
    print(f"\nScan completed in {end_time - start_time:.2f} seconds.")
    print("Results summary:")
    for tf in ['weekly', 'daily', '4h', '2h']:
        tf_results = results.get(tf, [])
        print(f"\nTimeframe: {tf.upper()} (Found {len(tf_results)} crossovers)")
        for r in tf_results[:10]: # Print first 10 for review
            print(f"  - {r['Ticker']}: Crossed on {r['Time']} at {r['CrossPrice']} TL (Latest: {r['Price']} TL)")
        if len(tf_results) > 10:
            print(f"  ... and {len(tf_results) - 10} more.")
            
except Exception as e:
    print(f"Error during test: {e}")
