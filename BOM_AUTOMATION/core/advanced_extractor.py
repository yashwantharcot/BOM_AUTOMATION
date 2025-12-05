#!/usr/bin/env python3
"""
Advanced CAD Drawing Extractor - Vector & OCR Backend
Extracts: text, symbols, values, relationships with high accuracy
Input: PDF (H.pdf)
Output: JSON with full fidelity
"""

import sys
import json
import re
import math
from pathlib import Path
from datetime import datetime
from collections import defaultdict

try:
    import pymupdf as fitz
    import pytesseract
    from pytesseract import Output
    import cv2
    import numpy as np
    from PIL import Image
    import pandas as pd
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install",
                          "pymupdf", "pytesseract", "opencv-python", 
                          "numpy", "pillow", "pandas"])
    import pymupdf as fitz
    import pytesseract
    from pytesseract import Output
    import cv2
    import numpy as np
    from PIL import Image
    import pandas as pd


class VectorTextExtractor:
    """Extract vector text with precise coordinates and properties"""
    
    def __init__(self, doc, page_num):
        self.doc = doc
        self.page = doc[page_num]
        self.page_num = page_num
        self.texts = []
    
    def extract(self):
        """Extract all vector text elements"""
        try:
            # Method 1: Word-level extraction (best accuracy)
            words = self.page.get_text("words")
            for word_data in words:
                x0, y0, x1, y1, text, block_no, line_no, word_no = word_data
                text = text.strip()
                if not text:
                    continue
                
                self.texts.append({
                    "text": text,
                    "bbox": [x0, y0, x1, y1],
                    "width": x1 - x0,
                    "height": y1 - y0,
                    "center": [(x0 + x1) / 2, (y0 + y1) / 2],
                    "source": "vector",
                    "confidence": 1.0,
                    "block_id": block_no,
                    "line_id": line_no,
                    "word_id": word_no
                })
        except Exception as e:
            print("[WARN] Vector extraction failed: {}".format(e))
        
        return self.texts


class OCRTextExtractor:
    """Extract text via OCR with coordinates and confidence"""
    
    def __init__(self, doc, page_num, zoom=8.33):
        self.doc = doc
        self.page = doc[page_num]
        self.page_num = page_num
        self.zoom = zoom
        self.cv_image = None
        self.texts = []
    
    def extract(self):
        """Extract text via OCR with word-level boxes"""
        try:
            # Rasterize page to high-res image
            mat = fitz.Matrix(self.zoom, self.zoom)
            pix = self.page.get_pixmap(matrix=mat, alpha=False)
            # Direct conversion to cv2 image (no temp file)
            img_array = np.frombuffer(pix.samples, dtype=np.uint8)
            img_array = img_array.reshape(pix.height, pix.width, pix.n)
            if pix.n == 4:
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
            else:
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            self.cv_image = img_array
            
            # Run Tesseract with detailed output
            data = pytesseract.image_to_data(img_array, output_type=Output.DICT)
            
            n_texts = len(data['text'])
            for i in range(n_texts):
                text = data['text'][i].strip()
                if not text:
                    continue
                
                conf = float(data['conf'][i]) / 100.0 if data['conf'][i] != '-1' else 0.0
                
                # Convert coordinates back to original PDF space
                x = data['left'][i] / self.zoom
                y = data['top'][i] / self.zoom
                w = data['width'][i] / self.zoom
                h = data['height'][i] / self.zoom
                
                self.texts.append({
                    "text": text,
                    "bbox": [x, y, x + w, y + h],
                    "width": w,
                    "height": h,
                    "center": [x + w / 2, y + h / 2],
                    "source": "ocr",
                    "confidence": conf,
                    "block_id": -1,
                    "line_id": data['line_num'][i],
                    "word_id": i
                })
        
        except Exception as e:
            print("[WARN] OCR extraction failed: {}".format(e))
        
        return self.texts, self.cv_image


class SymbolDetector:
    """Detect symbols: balloons, weld symbols, datum targets"""
    
    def __init__(self, cv_image):
        self.cv_image = cv_image
        self.symbols = []
    
    def detect_balloons(self, min_radius=5, max_radius=150):
        """Detect circular balloons (item numbers)"""
        try:
            gray = cv2.cvtColor(self.cv_image, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Hough Circle Detection
            circles = cv2.HoughCircles(
                blurred,
                cv2.HOUGH_GRADIENT,
                dp=1.2,
                minDist=25,
                param1=50,
                param2=30,
                minRadius=min_radius,
                maxRadius=max_radius
            )
            
            if circles is not None:
                circles = np.uint16(np.around(circles))
                for circle in circles[0, :]:
                    cx, cy, r = int(circle[0]), int(circle[1]), int(circle[2])
                    self.symbols.append({
                        "type": "balloon",
                        "center": [cx, cy],
                        "radius": r,
                        "confidence": 0.85
                    })
        
        except Exception as e:
            print("[WARN] Balloon detection failed: {}".format(e))
        
        return self.symbols
    
    def detect_rectangles(self, min_area=20, max_area=5000):
        """Detect rectangular boxes (item numbers, datum)"""
        try:
            gray = cv2.cvtColor(self.cv_image, cv2.COLOR_BGR2GRAY)
            _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
            
            contours, _ = cv2.findContours(binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                area = cv2.contourArea(contour)
                if min_area < area < max_area:
                    rect = cv2.boundingRect(contour)
                    x, y, w, h = rect
                    
                    self.symbols.append({
                        "type": "rectangle",
                        "bbox": [x, y, x + w, y + h],
                        "center": [x + w / 2, y + h / 2],
                        "area": area,
                        "confidence": 0.75
                    })
        
        except Exception as e:
            print("[WARN] Rectangle detection failed: {}".format(e))
        
        return self.symbols
    
    def detect_all(self):
        """Run all symbol detection methods"""
        self.detect_balloons()
        self.detect_rectangles()
        return self.symbols


class SymbolPatchExtractor:
    """Extract symbol-like patches from a page image (no prior templates)"""

    def __init__(self, cv_image, text_boxes=None, out_dir=Path("outputs/symbol_patches")):
        self.cv_image = cv_image
        self.text_boxes = text_boxes or []
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def remove_text_regions(self, mask):
        """Mask out known text regions to avoid extracting them as symbols"""
        for bbox in self.text_boxes:
            try:
                x0, y0, x1, y1 = map(int, bbox)
                cv2.rectangle(mask, (x0, y0), (x1, y1), 255, thickness=-1)
            except Exception:
                continue
        return mask

    def extract(self, page_num=0, min_area=1, max_area=1_000_000, min_ar=0.05, max_ar=20.0, save_debug=True):
        if self.cv_image is None:
            return []

        gray = cv2.cvtColor(self.cv_image, cv2.COLOR_BGR2GRAY)
        # Enhance contrast and binarize adaptively for thin CAD strokes
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray_eq = clahe.apply(gray)
        binary = cv2.adaptiveThreshold(
            gray_eq, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 5
        )
        inv = 255 - binary
        # Remove known text regions
        inv = self.remove_text_regions(inv)
        # Merge broken strokes and clean specks (aggressive)
        kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
        inv = cv2.morphologyEx(inv, cv2.MORPH_CLOSE, kernel_close, iterations=2)
        kernel_open = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        inv = cv2.morphologyEx(inv, cv2.MORPH_OPEN, kernel_open, iterations=1)

        if save_debug:
            debug_path = self.out_dir / f"page_{page_num+1}_debug.png"
            try:
                cv2.imwrite(str(debug_path), inv)
            except Exception:
                pass

        contours, _ = cv2.findContours(inv, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        patches = []
        h_img, w_img = inv.shape

        for idx, cnt in enumerate(contours):
            area = cv2.contourArea(cnt)
            if area < min_area or area > max_area:
                continue
            x, y, w, h = cv2.boundingRect(cnt)
            aspect = w / float(h + 1e-6)
            if aspect < min_ar or aspect > max_ar:
                continue

            x0, y0 = max(x - 2, 0), max(y - 2, 0)
            x1, y1 = min(x + w + 2, w_img), min(y + h + 2, h_img)
            patch = self.cv_image[y0:y1, x0:x1]
            filename = f"page_{page_num+1}_symbol_{len(patches)}.png"
            out_path = self.out_dir / filename
            try:
                cv2.imwrite(str(out_path), patch)
            except Exception:
                continue

            patches.append({
                "file": str(out_path),
                "bbox": [int(x0), int(y0), int(x1), int(y1)],
                "area": float(area),
                "aspect_ratio": float(aspect)
            })

        return patches


class ValueExtractor:
    """Extract numeric values, units, and engineering specifications"""
    
    # Regex patterns for common CAD values
    PATTERNS = {
        'bolt': r'\bM\s*(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)\b',
        'thread': r'\bM\s*(\d+(?:\.\d+)?)\b',
        'diameter': r'(?:Ø|phi|diameter)\s*[:=]?\s*(\d+(?:\.\d+)?)',
        'qty': r'\b(?:QTY|Qty|quantity)\s*[:=]?\s*(\d+)\b',
        'dimension': r'(\d+(?:\.\d+)?)\s*(?:mm|cm|in|\")',
        'tolerance': r'±\s*(\d+(?:\.\d+)?)',
        'material': r'(?:Material|Material:)\s*([A-Z0-9\-+\s\.]+?)(?:\n|$)',
        'scale': r'(?:Scale|SCALE)\s*[:=]?\s*([\d:.]+)',
        'date': r'(\d{4})-(\d{2})-(\d{2})',
        'item_number': r'(?:Item\s+(?:no|number)|#)\s*[:=]?\s*(\d+)',
    }
    
    @staticmethod
    def extract_from_text(text):
        """Extract and parse values from text"""
        values = []
        
        for pattern_name, pattern in ValueExtractor.PATTERNS.items():
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                values.append({
                    "type": pattern_name,
                    "value": match.group(1) if match.groups() else match.group(0),
                    "full_match": match.group(0),
                    "confidence": 0.95
                })
        
        return values


class AssociationEngine:
    """Associate symbols to text and features"""
    
    @staticmethod
    def distance(p1, p2):
        """Calculate Euclidean distance"""
        return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)
    
    @staticmethod
    def associate_symbol_to_text(symbol, texts, max_distance=200):
        """Find nearest text to symbol"""
        if 'center' not in symbol:
            return None
        
        center = symbol['center']
        best_text = None
        best_distance = max_distance
        
        for text in texts:
            d = AssociationEngine.distance(center, text['center'])
            if d < best_distance:
                best_distance = d
                best_text = text
        
        return {
            "symbol": symbol,
            "linked_text": best_text,
            "distance": best_distance,
            "confidence": max(0, 1.0 - (best_distance / max_distance))
        }
    
    @staticmethod
    def associate_all(symbols, texts):
        """Associate all symbols to nearest texts"""
        associations = []
        for symbol in symbols:
            assoc = AssociationEngine.associate_symbol_to_text(symbol, texts)
            if assoc:
                associations.append(assoc)
        return associations


class TableExtractor:
    """Extract tables from PDF"""
    
    def __init__(self, doc, page_num):
        self.page = doc[page_num]
        self.tables = []
    
    def extract(self):
        """Extract tables using line detection"""
        try:
            # Get all horizontal and vertical lines
            h_lines = [e for e in self.page.get_drawings() if e['type'] == 'l' and e['rect'][1] == e['rect'][3]]
            v_lines = [e for e in self.page.get_drawings() if e['type'] == 'l' and e['rect'][0] == e['rect'][2]]
            
            if h_lines and v_lines:
                # Potential table grid detected
                self.tables.append({
                    "type": "grid_detected",
                    "h_lines": len(h_lines),
                    "v_lines": len(v_lines),
                    "confidence": 0.7
                })
        
        except Exception as e:
            print("[WARN] Table extraction failed: {}".format(e))
        
        return self.tables


class ConfidenceScorer:
    """Calculate confidence scores for extracted data"""
    
    @staticmethod
    def score_extraction(item):
        """Calculate confidence for an extracted item"""
        scores = []
        
        # Source confidence
        if item.get('source') == 'vector':
            scores.append(('source', 1.0, 0.3))
        elif item.get('source') == 'ocr':
            conf = item.get('confidence', 0.5)
            scores.append(('source', conf, 0.3))
        
        # Pattern confidence
        if item.get('parsed'):
            scores.append(('pattern', 0.95, 0.3))
        
        # Symbol confidence
        if item.get('symbol_linked'):
            scores.append(('symbol', item.get('symbol_confidence', 0.7), 0.2))
        
        # Normalize
        if scores:
            total_weight = sum(w for _, _, w in scores)
            confidence = sum(v * w for _, v, w in scores) / total_weight
        else:
            confidence = item.get('confidence', 0.5)
        
        return min(1.0, max(0.0, confidence))


class CADExtractor:
    """Main extraction engine"""
    
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.doc = fitz.open(pdf_path)
        self.results = {
            'file': str(pdf_path),
            'timestamp': datetime.now().isoformat(),
            'pages': []
        }
    
    def extract_page(self, page_num):
        """Extract all data from a single page"""
        page_data = {
            'page': page_num + 1,
            'vector_text': [],
            'ocr_text': [],
            'symbols': [],
            'symbol_patches': [],
            'associations': [],
            'tables': [],
            'parsed_items': [],
            'statistics': {}
        }
        
        print("\n[PAGE {}] Extracting...".format(page_num + 1))
        
        # 1. Vector text extraction
        print("  [1/6] Vector text extraction...")
        vec_extractor = VectorTextExtractor(self.doc, page_num)
        vector_texts = vec_extractor.extract()
        page_data['vector_text'] = vector_texts
        print("       Found {} vector texts".format(len(vector_texts)))
        
        # 2. OCR extraction
        print("  [2/6] OCR text extraction...")
        ocr_extractor = OCRTextExtractor(self.doc, page_num, zoom=2.5)
        ocr_texts, cv_image = ocr_extractor.extract()
        page_data['ocr_text'] = ocr_texts
        print("       Found {} OCR texts".format(len(ocr_texts)))
        
        # 3. Vector symbol extraction (Option 2 - most accurate for CAD)
        print("  [3/8] Vector symbol extraction...")
        try:
            from core.vector_symbol_extractor import VectorSymbolExtractor
            vec_extractor = VectorSymbolExtractor(self.pdf_path)
            vec_result = vec_extractor.extract_symbols_from_page(page_num)
            page_data['vector_symbols'] = vec_result['symbols']
            page_data['vector_symbol_groups'] = vec_result['groups']
            page_data['vector_symbol_count'] = vec_result['total_symbols']
            vec_extractor.close()
            print("       Found {} vector symbols ({} unique patterns)".format(
                vec_result['total_symbols'], vec_result['unique_patterns']))
        except Exception as e:
            print("       Vector extraction failed: {}".format(e))
            page_data['vector_symbols'] = []
            page_data['vector_symbol_groups'] = {}
            page_data['vector_symbol_count'] = 0
        
        # 4. Symbol patch extraction (template-free raster method)
        print("  [4/8] Symbol patch extraction (raster)...")
        text_boxes = [t['bbox'] for t in (vector_texts + ocr_texts)]
        patch_extractor = SymbolPatchExtractor(cv_image, text_boxes=text_boxes)
        symbol_patches = patch_extractor.extract(page_num=page_num)
        page_data['symbol_patches'] = symbol_patches
        print("       Saved {} symbol patches".format(len(symbol_patches)))
        
        # 5. Symbol detection (heuristic)
        print("  [5/8] Symbol detection (heuristic)...")
        if cv_image is not None:
            symbol_detector = SymbolDetector(cv_image)
            symbols = symbol_detector.detect_all()
            page_data['symbols'] = symbols
            print("       Found {} symbols".format(len(symbols)))
        
        # 6. Associations
        print("  [6/8] Symbol-to-text association...")
        all_texts = vector_texts + ocr_texts
        associations = AssociationEngine.associate_all(page_data['symbols'], all_texts)
        page_data['associations'] = associations
        print("       Created {} associations".format(len(associations)))
        
        # 7. Table extraction
        print("  [7/8] Table detection...")
        table_extractor = TableExtractor(self.doc, page_num)
        tables = table_extractor.extract()
        page_data['tables'] = tables
        print("       Found {} table indicators".format(len(tables)))
        
        # 8. Value extraction and parsing
        print("  [8/8] Value extraction...")
        parsed_items = []
        combined_text = '\n'.join([t['text'] for t in all_texts])
        
        for text_item in all_texts:
            values = ValueExtractor.extract_from_text(text_item['text'])
            
            confidence = ConfidenceScorer.score_extraction({
                'source': text_item['source'],
                'confidence': text_item['confidence'],
                'parsed': values
            })
            
            # Find if this text is linked to symbol
            symbol_link = None
            for assoc in associations:
                if assoc['linked_text'] == text_item:
                    symbol_link = assoc
                    break
            
            item = {
                'text': text_item['text'],
                'bbox': text_item['bbox'],
                'source': text_item['source'],
                'base_confidence': text_item['confidence'],
                'final_confidence': confidence,
                'values': values,
                'symbol_linked': symbol_link is not None,
                'symbol_info': symbol_link['symbol'] if symbol_link else None
            }
            
            parsed_items.append(item)
        
        page_data['parsed_items'] = parsed_items
        print("       Parsed {} items".format(len(parsed_items)))
        
        # Statistics
        page_data['statistics'] = {
            'total_vector_text': len(vector_texts),
            'total_ocr_text': len(ocr_texts),
            'total_symbol_patches': len(symbol_patches),
            'total_symbols': len(page_data['symbols']),
            'total_vector_symbols': page_data.get('vector_symbol_count', 0),
            'total_associations': len(associations),
            'high_confidence_items': sum(1 for i in parsed_items if i['final_confidence'] > 0.9),
            'medium_confidence_items': sum(1 for i in parsed_items if 0.7 < i['final_confidence'] <= 0.9),
            'low_confidence_items': sum(1 for i in parsed_items if i['final_confidence'] <= 0.7)
        }
        
        return page_data
    
    def extract_all(self):
        """Extract from all pages"""
        print("\n" + "="*70)
        print("CAD DRAWING EXTRACTION - VECTOR + OCR + SYMBOLS")
        print("="*70)
        print("File: {}".format(self.pdf_path))
        print("Pages: {}".format(self.doc.page_count))
        
        for page_num in range(self.doc.page_count):
            page_data = self.extract_page(page_num)
            self.results['pages'].append(page_data)
        
        # Summary
        print("\n" + "="*70)
        print("EXTRACTION COMPLETE")
        print("="*70)
        
        return self.results
    
    def close(self):
        """Close PDF"""
        self.doc.close()


def main():
    if len(sys.argv) < 2:
        print("Usage: python extractor.py <pdf_path> [--output json_file]")
        print("Example: python extractor.py H.pdf --output H_extracted_full.json")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    output_file = "extracted_data.json"
    
    if '--output' in sys.argv:
        idx = sys.argv.index('--output')
        if idx + 1 < len(sys.argv):
            output_file = sys.argv[idx + 1]
    
    if not Path(pdf_path).exists():
        print("[ERROR] File not found: {}".format(pdf_path))
        sys.exit(1)
    
    # Extract
    extractor = CADExtractor(pdf_path)
    results = extractor.extract_all()
    extractor.close()
    
    # Save JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print("\n[OK] Results saved to: {}".format(output_file))
    
    # Print summary
    for page in results['pages']:
        print("\nPage {}: {} vector text + {} OCR text + {} symbols".format(
            page['page'],
            page['statistics']['total_vector_text'],
            page['statistics']['total_ocr_text'],
            page['statistics']['total_symbols']
        ))
        print("  High confidence: {} | Medium: {} | Low: {}".format(
            page['statistics']['high_confidence_items'],
            page['statistics']['medium_confidence_items'],
            page['statistics']['low_confidence_items']
        ))


if __name__ == "__main__":
    main()
