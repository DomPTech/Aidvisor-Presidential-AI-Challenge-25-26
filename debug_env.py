import sys
import os
import plotly
import pandas

print(f"Python: {sys.executable}")
print(f"Plotly Version: {plotly.__version__}")
print(f"Pandas Version: {pandas.__version__}")

scanner_path = "/Users/dominick/Presidential-AI-Challenge-25-26-1/app/prediction/scanner.py"
with open(scanner_path, "r") as f:
    lines = f.readlines()
    print(f"Scanner Line 124: {lines[123].strip() if len(lines) > 123 else 'N/A'}")
    print(f"Scanner Line 126: {lines[125].strip() if len(lines) > 125 else 'N/A'}")
