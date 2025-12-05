#!/usr/bin/env python3
"""
Test script for symbol detection API
Uploads template and tests detection on PDF
"""

import requests
import sys
from pathlib import Path

API_BASE = "http://localhost:5001"

def test_symbol_detection():
    """Test symbol detection with template and PDF"""
    
    print("=" * 70)
    print("Symbol Detection API Test")
    print("=" * 70)
    
    # Step 1: Upload symbol template
    print("\n[1/3] Uploading symbol template...")
    template_path = Path("inputs/templates/image4545.png")
    
    if not template_path.exists():
        print(f"[ERROR] Template not found: {template_path}")
        return False
    
    with open(template_path, 'rb') as f:
        files = {'file': ('image4545.png', f, 'image/png')}
        data = {'name': 'test_symbol'}
        
        try:
            response = requests.post(f"{API_BASE}/api/test/upload-template", files=files, data=data)
            response.raise_for_status()
            result = response.json()
            print(f"[OK] Template uploaded: {result.get('message')}")
            print(f"     Image shape: {result.get('image_shape')}")
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Failed to upload template: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"     Response: {e.response.text}")
            return False
    
    # Step 2: List templates
    print("\n[2/3] Listing templates...")
    try:
        response = requests.get(f"{API_BASE}/api/test/templates")
        response.raise_for_status()
        result = response.json()
        print(f"[OK] Templates: {result.get('templates')}")
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed to list templates: {e}")
        return False
    
    # Step 3: Test with PDF
    print("\n[3/3] Testing detection on PDF...")
    
    # Find a PDF in uploads folder
    pdf_files = list(Path("uploads").glob("*.pdf"))
    if not pdf_files:
        print("[ERROR] No PDF files found in uploads/ folder")
        print("        Please add a PDF file to uploads/ folder")
        return False
    
    pdf_path = pdf_files[0]  # Use first PDF found
    print(f"[*] Using PDF: {pdf_path.name}")
    
    with open(pdf_path, 'rb') as f:
        files = {'file': (pdf_path.name, f, 'application/pdf')}
        
        try:
            print("[*] Sending request...")
            response = requests.post(f"{API_BASE}/api/test/detect", files=files)
            response.raise_for_status()
            result = response.json()
            
            print("\n" + "=" * 70)
            print("DETECTION RESULTS")
            print("=" * 70)
            
            results = result.get('results', {})
            print(f"\nPDF File: {results.get('pdf_file')}")
            print(f"Timestamp: {results.get('timestamp')}")
            
            print("\nSymbol Counts:")
            symbol_counts = results.get('symbol_counts', {})
            for symbol_name, count in symbol_counts.items():
                print(f"  {symbol_name}: {count}")
            
            print("\nPage-by-Page Results:")
            for page_result in results.get('page_results', []):
                page_num = page_result.get('page')
                print(f"\n  Page {page_num}:")
                for symbol_name, symbol_data in page_result.get('symbols', {}).items():
                    count = symbol_data.get('count', 0)
                    print(f"    {symbol_name}: {count}")
            
            print("\n" + "=" * 70)
            print("[OK] Test completed successfully!")
            
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Failed to detect symbols: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"     Response: {e.response.text}")
            return False


if __name__ == '__main__':
    # Check if API is running
    try:
        response = requests.get(f"{API_BASE}/api/test/health", timeout=2)
        if response.status_code == 200:
            print("[OK] API is running")
        else:
            print("[ERROR] API returned unexpected status")
            sys.exit(1)
    except requests.exceptions.RequestException:
        print("[ERROR] API is not running!")
        print("\nPlease start the API first:")
        print("  python api/test_symbol_detection_api.py")
        sys.exit(1)
    
    # Run test
    success = test_symbol_detection()
    sys.exit(0 if success else 1)





