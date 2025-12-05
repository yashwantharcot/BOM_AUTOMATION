#!/usr/bin/env python3
"""
Confidence Engine Module (Section 9)
Calculates confidence scores for each detection based on multiple factors
"""

from typing import Dict, List, Optional
import math


class ConfidenceEngine:
    """
    9. CONFIDENCE ENGINE
    
    Each detection gets a score based on:
    - Template match score
    - ORB feature inliers ratio
    - ML detector probability
    - OCR confidence
    - Vector vs raster source
    
    Low confidence → flagged for manual review.
    """
    
    def __init__(self):
        self.weights = {
            'template_match': 0.3,
            'feature_match': 0.25,
            'ml_detector': 0.3,
            'ocr_confidence': 0.1,
            'source_type': 0.05
        }
    
    def calculate_confidence(self, detection: Dict) -> float:
        """
        Calculate overall confidence score for a detection
        
        Args:
            detection: Detection dict with various confidence indicators
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        scores = []
        
        # Template match score
        if 'template_score' in detection:
            template_score = float(detection['template_score'])
            scores.append(('template_match', template_score, self.weights['template_match']))
        
        # Feature match score (ORB inliers ratio)
        if 'feature_inliers_ratio' in detection:
            feature_score = float(detection['feature_inliers_ratio'])
            scores.append(('feature_match', feature_score, self.weights['feature_match']))
        
        # ML detector probability
        if 'ml_confidence' in detection:
            ml_score = float(detection['ml_confidence'])
            scores.append(('ml_detector', ml_score, self.weights['ml_detector']))
        
        # OCR confidence
        if 'ocr_confidence' in detection:
            ocr_score = float(detection['ocr_confidence'])
            scores.append(('ocr_confidence', ocr_score, self.weights['ocr_confidence']))
        
        # Source type (vector = higher confidence)
        source_score = 1.0 if detection.get('source') == 'vector' else 0.7
        scores.append(('source_type', source_score, self.weights['source_type']))
        
        # Calculate weighted average
        if scores:
            total_weight = sum(w for _, _, w in scores)
            if total_weight > 0:
                confidence = sum(score * weight for _, score, weight in scores) / total_weight
            else:
                confidence = 0.5  # Default if no scores
        else:
            confidence = detection.get('score', 0.5)  # Fallback to base score
        
        # Normalize to [0, 1]
        confidence = max(0.0, min(1.0, confidence))
        
        return confidence
    
    def calculate_text_confidence(self, text_item: Dict) -> float:
        """
        Calculate confidence for text extraction
        
        Args:
            text_item: Text item with source and OCR confidence
            
        Returns:
            Confidence score
        """
        base_score = 0.5
        
        # Vector text = 100% confidence
        if text_item.get('source') == 'vector':
            return 1.0
        
        # OCR confidence
        if 'ocr_confidence' in text_item:
            base_score = float(text_item['ocr_confidence'])
        
        # Pattern matching bonus
        if text_item.get('parsed'):
            base_score += 0.1
        
        # Font size consistency
        if 'font_size' in text_item and text_item.get('font_size', 0) > 8:
            base_score += 0.05
        
        return min(1.0, base_score)
    
    def calculate_symbol_confidence(self, symbol_detection: Dict, 
                                   detection_method: str) -> float:
        """
        Calculate confidence for symbol detection based on method
        
        Args:
            symbol_detection: Symbol detection dict
            detection_method: 'template', 'feature', or 'ml'
            
        Returns:
            Confidence score
        """
        if detection_method == 'template':
            # Template matching confidence
            score = symbol_detection.get('score', 0.5)
            # Adjust based on scale and rotation
            if 'scale' in symbol_detection:
                scale = symbol_detection['scale']
                # Penalize extreme scales
                if scale < 0.5 or scale > 1.5:
                    score *= 0.9
            
            if 'rotation' in symbol_detection and symbol_detection['rotation'] != 0:
                score *= 0.95  # Slight penalty for rotated matches
            
            return min(1.0, score)
        
        elif detection_method == 'feature':
            # Feature matching confidence based on inliers
            inliers_ratio = symbol_detection.get('inliers_ratio', 0.5)
            matches_count = symbol_detection.get('matches_count', 0)
            
            # More matches = higher confidence
            match_bonus = min(0.2, matches_count / 50.0)
            confidence = inliers_ratio + match_bonus
            
            return min(1.0, confidence)
        
        elif detection_method == 'ml':
            # ML detector confidence
            return float(symbol_detection.get('confidence', 0.5))
        
        return 0.5
    
    def calculate_table_confidence(self, table_data: Dict) -> float:
        """
        Calculate confidence for table extraction
        
        Args:
            table_data: Table extraction data
            
        Returns:
            Confidence score
        """
        confidence = 0.5
        
        # Grid structure detected
        if table_data.get('has_grid'):
            confidence += 0.2
        
        # Cell count
        cell_count = table_data.get('cell_count', 0)
        if cell_count > 0:
            confidence += min(0.2, cell_count / 100.0)
        
        # Text extraction success rate
        text_success_rate = table_data.get('text_success_rate', 0.5)
        confidence += text_success_rate * 0.1
        
        return min(1.0, confidence)
    
    def classify_confidence(self, confidence: float) -> str:
        """
        Classify confidence level
        
        Returns:
            'high', 'medium', or 'low'
        """
        if confidence >= 0.8:
            return 'high'
        elif confidence >= 0.5:
            return 'medium'
        else:
            return 'low'
    
    def should_review(self, confidence: float, threshold: float = 0.5) -> bool:
        """
        Determine if detection should be flagged for manual review
        
        Args:
            confidence: Confidence score
            threshold: Review threshold
            
        Returns:
            True if should be reviewed
        """
        return confidence < threshold
    
    def calculate_aggregate_confidence(self, detections: List[Dict]) -> Dict:
        """
        Calculate aggregate confidence statistics
        
        Args:
            detections: List of detections
            
        Returns:
            Dict with statistics
        """
        if not detections:
            return {
                'mean': 0.0,
                'median': 0.0,
                'min': 0.0,
                'max': 0.0,
                'high_count': 0,
                'medium_count': 0,
                'low_count': 0
            }
        
        confidences = [self.calculate_confidence(d) for d in detections]
        confidences.sort()
        
        high = sum(1 for c in confidences if c >= 0.8)
        medium = sum(1 for c in confidences if 0.5 <= c < 0.8)
        low = sum(1 for c in confidences if c < 0.5)
        
        return {
            'mean': sum(confidences) / len(confidences),
            'median': confidences[len(confidences) // 2],
            'min': min(confidences),
            'max': max(confidences),
            'high_count': high,
            'medium_count': medium,
            'low_count': low,
            'total': len(confidences)
        }


if __name__ == "__main__":
    # Example usage
    engine = ConfidenceEngine()
    
    # Test symbol detection confidence
    symbol_detection = {
        'template_score': 0.85,
        'source': 'vector',
        'score': 0.85
    }
    conf = engine.calculate_confidence(symbol_detection)
    print(f"Symbol confidence: {conf:.2f} ({engine.classify_confidence(conf)})")
    
    # Test text confidence
    text_item = {
        'source': 'ocr',
        'ocr_confidence': 0.75,
        'parsed': True
    }
    text_conf = engine.calculate_text_confidence(text_item)
    print(f"Text confidence: {text_conf:.2f} ({engine.classify_confidence(text_conf)})")





