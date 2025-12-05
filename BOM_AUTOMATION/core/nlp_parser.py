#!/usr/bin/env python3
"""
NLP Parsing Module (Section 6.3)
Detects quantities, dimensions, materials, and table headers/rows
Uses Regex + spaCy custom NER
"""

import re
from typing import List, Dict, Optional
from collections import defaultdict

try:
    import spacy
    HAS_SPACY = True
except ImportError:
    spacy = None
    HAS_SPACY = False


class NLPParser:
    """
    6.3 NLP Parsing
    Detects:
    - Quantities: QTY: 4
    - Dimensions: M8, Ø12.5
    - Materials: SS304, MS, Al6061
    - Table headers & rows
    """
    
    def __init__(self):
        self.nlp = None
        if HAS_SPACY:
            try:
                # Try to load English model
                self.nlp = spacy.load("en_core_web_sm")
            except OSError:
                print("[WARN] spaCy English model not found. Install with: python -m spacy download en_core_web_sm")
                self.nlp = None
    
    def parse_text(self, text: str) -> Dict:
        """
        Parse text and extract structured information
        
        Args:
            text: Input text
            
        Returns:
            Dict with parsed quantities, dimensions, materials, etc.
        """
        result = {
            'quantities': self.extract_quantities(text),
            'dimensions': self.extract_dimensions(text),
            'materials': self.extract_materials(text),
            'standards': self.extract_standards(text),
            'dates': self.extract_dates(text),
            'item_numbers': self.extract_item_numbers(text)
        }
        
        return result
    
    def extract_quantities(self, text: str) -> List[Dict]:
        """
        Extract quantities: QTY: 4
        """
        quantities = []
        
        patterns = [
            (r'QTY[:\s]+(\d+)', 'explicit_qty'),
            (r'QUANTITY[:\s]+(\d+)', 'explicit_quantity'),
            (r'QTY\.?\s*[=:]?\s*(\d+)', 'qty_abbrev'),
            (r'(\d+)\s*(?:pcs|pieces|units|nos|nr)', 'unit_suffix'),
            (r'(\d+)\s*x\s*(?=\d)', 'multiplier'),  # 4x M8
        ]
        
        for pattern, qty_type in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                quantities.append({
                    'value': int(match.group(1)),
                    'type': qty_type,
                    'text': match.group(0),
                    'position': match.start()
                })
        
        return quantities
    
    def extract_dimensions(self, text: str) -> List[Dict]:
        """
        Extract dimensions: M8, Ø12.5, 100x50
        """
        dimensions = []
        
        # Metric threads: M8, M10, M12x1.5
        metric_thread_pattern = r'M(\d+(?:\.\d+)?)(?:[xX](\d+(?:\.\d+)?))?'
        for match in re.finditer(metric_thread_pattern, text):
            dimensions.append({
                'type': 'metric_thread',
                'diameter': float(match.group(1)),
                'pitch': float(match.group(2)) if match.group(2) else None,
                'text': match.group(0),
                'position': match.start()
            })
        
        # Diameter: Ø12.5, Ø 12.5, DIA 12.5
        diameter_patterns = [
            r'[ØØDIA][\s:]?(\d+(?:\.\d+)?)',
            r'DIAMETER[\s:]?(\d+(?:\.\d+)?)'
        ]
        for pattern in diameter_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                dimensions.append({
                    'type': 'diameter',
                    'value': float(match.group(1)),
                    'text': match.group(0),
                    'position': match.start()
                })
        
        # Rectangular: 100x50, 100 x 50, 100×50
        rectangular_pattern = r'(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)'
        for match in re.finditer(rectangular_pattern, text):
            dimensions.append({
                'type': 'rectangular',
                'width': float(match.group(1)),
                'height': float(match.group(2)),
                'text': match.group(0),
                'position': match.start()
            })
        
        # Length: L=100, LENGTH=100
        length_pattern = r'L(?:ENGTH)?[=:]?\s*(\d+(?:\.\d+)?)'
        for match in re.finditer(length_pattern, text, re.IGNORECASE):
            dimensions.append({
                'type': 'length',
                'value': float(match.group(1)),
                'text': match.group(0),
                'position': match.start()
            })
        
        return dimensions
    
    def extract_materials(self, text: str) -> List[Dict]:
        """
        Extract materials: SS304, MS, Al6061
        """
        materials = []
        
        # Common material patterns
        patterns = [
            (r'SS(\d+)', 'stainless_steel', lambda m: f'Stainless Steel {m.group(1)}'),
            (r'STAINLESS[\s-]?STEEL[\s-]?(\d+)', 'stainless_steel', lambda m: f'Stainless Steel {m.group(1)}'),
            (r'AL(\d+)', 'aluminum', lambda m: f'Aluminum {m.group(1)}'),
            (r'ALUMINUM[\s-]?(\d+)', 'aluminum', lambda m: f'Aluminum {m.group(1)}'),
            (r'\bMS\b', 'mild_steel', lambda m: 'Mild Steel'),
            (r'MILD[\s-]?STEEL', 'mild_steel', lambda m: 'Mild Steel'),
            (r'CARBON[\s-]?STEEL', 'carbon_steel', lambda m: 'Carbon Steel'),
            (r'CS(\d+)', 'carbon_steel', lambda m: f'Carbon Steel {m.group(1)}'),
        ]
        
        for pattern, category, formatter in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                materials.append({
                    'original': match.group(0),
                    'normalized': formatter(match),
                    'category': category,
                    'text': match.group(0),
                    'position': match.start()
                })
        
        return materials
    
    def extract_standards(self, text: str) -> List[Dict]:
        """
        Extract standards: EN 10025, ASTM A36, ISO 9001
        """
        standards = []
        
        patterns = [
            (r'EN[\s-]?(\d+(?:[\s-]?:\d+)?)', 'EN'),
            (r'ASTM[\s-]?([A-Z]\d+)', 'ASTM'),
            (r'ISO[\s-]?(\d+(?:[\s-]?\d+)?)', 'ISO'),
            (r'DIN[\s-]?(\d+)', 'DIN'),
            (r'ANSI[\s-]?([A-Z]\d+)', 'ANSI'),
            (r'BS[\s-]?(\d+)', 'BS'),
        ]
        
        for pattern, standard_type in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                standards.append({
                    'type': standard_type,
                    'number': match.group(1),
                    'full': match.group(0),
                    'text': match.group(0),
                    'position': match.start()
                })
        
        return standards
    
    def extract_dates(self, text: str) -> List[Dict]:
        """Extract dates in various formats"""
        dates = []
        
        patterns = [
            (r'(\d{4}[-/]\d{2}[-/]\d{2})', 'YYYY-MM-DD'),
            (r'(\d{2}[-/]\d{2}[-/]\d{4})', 'DD-MM-YYYY'),
            (r'(\d{1,2}[-/]\d{1,2}[-/]\d{4})', 'M-D-YYYY'),
        ]
        
        for pattern, date_format in patterns:
            for match in re.finditer(pattern, text):
                dates.append({
                    'date': match.group(1),
                    'format': date_format,
                    'text': match.group(0),
                    'position': match.start()
                })
        
        return dates
    
    def extract_item_numbers(self, text: str) -> List[Dict]:
        """Extract item numbers, part numbers, etc."""
        item_numbers = []
        
        patterns = [
            (r'ITEM[\s#:]?\s*(\d+)', 'item_number'),
            (r'PART[\s#:]?\s*([A-Z0-9-]+)', 'part_number'),
            (r'PN[\s:]?\s*([A-Z0-9-]+)', 'part_number'),
            (r'REF[\s#:]?\s*([A-Z0-9-]+)', 'reference'),
        ]
        
        for pattern, item_type in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                item_numbers.append({
                    'type': item_type,
                    'value': match.group(1),
                    'text': match.group(0),
                    'position': match.start()
                })
        
        return item_numbers
    
    def detect_table_headers(self, rows: List[List[str]]) -> Optional[List[str]]:
        """
        Detect table headers from rows
        Usually the first row contains headers
        """
        if not rows or len(rows) == 0:
            return None
        
        # First row is likely headers
        first_row = rows[0]
        
        # Check if first row looks like headers (contains text, not numbers)
        header_score = sum(1 for cell in first_row if cell and not cell.replace('.', '').replace('-', '').isdigit())
        
        if header_score > len(first_row) * 0.5:  # More than 50% text
            return first_row
        
        return None
    
    def parse_table_row(self, row: List[str], headers: Optional[List[str]] = None) -> Dict:
        """
        Parse a table row into key-value pairs
        """
        if headers:
            # Map row cells to headers
            row_dict = {}
            for i, header in enumerate(headers):
                if i < len(row):
                    key = self._normalize_header(header)
                    row_dict[key] = row[i] if row[i] else None
            return row_dict
        else:
            # Assume first column is key, second is value
            if len(row) >= 2:
                return {
                    self._normalize_header(row[0]): row[1] if len(row) > 1 else None
                }
            return {}
    
    def _normalize_header(self, header: str) -> str:
        """Normalize table header text"""
        if not header:
            return ""
        
        # Remove special characters, normalize spaces
        normalized = re.sub(r'[^a-zA-Z0-9\s]', '', header)
        normalized = re.sub(r'\s+', '_', normalized.strip())
        return normalized.lower()


if __name__ == "__main__":
    # Example usage
    parser = NLPParser()
    
    test_text = "QTY: 4, Hex Bolt M8x25, Material: SS304, Standard: EN 10025, Date: 2024-01-15"
    
    result = parser.parse_text(test_text)
    
    print("Parsed Results:")
    print(f"Quantities: {result['quantities']}")
    print(f"Dimensions: {result['dimensions']}")
    print(f"Materials: {result['materials']}")
    print(f"Standards: {result['standards']}")
    print(f"Dates: {result['dates']}")





