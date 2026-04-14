import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import engine_viz
import yfinance as yf

try:
    print("Downloading data...")
    df = yf.download('THYAO.IS', period='1y', progress=False)
    print("Generating chart...")
    buf = engine_viz.create_tech_chart('THYAO', df)
    with open('test_chart.png', 'wb') as f:
        f.write(buf.getbuffer())
    print("Success: test_chart.png created.")
except Exception as e:
    print(f"Error: {e}")
