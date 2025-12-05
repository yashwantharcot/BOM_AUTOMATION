#!/usr/bin/env python3
"""
Preprocessing Module for CAD Drawing BOM Automation
Handles both vector PDF processing and raster preprocessing
"""

import sys
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import numpy as np

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    cv2 = None
    HAS_CV2 = False
    print("[WARN] OpenCV not available, raster preprocessing disabled")

try:
    import pymupdf as fitz
    HAS_PYMUPDF = True
except ImportError:
    fitz = None
    HAS_PYMUPDF = False
    print("[WARN] PyMuPDF not available, vector extraction disabled")

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    Image = None
    HAS_PIL = False


class VectorPDFProcessor:
    """
    4.1 Vector PDF Processing
    Extracts primitive geometry, text content with font + coordinates,
    block references, and line drawings for table borders.
    """
    
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        if not HAS_PYMUPDF:
            raise ImportError("PyMuPDF required for vector processing")
        self.doc = fitz.open(pdf_path)
    
    def extract_primitive_geometry(self, page_num: int) -> List[Dict]:
        """Extract primitive geometry (lines, circles, rectangles)"""
        if page_num >= len(self.doc):
            return []
        
        page = self.doc[page_num]
        geometry = []
        
        # Extract drawings (lines, curves, etc.)
        drawings = page.get_drawings()
        for draw in drawings:
            geom_item = {
                'type': draw.get('type', 'unknown'),
                'rect': draw.get('rect', []),
                'color': draw.get('color', []),
                'width': draw.get('width', 1.0),
                'fill': draw.get('fill', None)
            }
            geometry.append(geom_item)
        
        return geometry
    
    def extract_text_with_metadata(self, page_num: int) -> List[Dict]:
        """
        Extract text content with font + coordinates.
        Vector extraction yields 100% accuracy for text & shapes.
        """
        if page_num >= len(self.doc):
            return []
        
        page = self.doc[page_num]
        text_items = []
        
        # Get text blocks with detailed metadata
        blocks = page.get_text("dict").get("blocks", [])
        
        for block in blocks:
            if block.get("type") != 0:  # Skip non-text blocks
                continue
            
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text_item = {
                        'text': span.get("text", "").strip(),
                        'bbox': span.get("bbox", []),
                        'font': span.get("font", ""),
                        'font_size': span.get("size", 0),
                        'flags': span.get("flags", 0),  # Bold, italic, etc.
                        'color': span.get("color", 0),
                        'layer_info': self._get_layer_info(page, span.get("bbox", []))
                    }
                    if text_item['text']:
                        text_items.append(text_item)
        
        return text_items
    
    def extract_block_references(self, page_num: int) -> List[Dict]:
        """Extract block references (reusable symbols/groups)"""
        if page_num >= len(self.doc):
            return []
        
        page = self.doc[page_num]
        blocks = []
        
        # Extract images (often used as block references)
        image_list = page.get_images()
        for img_index, img in enumerate(image_list):
            block_ref = {
                'index': img_index,
                'xref': img[0],
                'bbox': page.get_image_bbox(img),
                'type': 'image_reference'
            }
            blocks.append(block_ref)
        
        return blocks
    
    def extract_table_borders(self, page_num: int) -> List[Dict]:
        """Extract line drawings for table borders"""
        if page_num >= len(self.doc):
            return []
        
        page = self.doc[page_num]
        borders = []
        
        # Extract horizontal and vertical lines
        drawings = page.get_drawings()
        
        for draw in drawings:
            if draw.get('type') == 'l':  # Line
                rect = draw.get('rect', [])
                if len(rect) == 4:
                    x0, y0, x1, y1 = rect
                    
                    # Classify as horizontal or vertical
                    if abs(y1 - y0) < 2:  # Horizontal line
                        borders.append({
                            'type': 'horizontal',
                            'y': (y0 + y1) / 2,
                            'x0': min(x0, x1),
                            'x1': max(x0, x1),
                            'bbox': rect
                        })
                    elif abs(x1 - x0) < 2:  # Vertical line
                        borders.append({
                            'type': 'vertical',
                            'x': (x0 + x1) / 2,
                            'y0': min(y0, y1),
                            'y1': max(y0, y1),
                            'bbox': rect
                        })
        
        return borders
    
    def _get_layer_info(self, page, bbox: List) -> Dict:
        """Get layer information for a bbox"""
        # PyMuPDF doesn't directly expose layers, but we can infer from properties
        return {
            'has_vector': True,
            'has_raster': False
        }
    
    def close(self):
        """Close the PDF document"""
        if self.doc:
            self.doc.close()


class RasterPreprocessor:
    """
    4.2 Raster Preprocessing (for scanned PDFs)
    Performed using OpenCV for high-quality preprocessing
    """
    
    def __init__(self):
        if not HAS_CV2:
            raise ImportError("OpenCV required for raster preprocessing")
    
    def preprocess(self, image: np.ndarray) -> np.ndarray:
        """
        Complete preprocessing pipeline:
        1. Grayscale conversion
        2. Denoising (Gaussian / bilateral)
        3. Adaptive threshold
        4. Deskewing (Hough line)
        5. Morphological closing (remove small artifacts)
        """
        # Step 1: Grayscale conversion
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Step 2: Denoising
        denoised = self._denoise(gray)
        
        # Step 3: Adaptive threshold
        thresholded = self._adaptive_threshold(denoised)
        
        # Step 4: Deskewing
        deskewed = self._deskew(thresholded)
        
        # Step 5: Morphological closing
        cleaned = self._morphological_closing(deskewed)
        
        return cleaned
    
    def _denoise(self, image: np.ndarray) -> np.ndarray:
        """Denoising using Gaussian and bilateral filters"""
        # Gaussian blur for general noise reduction
        gaussian = cv2.GaussianBlur(image, (3, 3), 0)
        
        # Bilateral filter to preserve edges while reducing noise
        bilateral = cv2.bilateralFilter(gaussian, 9, 75, 75)
        
        return bilateral
    
    def _adaptive_threshold(self, image: np.ndarray) -> np.ndarray:
        """Adaptive thresholding for varying lighting conditions"""
        # Use adaptive threshold instead of global threshold
        thresholded = cv2.adaptiveThreshold(
            image, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11, 2
        )
        return thresholded
    
    def _deskew(self, image: np.ndarray) -> np.ndarray:
        """Deskewing using Hough line transform"""
        # Detect lines using Hough transform
        edges = cv2.Canny(image, 50, 150, apertureSize=3)
        lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)
        
        if lines is None or len(lines) == 0:
            return image
        
        # Calculate average angle
        angles = []
        for line in lines:
            rho, theta = line[0]
            angle = (theta * 180 / np.pi) - 90
            angles.append(angle)
        
        if not angles:
            return image
        
        # Get median angle (more robust than mean)
        median_angle = np.median(angles)
        
        # Only correct if angle is significant
        if abs(median_angle) < 0.5:
            return image
        
        # Rotate image to correct skew
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
        rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC,
                                borderMode=cv2.BORDER_REPLICATE)
        
        return rotated
    
    def _morphological_closing(self, image: np.ndarray) -> np.ndarray:
        """Morphological closing to remove small artifacts"""
        # Create kernel for closing operation
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        
        # Apply closing (dilation followed by erosion)
        closed = cv2.morphologyEx(image, cv2.MORPH_CLOSE, kernel)
        
        return closed
    
    def preprocess_for_symbol_detection(self, image: np.ndarray) -> np.ndarray:
        """Optimized preprocessing specifically for symbol detection"""
        # For symbol detection, we want to preserve fine details
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Light denoising (preserve edges)
        denoised = cv2.bilateralFilter(gray, 5, 50, 50)
        
        # Use Otsu's threshold for better symbol contrast
        _, thresholded = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return thresholded


class PreprocessingPipeline:
    """Main preprocessing pipeline that handles both vector and raster"""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.vector_processor = None
        self.raster_preprocessor = None
        
        if HAS_PYMUPDF:
            try:
                self.vector_processor = VectorPDFProcessor(pdf_path)
            except Exception as e:
                print(f"[WARN] Vector processing unavailable: {e}")
        
        if HAS_CV2:
            self.raster_preprocessor = RasterPreprocessor()
    
    def process_page(self, page_num: int, dpi: int = 300) -> Dict:
        """
        Process a single page, extracting both vector and raster data
        """
        result = {
            'page': page_num,
            'vector_data': {},
            'raster_data': None,
            'is_vector': False
        }
        
        # Try vector extraction first
        if self.vector_processor:
            try:
                result['vector_data'] = {
                    'text': self.vector_processor.extract_text_with_metadata(page_num),
                    'geometry': self.vector_processor.extract_primitive_geometry(page_num),
                    'block_references': self.vector_processor.extract_block_references(page_num),
                    'table_borders': self.vector_processor.extract_table_borders(page_num)
                }
                
                # Check if page has vector content
                if result['vector_data']['text']:
                    result['is_vector'] = True
            except Exception as e:
                print(f"[WARN] Vector extraction failed: {e}")
        
        # If no vector content, prepare raster
        if not result['is_vector'] and self.raster_preprocessor:
            try:
                # Convert PDF page to image
                if HAS_PYMUPDF:
                    doc = fitz.open(self.pdf_path)
                    page = doc[page_num]
                    pix = page.get_pixmap(matrix=fitz.Matrix(dpi/72, dpi/72))
                    img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                        pix.height, pix.width, pix.n
                    )
                    doc.close()
                    
                    # Preprocess raster image
                    preprocessed = self.raster_preprocessor.preprocess(img_array)
                    result['raster_data'] = preprocessed
            except Exception as e:
                print(f"[WARN] Raster preprocessing failed: {e}")
        
        return result
    
    def close(self):
        """Clean up resources"""
        if self.vector_processor:
            self.vector_processor.close()


if __name__ == "__main__":
    # Example usage
    if len(sys.argv) < 2:
        print("Usage: python preprocessing.py <pdf_path>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    pipeline = PreprocessingPipeline(pdf_path)
    
    # Process first page
    result = pipeline.process_page(0)
    print(f"Page 0 - Vector: {result['is_vector']}")
    print(f"  Text items: {len(result['vector_data'].get('text', []))}")
    print(f"  Geometry items: {len(result['vector_data'].get('geometry', []))}")
    
    pipeline.close()





