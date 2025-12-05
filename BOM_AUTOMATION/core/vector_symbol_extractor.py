#!/usr/bin/env python3
"""
Vector-Based Symbol Extractor for CAD PDFs
Extracts symbols directly from vector primitives (paths, lines, shapes)
More accurate than raster-based methods for CAD drawings
"""

import sys
import json
import math
import hashlib
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Tuple, Optional

try:
    import pymupdf as fitz
    HAS_PYMUPDF = True
except ImportError:
    fitz = None
    HAS_PYMUPDF = False
    print("[WARN] PyMuPDF not available, vector extraction disabled")

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    np = None
    HAS_NUMPY = False


class VectorSymbolExtractor:
    """Extract symbols from PDF vector primitives"""
    
    def __init__(self, pdf_path: str):
        if not HAS_PYMUPDF:
            raise ImportError("PyMuPDF required for vector extraction")
        self.pdf_path = pdf_path
        self.doc = fitz.open(pdf_path)
        self.symbols = []
        self.symbol_groups = defaultdict(list)
    
    def extract_drawings(self, page_num: int) -> List[Dict]:
        """Extract all vector drawings from a page"""
        if page_num >= len(self.doc):
            return []
        
        page = self.doc[page_num]
        drawings = page.get_drawings()
        
        vector_items = []
        for draw in drawings:
            item = {
                'type': draw.get('type', 'unknown'),
                'rect': draw.get('rect', []),
                'color': draw.get('color', []),
                'width': draw.get('width', 1.0),
                'fill': draw.get('fill', None),
                'items': draw.get('items', []),  # Path segments
                'closePath': draw.get('closePath', False)
            }
            vector_items.append(item)
        
        return vector_items
    
    def compute_shape_signature(self, drawing: Dict) -> str:
        """Compute a signature for a drawing to identify similar symbols"""
        # Use geometric properties to create a signature
        rect = drawing.get('rect', [])
        if len(rect) < 4:
            return ""
        
        x0, y0, x1, y1 = rect
        width = abs(x1 - x0)
        height = abs(y1 - y0)
        area = width * height
        aspect = width / height if height > 0 else 0
        
        # Count path items
        items = drawing.get('items', [])
        num_segments = len(items)
        
        # Extract path types
        path_types = []
        for item in items:
            if isinstance(item, tuple) and len(item) > 0:
                path_types.append(str(item[0]))
        
        # Create signature from normalized properties
        sig_parts = [
            f"w{int(width*10)}",  # Normalize to 0.1mm precision
            f"h{int(height*10)}",
            f"a{int(area*100)}",
            f"ar{int(aspect*100)}",
            f"n{num_segments}",
            f"t{''.join(path_types[:5])}"  # First 5 path types
        ]
        
        return "_".join(sig_parts)
    
    def normalize_position(self, drawing: Dict, page_width: float, page_height: float) -> Dict:
        """Normalize drawing position relative to page"""
        rect = drawing.get('rect', [])
        if len(rect) < 4:
            return drawing
        
        x0, y0, x1, y1 = rect
        normalized = {
            'x_norm': x0 / page_width if page_width > 0 else 0,
            'y_norm': y0 / page_height if page_height > 0 else 0,
            'width_norm': abs(x1 - x0) / page_width if page_width > 0 else 0,
            'height_norm': abs(y1 - y0) / page_height if page_height > 0 else 0
        }
        return normalized
    
    def extract_symbols_from_page(self, page_num: int) -> Dict:
        """Extract and group symbols from a single page"""
        if page_num >= len(self.doc):
            return {'symbols': [], 'groups': {}}
        
        page = self.doc[page_num]
        page_rect = page.rect
        page_width = page_rect.width
        page_height = page_rect.height
        
        # Extract vector drawings
        drawings = self.extract_drawings(page_num)
        
        # Filter out very large items (likely page borders, title blocks)
        max_area = page_width * page_height * 0.3  # Max 30% of page
        min_area = 10  # Minimum area for a symbol
        
        symbol_candidates = []
        for draw in drawings:
            rect = draw.get('rect', [])
            if len(rect) < 4:
                continue
            
            x0, y0, x1, y1 = rect
            width = abs(x1 - x0)
            height = abs(y1 - y0)
            area = width * height
            
            # Filter by size
            if area < min_area or area > max_area:
                continue
            
            # Filter out very thin lines (likely dimension lines, not symbols)
            if width < 2 and height < 2:
                continue
            
            # Compute signature for grouping
            sig = self.compute_shape_signature(draw)
            if not sig:
                continue
            
            symbol = {
                'signature': sig,
                'bbox': rect,
                'width': width,
                'height': height,
                'area': area,
                'aspect_ratio': width / height if height > 0 else 0,
                'drawing': draw,
                'normalized': self.normalize_position(draw, page_width, page_height)
            }
            
            symbol_candidates.append(symbol)
        
        # Group symbols by signature
        groups = defaultdict(list)
        for sym in symbol_candidates:
            groups[sym['signature']].append(sym)
        
        # Filter groups: only keep symbols that appear multiple times (likely real symbols)
        # Or keep all if we want to see unique symbols too
        filtered_groups = {}
        for sig, syms in groups.items():
            if len(syms) >= 1:  # Keep all symbols, even unique ones
                filtered_groups[sig] = syms
        
        return {
            'page': page_num + 1,
            'symbols': symbol_candidates,
            'groups': {k: len(v) for k, v in filtered_groups.items()},
            'total_symbols': len(symbol_candidates),
            'unique_patterns': len(filtered_groups)
        }
    
    def extract_all_pages(self) -> Dict:
        """Extract symbols from all pages"""
        results = {
            'file': str(self.pdf_path),
            'timestamp': datetime.now().isoformat(),
            'pages': [],
            'summary': {}
        }
        
        all_groups = defaultdict(int)
        total_symbols = 0
        
        for page_num in range(len(self.doc)):
            print(f"\n[PAGE {page_num + 1}/{len(self.doc)}] Extracting vector symbols...")
            page_result = self.extract_symbols_from_page(page_num)
            results['pages'].append(page_result)
            
            # Aggregate statistics
            total_symbols += page_result['total_symbols']
            for sig, count in page_result['groups'].items():
                all_groups[sig] += count
        
        results['summary'] = {
            'total_pages': len(self.doc),
            'total_symbols': total_symbols,
            'unique_patterns': len(all_groups),
            'pattern_counts': dict(all_groups)
        }
        
        return results
    
    def save_symbol_templates(self, output_dir: str = "outputs/vector_symbols", 
                             min_count: int = 2) -> List[str]:
        """Save symbol templates as images (rasterize each unique pattern)"""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        saved_files = []
        all_groups = defaultdict(list)
        
        # Collect all symbols by signature across all pages
        for page_num in range(len(self.doc)):
            page_result = self.extract_symbols_from_page(page_num)
            for sym in page_result['symbols']:
                all_groups[sym['signature']].append((page_num, sym))
        
        # Save templates for patterns that appear multiple times
        for sig, instances in all_groups.items():
            if len(instances) < min_count:
                continue
            
            # Use first instance to create template
            page_num, sym = instances[0]
            page = self.doc[page_num]
            
            # Get bounding box with padding
            bbox = sym['bbox']
            x0, y0, x1, y1 = bbox
            pad = 10
            clip_rect = fitz.Rect(
                max(0, x0 - pad),
                max(0, y0 - pad),
                min(page.rect.width, x1 + pad),
                min(page.rect.height, y1 + pad)
            )
            
            # Rasterize the symbol region
            mat = fitz.Matrix(300 / 72, 300 / 72)  # 300 DPI
            pix = page.get_pixmap(matrix=mat, clip=clip_rect, alpha=False)
            
            # Save as PNG
            sig_hash = hashlib.md5(sig.encode()).hexdigest()[:8]
            filename = f"symbol_{sig_hash}_count{len(instances)}.png"
            filepath = Path(output_dir) / filename
            pix.save(str(filepath))
            
            saved_files.append(str(filepath))
            print(f"  Saved template: {filename} (appears {len(instances)} times)")
        
        return saved_files
    
    def close(self):
        """Close PDF document"""
        if self.doc:
            self.doc.close()


def main():
    if len(sys.argv) < 2:
        print("Usage: python vector_symbol_extractor.py <pdf_path> [--output json_file] [--save-templates]")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    output_file = "outputs/vector_symbols_extracted.json"
    save_templates = "--save-templates" in sys.argv
    
    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        if idx + 1 < len(sys.argv):
            output_file = sys.argv[idx + 1]
    
    if not Path(pdf_path).exists():
        print(f"[ERROR] File not found: {pdf_path}")
        sys.exit(1)
    
    # Extract symbols
    extractor = VectorSymbolExtractor(pdf_path)
    results = extractor.extract_all_pages()
    
    # Save templates if requested
    if save_templates:
        print("\n[Saving symbol templates...]")
        templates = extractor.save_symbol_templates()
        results['templates_saved'] = templates
    
    extractor.close()
    
    # Save JSON
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n[OK] Results saved to: {output_file}")
    print(f"\nSummary:")
    print(f"  Total symbols found: {results['summary']['total_symbols']}")
    print(f"  Unique patterns: {results['summary']['unique_patterns']}")
    print(f"\nTop patterns:")
    sorted_patterns = sorted(
        results['summary']['pattern_counts'].items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]
    for sig, count in sorted_patterns:
        print(f"  {sig[:50]}... : {count} instances")


if __name__ == "__main__":
    main()

