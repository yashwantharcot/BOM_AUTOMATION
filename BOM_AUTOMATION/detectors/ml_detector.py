#!/usr/bin/env python3
"""
Machine Learning Object Detector (Layer 3)
Uses YOLO/Detectron2 for highly varied or complex symbols
"""

import sys
from typing import List, Dict, Optional
import numpy as np

try:
    import torch
    HAS_TORCH = True
except ImportError:
    torch = None
    HAS_TORCH = False

try:
    from ultralytics import YOLO
    HAS_YOLO = True
except ImportError:
    YOLO = None
    HAS_YOLO = False

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    cv2 = None
    HAS_CV2 = False


class MLSymbolDetector:
    """
    5.4 Detection Layer 3 — Machine Learning Object Detector (YOLO/Detectron2)
    
    Used for highly varied or complex symbols.
    Workflow:
    1. User labels 200–1000 symbol instances
    2. Train YOLOv5/YOLOv8 model
    3. Save weights in model storage
    4. Perform inference on uploaded pages
    """
    
    def __init__(self, model_path: Optional[str] = None, model_type: str = "yolo"):
        """
        Initialize ML detector
        
        Args:
            model_path: Path to trained model weights
            model_type: "yolo" or "detectron2"
        """
        self.model_path = model_path
        self.model_type = model_type
        self.model = None
        
        if model_path and HAS_YOLO:
            try:
                self.model = YOLO(model_path)
                print(f"[OK] Loaded YOLO model from {model_path}")
            except Exception as e:
                print(f"[WARN] Failed to load YOLO model: {e}")
                self.model = None
    
    def detect(self, image: np.ndarray, conf_threshold: float = 0.25) -> List[Dict]:
        """
        Perform inference on image
        
        Args:
            image: Input image (numpy array)
            conf_threshold: Confidence threshold
            
        Returns:
            List of detections with bbox and score
        """
        if self.model is None:
            return []
        
        if not HAS_CV2:
            return []
        
        detections = []
        
        try:
            if self.model_type == "yolo" and HAS_YOLO:
                # YOLO inference
                results = self.model(image, conf=conf_threshold, verbose=False)
                
                for result in results:
                    boxes = result.boxes
                    if boxes is not None:
                        for box in boxes:
                            # Get bounding box coordinates
                            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                            confidence = float(box.conf[0].cpu().numpy())
                            class_id = int(box.cls[0].cpu().numpy())
                            
                            detections.append({
                                'bbox': [float(x1), float(y1), float(x2), float(y2)],
                                'score': confidence,
                                'class_id': class_id,
                                'class_name': self.model.names[class_id] if hasattr(self.model, 'names') else str(class_id)
                            })
            
        except Exception as e:
            print(f"[ERROR] ML detection failed: {e}")
        
        return detections
    
    def is_available(self) -> bool:
        """Check if ML detector is available"""
        return self.model is not None and HAS_YOLO
    
    @staticmethod
    def train_yolo_model(data_path: str, epochs: int = 100, imgsz: int = 640):
        """
        Train YOLO model (requires labeled dataset)
        
        Args:
            data_path: Path to YOLO dataset (yaml file)
            epochs: Number of training epochs
            imgsz: Image size for training
        """
        if not HAS_YOLO:
            print("[ERROR] YOLO not installed. Install with: pip install ultralytics")
            return None
        
        try:
            # Load YOLO model (YOLOv8 by default)
            model = YOLO('yolov8n.pt')  # nano model for faster training
            
            # Train the model
            results = model.train(
                data=data_path,
                epochs=epochs,
                imgsz=imgsz,
                batch=16,
                name='symbol_detector'
            )
            
            print(f"[OK] Training complete. Model saved to: {results.save_dir}")
            return results.save_dir
            
        except Exception as e:
            print(f"[ERROR] Training failed: {e}")
            return None


class MLDetectorManager:
    """Manager for multiple ML models"""
    
    def __init__(self, models_config: Dict[str, str]):
        """
        Initialize with multiple model configurations
        
        Args:
            models_config: Dict mapping symbol names to model paths
                Example: {"weld_symbol": "models/weld_yolo.pt", ...}
        """
        self.models = {}
        
        for symbol_name, model_path in models_config.items():
            try:
                detector = MLSymbolDetector(model_path)
                if detector.is_available():
                    self.models[symbol_name] = detector
                    print(f"[OK] Loaded ML model for: {symbol_name}")
            except Exception as e:
                print(f"[WARN] Failed to load model for {symbol_name}: {e}")
    
    def detect_all(self, image: np.ndarray, symbol_names: Optional[List[str]] = None) -> Dict[str, List[Dict]]:
        """
        Run detection for all or specified symbols
        
        Args:
            image: Input image
            symbol_names: List of symbol names to detect (None = all)
            
        Returns:
            Dict mapping symbol names to detections
        """
        results = {}
        
        symbols_to_detect = symbol_names if symbol_names else list(self.models.keys())
        
        for symbol_name in symbols_to_detect:
            if symbol_name in self.models:
                detections = self.models[symbol_name].detect(image)
                if detections:
                    results[symbol_name] = detections
        
        return results


if __name__ == "__main__":
    # Example usage
    print("ML Symbol Detector Module")
    print("=" * 50)
    
    # Check availability
    print(f"PyTorch available: {HAS_TORCH}")
    print(f"YOLO available: {HAS_YOLO}")
    print(f"OpenCV available: {HAS_CV2}")
    
    # Example: Initialize detector
    if len(sys.argv) > 1:
        model_path = sys.argv[1]
        detector = MLSymbolDetector(model_path)
        print(f"Detector initialized: {detector.is_available()}")





