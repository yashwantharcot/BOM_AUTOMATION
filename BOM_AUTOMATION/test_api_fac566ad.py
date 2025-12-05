#!/usr/bin/env python3
"""Test FastAPI endpoint for symbol_fac566ad_count2.png"""
import requests
import json

url = "http://127.0.0.1:8000/count/local"

data = {
    "pdf_filename": "H.pdf",
    "symbol_filename": "outputs/vector_symbols/symbol_fac566ad_count2.png",
    "threshold": 0.65,
    "dpi": 300
}

print("="*70)
print("Testing FastAPI Symbol Counting")
print("="*70)
print(f"\nSymbol: symbol_fac566ad_count2.png")
print(f"PDF: H.pdf")
print(f"Threshold: {data['threshold']}\n")

try:
    response = requests.post(url, data=data)
    
    if response.status_code == 200:
        result = response.json()
        print("="*70)
        print("SUCCESS")
        print("="*70)
        print(f"\nTotal Count: {result['total_count']}")
        print("\nPer-page breakdown:")
        for page in result['pages']:
            print(f"  Page {page['page']}: {page['count']} instances")
        
        print(f"\nFull response saved to: outputs/api_fac566ad_result.json")
        with open("outputs/api_fac566ad_result.json", 'w') as f:
            json.dump(result, f, indent=2)
    else:
        print(f"ERROR: {response.status_code}")
        print(response.text)

except requests.exceptions.ConnectionError:
    print("ERROR: API server not running.")
    print("Start it with: START_SYMBOL_COUNT_API.bat")
except Exception as e:
    print(f"ERROR: {e}")

