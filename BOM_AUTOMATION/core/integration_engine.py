#!/usr/bin/env python3
"""
Integration Engine - Main pipeline that integrates all modules
Combines preprocessing, detection, extraction, parsing, and confidence scoring
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional
import json

# Import all modules
from .preprocessing import PreprocessingPipeline
from .nlp_parser import NLPParser
from .rule_engine import RuleEngine
from .confidence_engine import ConfidenceEngine
from detectors.template_matcher import match_template
from detectors.feature_matcher import feature_match
from detectors.ml_detector import MLSymbolDetector, MLDetectorManager


class IntegrationEngine:
    """
    Main integration engine that combines all modules
    Implements the complete pipeline from PDF to structured data
    """
    
    def __init__(self, pdf_path: str, ml_models_config: Optional[Dict] = None):
        """
        Initialize integration engine
        
        Args:
            pdf_path: Path to PDF file
            ml_models_config: Optional dict mapping symbol names to ML model paths
        """
        self.pdf_path = pdf_path
        self.preprocessor = PreprocessingPipeline(pdf_path)
        self.nlp_parser = NLPParser()
        self.rule_engine = RuleEngine()
        self.confidence_engine = ConfidenceEngine()
        
        # Initialize ML detector if models provided
        self.ml_detector = None
        if ml_models_config:
            self.ml_detector = MLDetectorManager(ml_models_config)
        
        self.results = {
            'upload_id': None,
            'filename': Path(pdf_path).name,
            'pages': [],
            'symbols': {},
            'tables': [],
            'text_entries': [],
            'parsed_values': [],
            'confidence_report': {}
        }
    
    def process_page(self, page_num: int, symbol_templates: Dict) -> Dict:
        """
        Process a single page through the complete pipeline
        
        Args:
            page_num: Page number (0-indexed)
            symbol_templates: Dict mapping symbol names to template images
            
        Returns:
            Processed page data
        """
        print(f"\nProcessing page {page_num + 1}...")
        
        page_result = {
            'page': page_num,
            'symbols': {},
            'text_entries': [],
            'tables': [],
            'parsed_values': [],
            'associations': []
        }
        
        # Step 1: Preprocessing
        print("  [1/6] Preprocessing...")
        preprocessed = self.preprocessor.process_page(page_num)
        
        # Step 2: Symbol Detection (3-layer approach)
        print("  [2/6] Symbol detection...")
        page_result['symbols'] = self._detect_symbols(
            preprocessed, symbol_templates, page_num
        )
        
        # Step 3: Text Extraction
        print("  [3/6] Text extraction...")
        page_result['text_entries'] = self._extract_text(preprocessed, page_num)
        
        # Step 4: Table Extraction
        print("  [4/6] Table extraction...")
        page_result['tables'] = self._extract_tables(preprocessed, page_num)
        
        # Step 5: NLP Parsing
        print("  [5/6] NLP parsing...")
        page_result['parsed_values'] = self._parse_text(page_result['text_entries'])
        
        # Step 6: Rule Engine & Associations
        print("  [6/6] Rule engine & associations...")
        page_result['associations'] = self.rule_engine.link_symbols_to_text(
            list(page_result['symbols'].values()),
            page_result['text_entries']
        )
        
        # Calculate confidence scores
        page_result['confidence_report'] = self._calculate_confidence(page_result)
        
        return page_result
    
    def _detect_symbols(self, preprocessed: Dict, symbol_templates: Dict, 
                       page_num: int) -> Dict:
        """Detect symbols using 3-layer approach"""
        detections = {}
        
        # Get image for detection
        image = None
        if preprocessed.get('raster_data') is not None:
            image = preprocessed['raster_data']
        elif preprocessed.get('is_vector'):
            # Convert vector page to image
            import pymupdf as fitz
            doc = fitz.open(self.pdf_path)
            page = doc[page_num]
            pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))
            import numpy as np
            image = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.height, pix.width, pix.n
            )
            doc.close()
        
        if image is None:
            return detections
        
        # Convert to grayscale if needed
        import cv2
        if len(image.shape) == 3:
            image_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            image_gray = image
        
        for symbol_name, template_image in symbol_templates.items():
            symbol_detections = []
            
            # Layer 1: Template Matching
            template_detections = match_template(
                image_gray, template_image,
                scales=[0.5, 0.75, 1.0, 1.25, 1.5],
                rotations=[0, 90, 180, 270],
                thresh=0.75
            )
            
            for det in template_detections:
                det['method'] = 'template'
                det['template_score'] = det['score']
                symbol_detections.append(det)
            
            # Layer 2: Feature Matching (if template fails or for rotated symbols)
            if len(template_detections) == 0 or symbol_templates.get(f'{symbol_name}_allow_rotation'):
                feature_result = feature_match(image_gray, template_image)
                if feature_result:
                    feature_result['method'] = 'feature'
                    feature_result['feature_inliers_ratio'] = 0.8  # Placeholder
                    symbol_detections.append(feature_result)
            
            # Layer 3: ML Detection (if available)
            if self.ml_detector and symbol_name in self.ml_detector.models:
                ml_detections = self.ml_detector.models[symbol_name].detect(image)
                for det in ml_detections:
                    det['method'] = 'ml'
                    det['ml_confidence'] = det['score']
                    symbol_detections.append(det)
            
            # Apply Non-Maximum Suppression
            if symbol_detections:
                from core.symbol_detector import SymbolDetector
                boxes = [d['bbox'] for d in symbol_detections]
                scores = [d['score'] for d in symbol_detections]
                keep_idx = SymbolDetector.non_max_suppression(boxes, scores)
                
                final_detections = [symbol_detections[i] for i in keep_idx]
                detections[symbol_name] = {
                    'count': len(final_detections),
                    'detections': final_detections
                }
        
        return detections
    
    def _extract_text(self, preprocessed: Dict, page_num: int) -> List[Dict]:
        """Extract text from preprocessed data"""
        text_entries = []
        
        # Vector text
        vector_texts = preprocessed.get('vector_data', {}).get('text', [])
        for text_item in vector_texts:
            text_entry = {
                'text': text_item.get('text', ''),
                'bbox': text_item.get('bbox', []),
                'source': 'vector',
                'font': text_item.get('font', ''),
                'font_size': text_item.get('font_size', 0),
                'confidence': 1.0  # Vector text is 100% accurate
            }
            text_entries.append(text_entry)
        
        # OCR text (if no vector or as supplement)
        # This would be implemented using OCR engine
        # For now, we'll use vector text only
        
        return text_entries
    
    def _extract_tables(self, preprocessed: Dict, page_num: int) -> List[Dict]:
        """Extract tables from preprocessed data"""
        tables = []
        
        # Extract table borders from vector data
        borders = preprocessed.get('vector_data', {}).get('table_borders', [])
        
        if borders:
            # Group borders into tables
            horizontal_borders = [b for b in borders if b['type'] == 'horizontal']
            vertical_borders = [b for b in borders if b['type'] == 'vertical']
            
            if horizontal_borders and vertical_borders:
                table = {
                    'page': page_num,
                    'horizontal_lines': len(horizontal_borders),
                    'vertical_lines': len(vertical_borders),
                    'cells': []  # Would be populated by table extraction
                }
                tables.append(table)
        
        return tables
    
    def _parse_text(self, text_entries: List[Dict]) -> List[Dict]:
        """Parse text using NLP parser"""
        parsed_values = []
        
        for text_entry in text_entries:
            text = text_entry.get('text', '')
            if not text:
                continue
            
            parsed = self.nlp_parser.parse_text(text)
            
            # Add parsed values
            for qty in parsed['quantities']:
                parsed_values.append({
                    'type': 'quantity',
                    'value': qty['value'],
                    'text': qty['text'],
                    'text_entry_id': text_entry.get('id')
                })
            
            for dim in parsed['dimensions']:
                parsed_values.append({
                    'type': 'dimension',
                    'value': dim,
                    'text': dim['text'],
                    'text_entry_id': text_entry.get('id')
                })
            
            for mat in parsed['materials']:
                parsed_values.append({
                    'type': 'material',
                    'value': mat,
                    'text': mat['text'],
                    'text_entry_id': text_entry.get('id')
                })
        
        return parsed_values
    
    def _calculate_confidence(self, page_result: Dict) -> Dict:
        """Calculate confidence report for page"""
        all_detections = []
        
        # Collect all detections
        for symbol_data in page_result['symbols'].values():
            all_detections.extend(symbol_data.get('detections', []))
        
        # Calculate aggregate confidence
        aggregate = self.confidence_engine.calculate_aggregate_confidence(all_detections)
        
        return {
            'aggregate': aggregate,
            'high_confidence_count': aggregate['high_count'],
            'medium_confidence_count': aggregate['medium_count'],
            'low_confidence_count': aggregate['low_count'],
            'review_required': aggregate['low_count'] > 0
        }
    
    def process_all_pages(self, symbol_templates: Dict) -> Dict:
        """Process all pages in PDF"""
        import pymupdf as fitz
        doc = fitz.open(self.pdf_path)
        total_pages = doc.page_count
        doc.close()
        
        print(f"\nProcessing {total_pages} page(s)...")
        
        for page_num in range(total_pages):
            page_result = self.process_page(page_num, symbol_templates)
            self.results['pages'].append(page_result)
        
        # Aggregate results
        self._aggregate_results()
        
        return self.results
    
    def _aggregate_results(self):
        """Aggregate results across all pages"""
        # Aggregate symbol counts
        symbol_counts = {}
        for page_result in self.results['pages']:
            for symbol_name, symbol_data in page_result['symbols'].items():
                if symbol_name not in symbol_counts:
                    symbol_counts[symbol_name] = 0
                symbol_counts[symbol_name] += symbol_data.get('count', 0)
        
        self.results['symbols'] = symbol_counts
        
        # Aggregate text entries
        all_text_entries = []
        for page_result in self.results['pages']:
            all_text_entries.extend(page_result.get('text_entries', []))
        self.results['text_entries'] = all_text_entries
        
        # Aggregate tables
        all_tables = []
        for page_result in self.results['pages']:
            all_tables.extend(page_result.get('tables', []))
        self.results['tables'] = all_tables
    
    def close(self):
        """Clean up resources"""
        if self.preprocessor:
            self.preprocessor.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python integration_engine.py <pdf_path>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    engine = IntegrationEngine(pdf_path)
    
    # Example: Process with sample templates
    symbol_templates = {}  # Would load from database
    
    results = engine.process_all_pages(symbol_templates)
    
    print("\nResults:")
    print(f"Symbols detected: {results['symbols']}")
    print(f"Text entries: {len(results['text_entries'])}")
    print(f"Tables: {len(results['tables'])}")
    
    engine.close()





