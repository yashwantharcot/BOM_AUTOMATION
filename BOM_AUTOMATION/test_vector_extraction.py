#!/usr/bin/env python3
"""
Test script for vector symbol extraction
Run: python test_vector_extraction.py H.pdf
"""

import sys
from pathlib import Path

# Add core to path
sys.path.insert(0, str(Path(__file__).parent))

from core.vector_symbol_extractor import VectorSymbolExtractor

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_vector_extraction.py <pdf_path>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not Path(pdf_path).exists():
        print(f"[ERROR] File not found: {pdf_path}")
        sys.exit(1)
    
    print("="*70)
    print("VECTOR SYMBOL EXTRACTION TEST")
    print("="*70)
    print(f"PDF: {pdf_path}\n")
    
    extractor = VectorSymbolExtractor(pdf_path)
    
    # Extract from all pages
    results = extractor.extract_all_pages()
    
    # Save templates
    print("\n[Saving symbol templates...]")
    templates = extractor.save_symbol_templates(min_count=1)  # Save all symbols
    
    extractor.close()
    
    # Print summary
    print("\n" + "="*70)
    print("EXTRACTION SUMMARY")
    print("="*70)
    print(f"Total pages: {results['summary']['total_pages']}")
    print(f"Total symbols found: {results['summary']['total_symbols']}")
    print(f"Unique patterns: {results['summary']['unique_patterns']}")
    print(f"Templates saved: {len(templates)}")
    
    print("\nTop 10 patterns by count:")
    sorted_patterns = sorted(
        results['summary']['pattern_counts'].items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]
    
    for i, (sig, count) in enumerate(sorted_patterns, 1):
        print(f"  {i}. Pattern: {sig[:60]}... | Count: {count}")
    
    # Save results
    output_file = "outputs/vector_symbols_extracted.json"
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    
    import json
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n[OK] Results saved to: {output_file}")
    print(f"[OK] Templates saved to: outputs/vector_symbols/")

