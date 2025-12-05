#!/usr/bin/env python3
"""
Simple standalone symbol detection test
Doesn't require MongoDB - uses template directly from file
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    import cv2
    import numpy as np
    import pymupdf as fitz
    HAS_REQUIRED = True
except ImportError as e:
    print(f"[ERROR] Missing required library: {e}")
    print("Install with: pip install opencv-python pymupdf numpy")
    sys.exit(1)

from detectors.template_matcher import match_template
from core.symbol_detector import SymbolDetector


def test_symbol_detection():
    """Test symbol detection with template file and PDF"""
    
    print("=" * 70)
    print("Simple Symbol Detection Test")
    print("=" * 70)
    
    template_path = Path("inputs/templates/image4545.png")
    pdf_path = Path("uploads/H.pdf")
    
    # Check files exist
    if not template_path.exists():
        print(f"[ERROR] Template not found: {template_path}")
        print("\nAvailable templates:")
        for tpl in Path("inputs/templates").glob("*.png"):
            print(f"  - {tpl}")
        return False
    
    if not pdf_path.exists():
        print(f"[ERROR] PDF not found: {pdf_path}")
        print("\nAvailable PDFs:")
        for pdf in Path("uploads").glob("*.pdf"):
            print(f"  - {pdf}")
        # Use first available PDF
        pdfs = list(Path("uploads").glob("*.pdf"))
        if pdfs:
            pdf_path = pdfs[0]
            print(f"\n[*] Using: {pdf_path}")
        else:
            return False
    
    # Load template
    print(f"\n[1/3] Loading template: {template_path.name}")
    template_img = cv2.imread(str(template_path))
    if template_img is None:
        print(f"[ERROR] Failed to load template image")
        return False
    
    template_gray = cv2.cvtColor(template_img, cv2.COLOR_BGR2GRAY)
    print(f"[OK] Template loaded: {template_gray.shape}")
    
    # Open PDF
    print(f"\n[2/3] Processing PDF: {pdf_path.name}")
    doc = fitz.open(str(pdf_path))
    total_pages = doc.page_count
    print(f"[OK] PDF has {total_pages} page(s)")
    
    # Process each page
    print(f"\n[3/3] Detecting symbols...")
    all_results = []
    total_count = 0
    
    for page_num in range(total_pages):
        print(f"\n  Processing page {page_num + 1}/{total_pages}...")
        
        # Convert page to image
        page = doc[page_num]
        pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))
        img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
            pix.height, pix.width, pix.n
        )
        
        # Convert to grayscale
        if len(img_array.shape) == 3:
            page_gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
        else:
            page_gray = img_array
        
        # Detect symbols with multi-scale and multi-rotation
        detections = match_template(
            page_gray,
            template_gray,
            scales=[0.8, 0.9, 1.0, 1.1, 1.2],
            rotations=[0, 90, 180, 270],
            thresh=0.75
        )
        
        print(f"    Found {len(detections)} potential matches")
        
        # Apply Non-Maximum Suppression
        if detections:
            boxes = [d['bbox'] for d in detections]
            scores = [d['score'] for d in detections]
            keep_idx = SymbolDetector.non_max_suppression(boxes, scores, iou_thresh=0.25)
            
            final_detections = [detections[i] for i in keep_idx]
            count = len(final_detections)
            
            print(f"    After NMS: {count} symbols detected")
            
            all_results.append({
                'page': page_num + 1,
                'count': count,
                'detections': final_detections
            })
            
            total_count += count
        else:
            all_results.append({
                'page': page_num + 1,
                'count': 0,
                'detections': []
            })
    
    doc.close()
    
    # Print results
    print("\n" + "=" * 70)
    print("DETECTION RESULTS")
    print("=" * 70)
    print(f"\nTemplate: {template_path.name}")
    print(f"PDF: {pdf_path.name}")
    print(f"\nTotal Symbols Detected: {total_count}")
    print("\nPage-by-Page:")
    for result in all_results:
        print(f"  Page {result['page']}: {result['count']} symbol(s)")
    
    if total_count > 0:
        print("\nDetection Details:")
        for result in all_results:
            if result['count'] > 0:
                print(f"\n  Page {result['page']}:")
                for i, det in enumerate(result['detections'][:5], 1):  # Show first 5
                    bbox = det['bbox']
                    score = det['score']
                    print(f"    {i}. BBox: [{bbox[0]:.1f}, {bbox[1]:.1f}, {bbox[2]:.1f}, {bbox[3]:.1f}], Score: {score:.3f}")
                if result['count'] > 5:
                    print(f"    ... and {result['count'] - 5} more")
    
    print("\n" + "=" * 70)
    print("[OK] Test completed!")
    print("=" * 70)
    
    return True


if __name__ == '__main__':
    try:
        success = test_symbol_detection()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n[INFO] Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)





