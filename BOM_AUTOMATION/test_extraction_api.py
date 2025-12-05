#!/usr/bin/env python3
"""Test the symbol extraction API"""
import requests
import json
from pathlib import Path

# Test local endpoint
url = "http://127.0.0.1:8001/extract/local"

data = {
    "pdf_filename": "H.pdf",
    "min_count": 1,
    "include_images": True,
    "save_templates": True
}

print("="*70)
print("Testing Symbol Extraction API")
print("="*70)
print(f"\nEndpoint: {url}")
print(f"PDF: {data['pdf_filename']}")
print(f"Min count: {data['min_count']}")
print(f"Include images: {data['include_images']}\n")

try:
    print("Sending request...")
    response = requests.post(url, data=data, timeout=300)  # 5 min timeout
    
    if response.status_code == 200:
        result = response.json()
        print("="*70)
        print("SUCCESS")
        print("="*70)
        print(f"\nSummary:")
        print(f"  Total symbols: {result['summary']['total_symbols']}")
        print(f"  Unique symbols: {result['summary']['unique_symbols']}")
        print(f"  Total pages: {result['summary']['total_pages']}")
        print(f"  Symbols with images: {result['summary'].get('symbols_with_images', 0)}")
        
        print(f"\nTop 10 symbols by count:")
        for i, symbol in enumerate(result['symbols'][:10], 1):
            print(f"  {i}. Count: {symbol['count']:3d} | "
                  f"Size: {symbol['width']:.1f}x{symbol['height']:.1f} | "
                  f"Signature: {symbol['signature'][:40]}...")
            if symbol.get('image_filename'):
                print(f"     Image: {symbol['image_filename']}")
        
        print(f"\nPer-page breakdown:")
        for page in result['pages']:
            print(f"  Page {page['page']}: {page['symbol_count']} symbols, "
                  f"{page['unique_patterns']} unique patterns")
        
        # Save full response
        output_file = Path("outputs") / "api_extraction_result.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\n[OK] Full response saved to: {output_file}")
        
        # Save summary without base64 images (smaller file)
        summary = {
            "summary": result['summary'],
            "symbols": [
                {
                    "signature": s['signature'],
                    "count": s['count'],
                    "width": s['width'],
                    "height": s['height'],
                    "image_filename": s.get('image_filename'),
                    "instances": len(s['instances'])
                }
                for s in result['symbols']
            ],
            "pages": result['pages']
        }
        summary_file = Path("outputs") / "api_extraction_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        print(f"[OK] Summary (without images) saved to: {summary_file}")
        
    else:
        print(f"ERROR: {response.status_code}")
        print(response.text)

except requests.exceptions.ConnectionError:
    print("ERROR: Could not connect to API server.")
    print("Make sure the server is running:")
    print("  python api/fastapi_symbol_extraction.py")
    print("  or")
    print("  START_SYMBOL_EXTRACTION_API.bat")
except requests.exceptions.Timeout:
    print("ERROR: Request timed out. PDF processing may take a while for large files.")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

