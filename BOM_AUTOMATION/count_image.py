#!/usr/bin/env python3
"""Quick script to count image.png in H.pdf"""
import sys
sys.path.insert(0, '.')
from count_symbol import count_symbol_in_pdf
import json
from pathlib import Path

pdf_path = "H.pdf"
symbol_path = r"C:\Users\Arcot Yashwanth\Downloads\BOM_AUTOMATION\BOM_AUTOMATION\image.png"

print("="*70)
print("COUNTING SYMBOL: image.png")
print("="*70)
print(f"PDF: {pdf_path}")
print(f"Template: {symbol_path}\n")

results = count_symbol_in_pdf(pdf_path, symbol_path, dpi=300, match_thresh=0.65)

if results:
    print("\n" + "="*70)
    print("RESULTS")
    print("="*70)
    print(f"TOTAL COUNT: {results['total_count']}")
    print("\nPer-page breakdown:")
    for page_result in results['pages']:
        print(f"  Page {page_result['page']}: {page_result['count']} instances")
        if page_result['detections']:
            avg_score = sum(d['score'] for d in page_result['detections']) / len(page_result['detections'])
            print(f"    Average confidence: {avg_score:.3f}")
    
    # Save results
    output_file = Path("outputs") / "symbol_count_image.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n[OK] Detailed results saved to: {output_file}")
else:
    print("[ERROR] Counting failed")

