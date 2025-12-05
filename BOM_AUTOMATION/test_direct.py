#!/usr/bin/env python3
"""
Direct test script - bypasses API, tests symbol detection directly
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.symbol_detector import SymbolTemplate, SymbolDetector

def test_direct():
    """Test symbol detection directly"""
    
    print("=" * 70)
    print("Direct Symbol Detection Test")
    print("=" * 70)
    
    template_path = Path("inputs/templates/image4545.png")
    pdf_path = Path("uploads/H.pdf")
    
    if not template_path.exists():
        print(f"[ERROR] Template not found: {template_path}")
        return False
    
    if not pdf_path.exists():
        print(f"[ERROR] PDF not found: {pdf_path}")
        print("        Available PDFs:")
        for pdf in Path("uploads").glob("*.pdf"):
            print(f"          - {pdf}")
        return False
    
    # Step 1: Upload template
    print("\n[1/3] Uploading symbol template...")
    try:
        template_mgr = SymbolTemplate()
        doc_id = template_mgr.upload_symbol("test_symbol", str(template_path))
        template_mgr.close()
        
        if doc_id:
            print(f"[OK] Template uploaded: test_symbol")
        else:
            print("[WARN] Template upload returned None (may already exist)")
    except Exception as e:
        print(f"[ERROR] Failed to upload template: {e}")
        return False
    
    # Step 2: Load templates
    print("\n[2/3] Loading templates...")
    try:
        template_mgr = SymbolTemplate()
        symbols = template_mgr.list_symbols()
        
        templates_dict = {}
        for sym in symbols:
            symbol_name = sym.get('symbol_name')
            img = template_mgr.get_symbol(symbol_name)
            if img is not None:
                templates_dict[symbol_name] = img
                print(f"  [OK] Loaded: {symbol_name}")
        
        template_mgr.close()
        
        if not templates_dict:
            print("[ERROR] No templates loaded")
            return False
        
    except Exception as e:
        print(f"[ERROR] Failed to load templates: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 3: Detect symbols
    print(f"\n[3/3] Detecting symbols in {pdf_path.name}...")
    try:
        detector = SymbolDetector()
        results = detector.detect_symbols_in_pdf(
            str(pdf_path),
            templates_dict,
            dpi=300,
            match_thresh=0.75
        )
        
        print("\n" + "=" * 70)
        print("DETECTION RESULTS")
        print("=" * 70)
        
        # Aggregate counts
        total_counts = {}
        for page_result in results.get('pages', []):
            page_num = page_result.get('page', 0)
            print(f"\nPage {page_num + 1}:")
            
            for symbol_name, symbol_data in page_result.get('symbols', {}).items():
                count = symbol_data.get('count', 0)
                print(f"  {symbol_name}: {count}")
                
                if symbol_name not in total_counts:
                    total_counts[symbol_name] = 0
                total_counts[symbol_name] += count
        
        print("\n" + "=" * 70)
        print("TOTAL COUNTS:")
        for symbol_name, count in total_counts.items():
            print(f"  {symbol_name}: {count}")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Detection failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = test_direct()
    sys.exit(0 if success else 1)





