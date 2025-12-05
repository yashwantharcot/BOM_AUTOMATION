#!/usr/bin/env python3
"""
Test symbol counting using existing infrastructure
Works with or without OpenCV
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.symbol_detector import SymbolTemplate, SymbolDetector
import pymupdf as fitz
from PIL import Image
import numpy as np

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
    
    # Step 1: Upload template to MongoDB
    print("\n[1/4] Uploading template to MongoDB...")
    try:
        template_mgr = SymbolTemplate()
        doc_id = template_mgr.upload_symbol("test_symbol", str(template_path))
        template_mgr.close()
        print(f"[OK] Template uploaded (ID: {doc_id})")
    except Exception as e:
        print(f"[ERROR] Failed to upload template: {e}")
        print("[INFO] Trying to continue with existing template...")
    
    # Step 2: Load templates
    print("\n[2/4] Loading templates from MongoDB...")
    try:
        template_mgr = SymbolTemplate()
        symbols = template_mgr.list_symbols()
        
        templates_dict = {}
        for sym in symbols:
            symbol_name = sym.get('symbol_name')
            print(f"  Loading: {symbol_name}...")
            
            # Try to get symbol image
            try:
                img = template_mgr.get_symbol(symbol_name)
                if img is not None:
                    templates_dict[symbol_name] = img
                    print(f"    [OK] Loaded {symbol_name}")
                else:
                    print(f"    [WARN] Could not load {symbol_name} image")
            except Exception as e:
                print(f"    [WARN] Error loading {symbol_name}: {e}")
                # Try loading directly from file
                if symbol_name == "test_symbol" and template_path.exists():
                    try:
                        from PIL import Image as PILImage
                        pil_img = PILImage.open(str(template_path))
                        img_array = np.array(pil_img)
                        templates_dict[symbol_name] = img_array
                        print(f"    [OK] Loaded {symbol_name} from file")
                    except Exception as e2:
                        print(f"    [ERROR] Failed to load from file: {e2}")
        
        template_mgr.close()
        
        if not templates_dict:
            print("[ERROR] No templates loaded")
            return False
        
        print(f"[OK] Loaded {len(templates_dict)} template(s)")
        
    except Exception as e:
        print(f"[ERROR] Failed to load templates: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 3: Detect symbols
    print(f"\n[3/4] Detecting symbols in PDF...")
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
        return False
    
    # Step 4: Display results
    print("\n[4/4] Results:")
    print("=" * 70)
    
    total_counts = {}
    
    for page_result in results.get('pages', []):
        page_num = page_result.get('page', 0)
        print(f"\nPage {page_num + 1}:")
        
        page_symbols = page_result.get('symbols', {})
        if not page_symbols:
            print("  No symbols detected")
            continue
        
        for symbol_name, symbol_data in page_symbols.items():
            count = symbol_data.get('count', 0)
            detections = symbol_data.get('detections', [])
            
            print(f"  {symbol_name}: {count} symbol(s)")
            
            # Show first few detections
            if detections and count > 0:
                print(f"    Detections:")
                for i, det in enumerate(detections[:3], 1):  # Show first 3
                    bbox = det.get('bbox', [])
                    score = det.get('score', 0)
                    if bbox:
                        print(f"      {i}. BBox: [{bbox[0]:.0f}, {bbox[1]:.0f}, {bbox[2]:.0f}, {bbox[3]:.0f}], Score: {score:.3f}")
                if count > 3:
                    print(f"      ... and {count - 3} more")
            
            # Aggregate
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
    else:
        total_all = sum(total_counts.values())
        print(f"\n  Grand Total: {total_all} symbol(s)")
    
    print("=" * 70)
    
    return True


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





