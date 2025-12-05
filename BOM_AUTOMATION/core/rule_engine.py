#!/usr/bin/env python3
"""
Rule Engine Module
Ensures data correctness through validation and normalization rules
"""

import re
from typing import Dict, List, Optional, Tuple
from collections import defaultdict


class RuleEngine:
    """
    Rule Engine (Section 8)
    Rules ensure data correctness.
    Examples:
    - Symbols linked to matching OCR text via nearest-neighbor
    - Material normalization (SS304 → Stainless Steel 304)
    - Auto-unit inference (mm)
    """
    
    def __init__(self):
        self.material_mappings = self._load_material_mappings()
        self.unit_patterns = self._load_unit_patterns()
    
    def link_symbols_to_text(self, symbols: List[Dict], texts: List[Dict], 
                            max_distance: float = 500.0) -> List[Dict]:
        """
        Link symbols to matching OCR text via nearest-neighbor
        
        Args:
            symbols: List of symbol detections with bbox
            texts: List of text items with bbox
            max_distance: Maximum distance for linking
            
        Returns:
            List of relations {symbol_index, text_index, distance, score}
        """
        relations = []
        
        for i, symbol in enumerate(symbols):
            symbol_center = self._get_bbox_center(symbol.get('bbox', []))
            if symbol_center is None:
                continue
            
            best_match = None
            best_distance = float('inf')
            
            for j, text in enumerate(texts):
                text_center = self._get_bbox_center(text.get('bbox', []))
                if text_center is None:
                    continue
                
                distance = self._euclidean_distance(symbol_center, text_center)
                
                if distance < best_distance and distance <= max_distance:
                    best_distance = distance
                    best_match = j
            
            if best_match is not None:
                # Score based on distance (closer = higher score)
                score = max(0.0, 1.0 - (best_distance / max_distance))
                relations.append({
                    'symbol_index': i,
                    'text_index': best_match,
                    'distance': best_distance,
                    'score': score
                })
        
        return relations
    
    def normalize_material(self, material_text: str) -> Dict[str, str]:
        """
        Material normalization (SS304 → Stainless Steel 304)
        
        Args:
            material_text: Raw material text
            
        Returns:
            Dict with normalized name and properties
        """
        material_text = material_text.strip().upper()
        
        # Check direct mappings
        if material_text in self.material_mappings:
            return self.material_mappings[material_text]
        
        # Pattern-based matching
        normalized = self._normalize_by_pattern(material_text)
        if normalized:
            return normalized
        
        # Return original if no match
        return {
            'original': material_text,
            'normalized': material_text,
            'category': 'unknown',
            'standard': None
        }
    
    def infer_units(self, value_text: str, context: Optional[str] = None) -> Dict[str, str]:
        """
        Auto-unit inference (mm, inches, etc.)
        
        Args:
            value_text: Text containing value
            context: Optional context text
            
        Returns:
            Dict with value, unit, and confidence
        """
        # Check for explicit units in text
        for unit, patterns in self.unit_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, value_text, re.IGNORECASE)
                if match:
                    return {
                        'value': value_text,
                        'unit': unit,
                        'confidence': 1.0,
                        'method': 'explicit'
                    }
        
        # Infer from context
        if context:
            for unit, patterns in self.unit_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, context, re.IGNORECASE):
                        return {
                            'value': value_text,
                            'unit': unit,
                            'confidence': 0.7,
                            'method': 'context'
                        }
        
        # Default inference (common in CAD: mm)
        return {
            'value': value_text,
            'unit': 'mm',
            'confidence': 0.5,
            'method': 'default'
        }
    
    def validate_dimension(self, dimension_text: str) -> Dict[str, any]:
        """
        Validate and parse dimension (e.g., "M8", "Ø12.5", "100x50")
        
        Args:
            dimension_text: Dimension text
            
        Returns:
            Dict with parsed dimension data
        """
        # Pattern: M8, M10, etc. (metric threads)
        metric_thread = re.match(r'M(\d+(?:\.\d+)?)', dimension_text, re.IGNORECASE)
        if metric_thread:
            return {
                'type': 'metric_thread',
                'value': float(metric_thread.group(1)),
                'unit': 'mm',
                'valid': True
            }
        
        # Pattern: Ø12.5 (diameter)
        diameter = re.match(r'[ØØ](\d+(?:\.\d+)?)', dimension_text, re.IGNORECASE)
        if diameter:
            return {
                'type': 'diameter',
                'value': float(diameter.group(1)),
                'unit': 'mm',
                'valid': True
            }
        
        # Pattern: 100x50 (rectangular)
        rectangular = re.match(r'(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)', dimension_text)
        if rectangular:
            return {
                'type': 'rectangular',
                'width': float(rectangular.group(1)),
                'height': float(rectangular.group(2)),
                'unit': 'mm',
                'valid': True
            }
        
        # Pattern: Simple number
        number = re.match(r'(\d+(?:\.\d+)?)', dimension_text)
        if number:
            return {
                'type': 'numeric',
                'value': float(number.group(1)),
                'unit': 'mm',
                'valid': True
            }
        
        return {
            'type': 'unknown',
            'original': dimension_text,
            'valid': False
        }
    
    def extract_quantity(self, text: str) -> Optional[int]:
        """Extract quantity from text (QTY: 4, Quantity: 4, etc.)"""
        patterns = [
            r'QTY[:\s]+(\d+)',
            r'QUANTITY[:\s]+(\d+)',
            r'QTY\.?\s*[=:]?\s*(\d+)',
            r'(\d+)\s*(?:pcs|pieces|units)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        
        return None
    
    def _get_bbox_center(self, bbox: List) -> Optional[Tuple[float, float]]:
        """Get center point of bounding box"""
        if not bbox or len(bbox) < 4:
            return None
        x0, y0, x1, y1 = bbox[:4]
        return ((x0 + x1) / 2.0, (y0 + y1) / 2.0)
    
    def _euclidean_distance(self, p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        """Calculate Euclidean distance between two points"""
        return ((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2) ** 0.5
    
    def _load_material_mappings(self) -> Dict[str, Dict]:
        """Load material normalization mappings"""
        return {
            'SS304': {
                'original': 'SS304',
                'normalized': 'Stainless Steel 304',
                'category': 'stainless_steel',
                'standard': 'AISI 304'
            },
            'SS316': {
                'original': 'SS316',
                'normalized': 'Stainless Steel 316',
                'category': 'stainless_steel',
                'standard': 'AISI 316'
            },
            'MS': {
                'original': 'MS',
                'normalized': 'Mild Steel',
                'category': 'carbon_steel',
                'standard': None
            },
            'AL6061': {
                'original': 'AL6061',
                'normalized': 'Aluminum 6061',
                'category': 'aluminum',
                'standard': 'AA 6061'
            },
            'EN10025': {
                'original': 'EN10025',
                'normalized': 'European Standard EN 10025',
                'category': 'structural_steel',
                'standard': 'EN 10025'
            }
        }
    
    def _load_unit_patterns(self) -> Dict[str, List[str]]:
        """Load unit detection patterns"""
        return {
            'mm': [r'\d+\s*mm', r'\d+\.\d+\s*mm', r'MM', r'millimeter'],
            'cm': [r'\d+\s*cm', r'\d+\.\d+\s*cm', r'CM', r'centimeter'],
            'm': [r'\d+\s*m\b', r'\d+\.\d+\s*m\b', r'METER'],
            'inch': [r'\d+\s*in', r'\d+\.\d+\s*in', r'\d+"', r'INCH'],
            'ft': [r'\d+\s*ft', r'\d+\.\d+\s*ft', r'\d+\'', r'FOOT']
        }
    
    def _normalize_by_pattern(self, material_text: str) -> Optional[Dict]:
        """Normalize material by pattern matching"""
        # Pattern: SS followed by numbers
        ss_match = re.match(r'SS(\d+)', material_text)
        if ss_match:
            grade = ss_match.group(1)
            return {
                'original': material_text,
                'normalized': f'Stainless Steel {grade}',
                'category': 'stainless_steel',
                'standard': f'AISI {grade}'
            }
        
        # Pattern: AL followed by numbers
        al_match = re.match(r'AL(\d+)', material_text)
        if al_match:
            grade = al_match.group(1)
            return {
                'original': material_text,
                'normalized': f'Aluminum {grade}',
                'category': 'aluminum',
                'standard': f'AA {grade}'
            }
        
        return None


if __name__ == "__main__":
    # Example usage
    engine = RuleEngine()
    
    # Test material normalization
    print("Material Normalization:")
    print(engine.normalize_material("SS304"))
    print(engine.normalize_material("AL6061"))
    
    # Test unit inference
    print("\nUnit Inference:")
    print(engine.infer_units("12.5"))
    print(engine.infer_units("12.5 mm"))
    
    # Test dimension validation
    print("\nDimension Validation:")
    print(engine.validate_dimension("M8"))
    print(engine.validate_dimension("Ø12.5"))
    print(engine.validate_dimension("100x50"))





