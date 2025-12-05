#!/usr/bin/env python3
"""
Test script for FastAPI symbol counting endpoint
"""

import requests
import json

# Test local endpoint
url = "http://127.0.0.1:8000/count/local"

data = {
    "pdf_filename": "H.pdf",
    "symbol_filename": "image.png",
    "threshold": 0.65,
    "dpi": 300
}

print("="*70)
print("Testing Symbol Counting API")
print("="*70)
print(f"\nEndpoint: {url}")
print(f"PDF: {data['pdf_filename']}")
print(f"Symbol: {data['symbol_filename']}")
print(f"Threshold: {data['threshold']}")
print(f"DPI: {data['dpi']}\n")

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
        
        print(f"\nFull response saved to: outputs/api_test_result.json")
        with open("outputs/api_test_result.json", 'w') as f:
            json.dump(result, f, indent=2)
    else:
        print(f"ERROR: {response.status_code}")
        print(response.text)

except requests.exceptions.ConnectionError:
    print("ERROR: Could not connect to API server.")
    print("Make sure the server is running:")
    print("  python api/fastapi_symbol_count.py")
    print("  or")
    print("  START_SYMBOL_COUNT_API.bat")
except Exception as e:
    print(f"ERROR: {e}")

