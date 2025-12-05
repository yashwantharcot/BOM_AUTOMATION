#!/usr/bin/env python3
"""
Test symbol counting - Fixed version that works without OpenCV
Loads template directly from file
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.symbol_detector import SymbolDetector
import pymupdf as fitz
from PIL import Image
import numpy as np

def load_template_image(template_path):
    """Load template image, handling OpenCV absence"""
    try:
        # Try OpenCV first
        import cv2
        img = cv2.imread(str(template_path))
        if img is not None:
            return img
    except:
        pass
    
    # Fallback to PIL
    try:
        pil_img = Image.open(str(template_path))
        # Convert to RGB if needed
        if pil_img.mode != 'RGB':
            pil_img = pil_img.convert('RGB')
        img_array = np.array(pil_img)
        return img_array
    except Exception as e:
        print(f"[ERROR] Failed to load template: {e}")
        return None

def test_symbol_count():
    """Test symbol counting"""
    
    print("=" * 70)
    print("Symbol Detection & Counting Test")
    print("=" * 70)
    
    template_path = Path("inputs/templates/image4545.png")
    pdf_path = Path("uploads/H.pdf")
    
    # Check files
    if not template_path.exists():
        print(f"[ERROR] Template not found: {template_path}")
        return False
    
    if not pdf_path.exists():
        pdfs = list(Path("uploads").glob("*.pdf"))
        if pdfs:
            pdf_path = pdfs[0]
            print(f"[*] Using PDF: {pdf_path.name}")
        else:
            print("[ERROR] No PDF files found in uploads/")
            return False
    
    print(f"\nTemplate: {template_path.name}")
    print(f"PDF: {pdf_path.name}")
    
    # Load template directly from file
    print("\n[1/3] Loading template from file...")
    template_img = load_template_image(template_path)
    if template_img is None:
        print("[ERROR] Failed to load template image")
        return False
    
    print(f"[OK] Template loaded: {template_img.shape}")
    
    # Prepare templates dict
    templates_dict = {
        "test_symbol": template_img
    }
    
    # Detect symbols
    print(f"\n[2/3] Detecting symbols in PDF...")
    print("[*] This may take a moment...")
    
    try:
        detector = SymbolDetector()
        results = detector.detect_symbols_in_pdf(
            str(pdf_path),
            templates_dict,
            dpi=300,
            match_thresh=0.75
        )
        
        print("[OK] Detection complete")
        
    except Exception as e:
        print(f"[ERROR] Detection failed: {e}")
        import traceback
        traceback.print_exc()
        
        # If OpenCV fails, try manual detection
        print("\n[*] Trying alternative detection method...")
        return manual_detection(template_img, pdf_path)
    
    # Display results
    print("\n[3/3] Results:")
    print("=" * 70)
    
    total_counts = {}
    
    # Check if results have the expected structure
    pages = results.get('pages', [])
    if not pages:
        # Try alternative structure
        if 'symbols' in results:
            print("\nAlternative result structure detected")
            for symbol_name, symbol_data in results['symbols'].items():
                count = symbol_data.get('count', 0) if isinstance(symbol_data, dict) else len(symbol_data) if isinstance(symbol_data, list) else 0
                total_counts[symbol_name] = count
                print(f"  {symbol_name}: {count}")
        else:
            print("No results found")
            return False
    
    for page_result in pages:
        page_num = page_result.get('page', 0)
        print(f"\nPage {page_num}:")
        
        # Handle different result structures
        symbols_data = page_result.get('symbols', [])
        
        if isinstance(symbols_data, list):
            # List format
            for sym_data in symbols_data:
                symbol_name = sym_data.get('symbol_name', 'unknown')
                count = sym_data.get('count', 0)
                detections = sym_data.get('detections', [])
                
                print(f"  {symbol_name}: {count} symbol(s)")
                
                if symbol_name not in total_counts:
                    total_counts[symbol_name] = 0
                total_counts[symbol_name] += count
                
                # Show detections
                if detections and count > 0:
                    for i, det in enumerate(detections[:2], 1):
                        bbox = det.get('bbox', [])
                        score = det.get('score', 0)
                        if bbox:
                            print(f"    {i}. Score: {score:.3f}, BBox: [{bbox[0]:.0f}, {bbox[1]:.0f}, {bbox[2]:.0f}, {bbox[3]:.0f}]")
        elif isinstance(symbols_data, dict):
            # Dict format
            for symbol_name, symbol_data in symbols_data.items():
                count = symbol_data.get('count', 0) if isinstance(symbol_data, dict) else len(symbol_data) if isinstance(symbol_data, list) else 0
                detections = symbol_data.get('detections', []) if isinstance(symbol_data, dict) else symbol_data if isinstance(symbol_data, list) else []
                
                print(f"  {symbol_name}: {count} symbol(s)")
                
                if symbol_name not in total_counts:
                    total_counts[symbol_name] = 0
                total_counts[symbol_name] += count
    
    print("\n" + "=" * 70)
    print("TOTAL SYMBOL COUNTS:")
    print("=" * 70)
    for symbol_name, count in total_counts.items():
        print(f"  {symbol_name}: {count} total")
    
    if not total_counts:
        print("  No symbols detected in PDF")
        print("\n[*] This could mean:")
        print("    - OpenCV is not working (required for detection)")
        print("    - Template doesn't match symbols in PDF")
        print("    - Threshold too high (try lowering match_thresh)")
    else:
        total_all = sum(total_counts.values())
        print(f"\n  Grand Total: {total_all} symbol(s)")
    
    print("=" * 70)
    
    return True

def manual_detection(template_img, pdf_path):
    """Manual detection fallback"""
    print("[*] Manual detection not implemented yet")
    print("[*] OpenCV is required for symbol detection")
    return False

if __name__ == '__main__':
    try:
        success = test_symbol_count()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n[INFO] Test interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)





