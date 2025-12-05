#!/usr/bin/env python3
"""
Count occurrences of a specific symbol template in PDF
Usage: python count_symbol.py <pdf_path> <symbol_template.png>
"""

import sys
import json
from pathlib import Path

try:
    import pymupdf as fitz
    import cv2
    import numpy as np
    from PIL import Image
    HAS_DEPS = True
except ImportError as e:
    print(f"[ERROR] Missing dependencies: {e}")
    HAS_DEPS = False

def rasterize_pdf_page(pdf_path, page_num=0, dpi=300):
    """Rasterize PDF page to image"""
    doc = fitz.open(pdf_path)
    page = doc[page_num]
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    
    mode = "RGB" if pix.n < 4 else "RGBA"
    img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
    doc.close()
    
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

def preprocess_for_matching(img):
    """Preprocess image for template matching"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    # Apply CLAHE for better contrast
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    gray = clahe.apply(gray)
    return gray

def multi_scale_template_match(image, template, scales=(0.8, 0.9, 1.0, 1.1, 1.2), 
                               match_thresh=0.7):
    """Multi-scale template matching with NMS"""
    img_gray = preprocess_for_matching(image)
    tpl_gray = preprocess_for_matching(template)
    
    hT, wT = tpl_gray.shape[:2]
    detections = []
    
    for s in scales:
        new_w = int(wT * s)
        new_h = int(hT * s)
        
        if new_w < 5 or new_h < 5:
            continue
        if new_w > img_gray.shape[1] or new_h > img_gray.shape[0]:
            continue
        
        resized = cv2.resize(tpl_gray, (new_w, new_h), interpolation=cv2.INTER_AREA)
        
        try:
            res = cv2.matchTemplate(img_gray, resized, cv2.TM_CCOEFF_NORMED)
            loc = np.where(res >= match_thresh)
            
            for pt in zip(*loc[::-1]):
                score = float(res[pt[1], pt[0]])
                x1, y1 = pt[0], pt[1]
                x2, y2 = x1 + new_w, y1 + new_h
                detections.append({
                    'bbox': [x1, y1, x2, y2],
                    'score': score,
                    'scale': s
                })
        except Exception as e:
            print(f"  Warning: Scale {s} failed: {e}")
            continue
    
    # Non-maximum suppression
    if not detections:
        return []
    
    boxes = np.array([d['bbox'] for d in detections])
    scores = np.array([d['score'] for d in detections])
    
    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 2]
    y2 = boxes[:, 3]
    
    areas = (x2 - x1 + 1) * (y2 - y1 + 1)
    order = scores.argsort()[::-1]
    
    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(i)
        
        if order.size == 1:
            break
        
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        
        w = np.maximum(0.0, xx2 - xx1 + 1)
        h = np.maximum(0.0, yy2 - yy1 + 1)
        inter = w * h
        iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-6)
        
        inds = np.where(iou <= 0.25)[0]  # IoU threshold
        order = order[inds + 1]
    
    return [detections[i] for i in keep]

def count_symbol_in_pdf(pdf_path, symbol_template_path, dpi=300, match_thresh=0.7):
    """Count symbol occurrences across all pages"""
    if not HAS_DEPS:
        return None
    
    # Load template
    template = cv2.imread(str(symbol_template_path))
    if template is None:
        print(f"[ERROR] Could not load template: {symbol_template_path}")
        return None
    
    print(f"Template size: {template.shape[1]}x{template.shape[0]} pixels")
    
    # Open PDF
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    
    results = {
        'pdf': str(pdf_path),
        'template': str(symbol_template_path),
        'pages': [],
        'total_count': 0
    }
    
    print(f"\nProcessing {total_pages} page(s)...")
    
    for page_num in range(total_pages):
        print(f"\n[Page {page_num + 1}/{total_pages}]")
        
        # Rasterize page
        page_img = rasterize_pdf_page(pdf_path, page_num, dpi=dpi)
        print(f"  Page size: {page_img.shape[1]}x{page_img.shape[0]} pixels")
        
        # Match template
        detections = multi_scale_template_match(
            page_img, template, 
            scales=(0.8, 0.9, 1.0, 1.1, 1.2),
            match_thresh=match_thresh
        )
        
        page_result = {
            'page': page_num + 1,
            'count': len(detections),
            'detections': detections
        }
        
        results['pages'].append(page_result)
        results['total_count'] += len(detections)
        
        print(f"  Found: {len(detections)} instances")
        if detections:
            avg_score = sum(d['score'] for d in detections) / len(detections)
            print(f"  Average confidence: {avg_score:.3f}")
    
    doc.close()
    
    return results

def main():
    if len(sys.argv) < 3:
        print("Usage: python count_symbol.py <pdf_path> <symbol_template.png> [--thresh 0.7] [--dpi 300]")
        print("\nExample:")
        print("  python count_symbol.py H.pdf outputs/vector_symbols/symbol_866c86c8_count1.png")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    symbol_path = sys.argv[2]
    
    match_thresh = 0.7
    dpi = 300
    
    if "--thresh" in sys.argv:
        idx = sys.argv.index("--thresh")
        if idx + 1 < len(sys.argv):
            match_thresh = float(sys.argv[idx + 1])
    
    if "--dpi" in sys.argv:
        idx = sys.argv.index("--dpi")
        if idx + 1 < len(sys.argv):
            dpi = int(sys.argv[idx + 1])
    
    if not Path(pdf_path).exists():
        print(f"[ERROR] PDF not found: {pdf_path}")
        sys.exit(1)
    
    if not Path(symbol_path).exists():
        print(f"[ERROR] Symbol template not found: {symbol_path}")
        sys.exit(1)
    
    print("="*70)
    print("SYMBOL COUNTING")
    print("="*70)
    print(f"PDF: {pdf_path}")
    print(f"Template: {symbol_path}")
    print(f"Match threshold: {match_thresh}")
    print(f"DPI: {dpi}")
    
    results = count_symbol_in_pdf(pdf_path, symbol_path, dpi=dpi, match_thresh=match_thresh)
    
    if results is None:
        sys.exit(1)
    
    # Print summary
    print("\n" + "="*70)
    print("RESULTS SUMMARY")
    print("="*70)
    print(f"Total symbol count: {results['total_count']}")
    print("\nPer-page breakdown:")
    for page_result in results['pages']:
        print(f"  Page {page_result['page']}: {page_result['count']} instances")
    
    # Save results
    output_file = Path("outputs") / f"symbol_count_{Path(symbol_path).stem}.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n[OK] Detailed results saved to: {output_file}")
    
    return results['total_count']

if __name__ == "__main__":
    main()

