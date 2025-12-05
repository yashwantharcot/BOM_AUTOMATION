#!/usr/bin/env python3
"""
Symbol Detection & Counting System
Store symbol templates in MongoDB
Detect and count symbols in uploaded PDFs
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Import dependencies with auto-install
def ensure_imports():
    """Ensure all required packages are installed"""
    try:
        import pymupdf as fitz
        from pymongo import MongoClient
        from PIL import Image
        import numpy as np
        return fitz, MongoClient, Image, np
    except ImportError as e:
        print(f"[*] Installing missing dependencies...")
        import subprocess
        packages = ["pymupdf", "pymongo", "python-dotenv", "pillow", "numpy"]
        for pkg in packages:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", pkg])
                print(f"  [OK] {pkg}")
            except:
                print(f"  [WARN] {pkg} install failed, continuing...")
        
        import pymupdf as fitz
        from pymongo import MongoClient
        from PIL import Image
        import numpy as np
        return fitz, MongoClient, Image, np

fitz, MongoClient, Image, np = ensure_imports()

# Try to import cv2, use Pillow as fallback
try:
    import cv2
    HAS_CV2 = True
except:
    print("[WARN] OpenCV not available, using Pillow for image processing")
    cv2 = None
    HAS_CV2 = False

load_dotenv()


class SymbolTemplate:
    """Manage symbol templates"""
    
    def __init__(self, db_name="utkarshproduction", collection_name="SYMBOL_TEMPLATES"):
        mongo_uri = os.getenv("MONGO_URI")
        if not mongo_uri:
            raise ValueError("[ERROR] MONGO_URI not set in .env")
        
        self.client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]
        self.client.admin.command('ping')
    
    def upload_symbol(self, symbol_name, image_path, metadata=None):
        """Upload symbol template image to MongoDB"""
        try:
            if not Path(image_path).exists():
                print(f"[ERROR] File not found: {image_path}")
                return None
            
            # Read image
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            # Create document
            doc = {
                'symbol_name': symbol_name,
                'image_data': image_data,
                'image_filename': Path(image_path).name,
                'file_size': len(image_data),
                'metadata': metadata or {},
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            # Check if exists and update or insert
            existing = self.collection.find_one({'symbol_name': symbol_name})
            if existing:
                result = self.collection.update_one(
                    {'symbol_name': symbol_name},
                    {'$set': doc}
                )
                print(f"[OK] Updated symbol: {symbol_name}")
                return existing['_id']
            else:
                result = self.collection.insert_one(doc)
                print(f"[OK] Uploaded symbol: {symbol_name}")
                return result.inserted_id
        
        except Exception as e:
            print(f"[ERROR] Upload failed: {e}")
            return None
    
    def get_symbol(self, symbol_name):
        """Get symbol template from MongoDB"""
        try:
            doc = self.collection.find_one({'symbol_name': symbol_name})
            if doc:
                image_data = doc['image_data']
                nparr = np.frombuffer(image_data, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                return img
            return None
        except Exception as e:
            print(f"[ERROR] Get symbol failed: {e}")
            return None
    
    def list_symbols(self):
        """List all stored symbols"""
        try:
            docs = list(self.collection.find({}, {'image_data': 0}))
            return docs
        except Exception as e:
            print(f"[ERROR] List failed: {e}")
            return []
    
    def delete_symbol(self, symbol_name):
        """Delete symbol template"""
        try:
            result = self.collection.delete_one({'symbol_name': symbol_name})
            if result.deleted_count > 0:
                print(f"[OK] Deleted symbol: {symbol_name}")
                return True
            else:
                print(f"[WARN] Symbol not found: {symbol_name}")
                return False
        except Exception as e:
            print(f"[ERROR] Delete failed: {e}")
            return False
    
    def close(self):
        self.client.close()


class SymbolDetector:
    """Detect and count symbols in PDF pages"""
    
    @staticmethod
    def rasterize_pdf_page(pdf_path, page_idx=0, dpi=300):
        """Rasterize PDF page to image"""
        try:
            doc = fitz.open(pdf_path)
            if page_idx >= len(doc):
                print(f"[ERROR] Page {page_idx} not found")
                return None
            
            page = doc[page_idx]
            zoom = dpi / 72.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            
            mode = "RGB" if pix.n < 4 else "RGBA"
            img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
            
            return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        except Exception as e:
            print(f"[ERROR] Rasterize failed: {e}")
            return None
    
    @staticmethod
    def preprocess_image(img):
        """Preprocess image for template matching"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Denoise
        denoised = cv2.fastNlMeansDenoising(gray, h=10)
        return denoised
    
    @staticmethod
    def non_max_suppression(boxes, scores, iou_thresh=0.25):
        """Non-maximum suppression to remove duplicate detections"""
        if len(boxes) == 0:
            return []
        
        boxes = np.array(boxes, dtype=np.float32)
        scores = np.array(scores, dtype=np.float32)
        
        x1 = boxes[:, 0]
        y1 = boxes[:, 1]
        x2 = boxes[:, 2]
        y2 = boxes[:, 3]
        
        areas = (x2 - x1 + 1) * (y2 - y1 + 1)
        order = scores.argsort()[::-1]
        
        keep = []
        while order.size > 0:
            i = order[0]
            keep.append(i)
            
            if order.size == 1:
                break
            
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])
            
            w = np.maximum(0.0, xx2 - xx1 + 1)
            h = np.maximum(0.0, yy2 - yy1 + 1)
            
            inter = w * h
            ovr = inter / (areas[i] + areas[order[1:]] - inter + 1e-6)
            
            inds = np.where(ovr <= iou_thresh)[0]
            order = order[inds + 1]
        
        return keep
    
    @staticmethod
    def multi_scale_template_match(image, template, scales=(0.5, 0.75, 1.0, 1.25, 1.5), 
                                   match_thresh=0.75, method=None):
        """Multi-scale template matching"""
        if not HAS_CV2:
            print("[WARN] CV2 not available, returning empty detections")
            return []
        
        # If method not specified, use default
        if method is None:
            method = cv2.TM_CCOEFF_NORMED
        
        hT, wT = template.shape[:2]
        detections = []
        
        gray_image = SymbolDetector.preprocess_image(image) if len(image.shape) == 3 else image
        gray_template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY) if len(template.shape) == 3 else template
        
        for s in scales:
            new_w = int(wT * s)
            new_h = int(hT * s)
            
            if new_w < 5 or new_h < 5:
                continue
            
            if new_w > gray_image.shape[1] or new_h > gray_image.shape[0]:
                continue
            
            resized = cv2.resize(gray_template, (new_w, new_h), interpolation=cv2.INTER_AREA)
            
            try:
                res = cv2.matchTemplate(gray_image, resized, method)
                loc = np.where(res >= match_thresh)
                
                for pt in zip(*loc[::-1]):
                    score = float(res[pt[1], pt[0]])
                    x1, y1 = pt[0], pt[1]
                    x2, y2 = x1 + new_w, y1 + new_h
                    detections.append(((x1, y1, x2, y2), score))
            except Exception as e:
                continue
        
        # Apply NMS
        if not detections:
            return []
        
        boxes = [d[0] for d in detections]
        scores = [d[1] for d in detections]
        keep_idx = SymbolDetector.non_max_suppression(boxes, scores, iou_thresh=0.25)
        
        return [{"bbox": list(boxes[i]), "score": float(scores[i])} for i in keep_idx]
    
    @staticmethod
    def detect_symbols_in_pdf(pdf_path, symbol_templates_dict, dpi=300, match_thresh=0.75):
        """Detect all symbols in PDF"""
        results = {
            "file": pdf_path,
            "dpi": dpi,
            "timestamp": datetime.utcnow().isoformat(),
            "pages": []
        }
        
        try:
            doc = fitz.open(pdf_path)
            
            for page_idx in range(len(doc)):
                print(f"[*] Processing page {page_idx + 1}/{len(doc)}...")
                
                img = SymbolDetector.rasterize_pdf_page(pdf_path, page_idx, dpi)
                if img is None:
                    continue
                
                page_result = {
                    "page": page_idx + 1,
                    "image_width": img.shape[1],
                    "image_height": img.shape[0],
                    "symbols": []
                }
                
                # Detect each symbol
                for symbol_name, template_img in symbol_templates_dict.items():
                    if template_img is None:
                        continue
                    
                    detections = SymbolDetector.multi_scale_template_match(
                        img, template_img, 
                        scales=(0.5, 0.75, 1.0, 1.25, 1.5),
                        match_thresh=match_thresh
                    )
                    
                    page_result['symbols'].append({
                        "symbol_name": symbol_name,
                        "count": len(detections),
                        "detections": detections
                    })
                    
                    print(f"  [{symbol_name}] Found: {len(detections)}")
                
                results['pages'].append(page_result)
            
            return results
        
        except Exception as e:
            print(f"[ERROR] Detection failed: {e}")
            return results


class SymbolDetectionDB:
    """Store detection results in MongoDB"""
    
    def __init__(self, db_name="utkarshproduction", collection_name="SYMBOL_DETECTIONS"):
        mongo_uri = os.getenv("MONGO_URI")
        if not mongo_uri:
            raise ValueError("[ERROR] MONGO_URI not set in .env")
        
        self.client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]
        self.client.admin.command('ping')
    
    def create_indexes(self):
        """Create indexes"""
        try:
            self.collection.create_index([("filename", 1)])
            self.collection.create_index([("timestamp", -1)])
            self.collection.create_index([("page", 1)])
            print("[OK] Indexes created")
        except Exception as e:
            print(f"[WARN] Index creation: {e}")
    
    def store_detection_results(self, pdf_filename, detection_results):
        """Store detection results"""
        try:
            for page_result in detection_results['pages']:
                doc = {
                    'filename': pdf_filename,
                    'page': page_result['page'],
                    'image_width': page_result['image_width'],
                    'image_height': page_result['image_height'],
                    'symbols': page_result['symbols'],
                    'timestamp': datetime.utcnow(),
                    'dpi': detection_results['dpi']
                }
                
                result = self.collection.insert_one(doc)
                print(f"[OK] Stored page {page_result['page']} detection results")
            
            return True
        except Exception as e:
            print(f"[ERROR] Store failed: {e}")
            return False
    
    def get_summary(self, filename):
        """Get summary of detections for file"""
        try:
            docs = list(self.collection.find({'filename': filename}))
            
            summary = {
                'filename': filename,
                'pages': [],
                'total_symbols': {}
            }
            
            for doc in docs:
                page_summary = {
                    'page': doc['page'],
                    'symbols': []
                }
                
                for sym in doc['symbols']:
                    page_summary['symbols'].append({
                        'name': sym['symbol_name'],
                        'count': sym['count']
                    })
                    
                    if sym['symbol_name'] not in summary['total_symbols']:
                        summary['total_symbols'][sym['symbol_name']] = 0
                    summary['total_symbols'][sym['symbol_name']] += sym['count']
                
                summary['pages'].append(page_summary)
            
            return summary
        except Exception as e:
            print(f"[ERROR] Summary failed: {e}")
            return None
    
    def close(self):
        self.client.close()


def main():
    """Main CLI"""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python symbol_detector.py upload <symbol_name> <image_path>")
        print("  python symbol_detector.py list")
        print("  python symbol_detector.py delete <symbol_name>")
        print("  python symbol_detector.py detect <pdf_path> [--store]")
        print("  python symbol_detector.py summary <filename>")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "upload":
        if len(sys.argv) < 4:
            print("[ERROR] Usage: symbol_detector.py upload <symbol_name> <image_path>")
            sys.exit(1)
        
        symbol_name = sys.argv[2]
        image_path = sys.argv[3]
        
        try:
            template_mgr = SymbolTemplate()
            template_mgr.upload_symbol(symbol_name, image_path)
            template_mgr.close()
        except Exception as e:
            print(f"[ERROR] {e}")
    
    elif command == "list":
        try:
            template_mgr = SymbolTemplate()
            symbols = template_mgr.list_symbols()
            
            print("\n" + "="*70)
            print("STORED SYMBOLS")
            print("="*70)
            
            if not symbols:
                print("No symbols stored")
            else:
                for sym in symbols:
                    print(f"\n{sym['symbol_name']}:")
                    print(f"  File: {sym['image_filename']}")
                    print(f"  Size: {sym['file_size']} bytes")
                    print(f"  Created: {sym['created_at']}")
            
            print("\n" + "="*70 + "\n")
            template_mgr.close()
        except Exception as e:
            print(f"[ERROR] {e}")
    
    elif command == "delete":
        if len(sys.argv) < 3:
            print("[ERROR] Usage: symbol_detector.py delete <symbol_name>")
            sys.exit(1)
        
        symbol_name = sys.argv[2]
        
        try:
            template_mgr = SymbolTemplate()
            template_mgr.delete_symbol(symbol_name)
            template_mgr.close()
        except Exception as e:
            print(f"[ERROR] {e}")
    
    elif command == "detect":
        if len(sys.argv) < 3:
            print("[ERROR] Usage: symbol_detector.py detect <pdf_path> [--store]")
            sys.exit(1)
        
        pdf_path = sys.argv[2]
        store = '--store' in sys.argv
        
        if not Path(pdf_path).exists():
            print(f"[ERROR] File not found: {pdf_path}")
            sys.exit(1)
        
        try:
            # Get all symbols
            template_mgr = SymbolTemplate()
            symbols = template_mgr.list_symbols()
            
            if not symbols:
                print("[ERROR] No symbols stored. Upload symbols first.")
                template_mgr.close()
                sys.exit(1)
            
            print(f"\n[*] Loading {len(symbols)} symbol templates...")
            templates_dict = {}
            for sym in symbols:
                img = template_mgr.get_symbol(sym['symbol_name'])
                if img is not None:
                    templates_dict[sym['symbol_name']] = img
                    print(f"  [OK] {sym['symbol_name']}")
            
            template_mgr.close()
            
            # Detect
            print(f"\n[*] Detecting symbols in: {pdf_path}")
            print("="*70)
            
            detector = SymbolDetector()
            results = detector.detect_symbols_in_pdf(pdf_path, templates_dict, dpi=300, match_thresh=0.75)
            
            # Print summary
            print("\n" + "="*70)
            print("DETECTION RESULTS")
            print("="*70)
            
            for page_result in results['pages']:
                print(f"\nPage {page_result['page']}:")
                for sym in page_result['symbols']:
                    print(f"  {sym['symbol_name']}: {sym['count']} instances")
            
            print("\n" + "="*70)
            
            # Export JSON
            output_file = f"{Path(pdf_path).stem}_symbol_detections.json"
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\n[OK] Saved to: {output_file}")
            
            # Store in MongoDB
            if store:
                print("\n[*] Storing in MongoDB...")
                detection_db = SymbolDetectionDB()
                detection_db.create_indexes()
                detection_db.store_detection_results(Path(pdf_path).name, results)
                detection_db.close()
        
        except Exception as e:
            print(f"[ERROR] {e}")
    
    elif command == "summary":
        if len(sys.argv) < 3:
            print("[ERROR] Usage: symbol_detector.py summary <filename>")
            sys.exit(1)
        
        filename = sys.argv[2]
        
        try:
            detection_db = SymbolDetectionDB()
            summary = detection_db.get_summary(filename)
            
            if summary and summary['pages']:
                print("\n" + "="*70)
                print("DETECTION SUMMARY")
                print("="*70)
                print(f"\nFile: {summary['filename']}")
                print(f"\nPer-Page Counts:")
                for page in summary['pages']:
                    print(f"  Page {page['page']}:")
                    for sym in page['symbols']:
                        print(f"    {sym['name']}: {sym['count']}")
                
                print(f"\nTotal Per Symbol:")
                for sym_name, count in summary['total_symbols'].items():
                    print(f"  {sym_name}: {count}")
                
                print("\n" + "="*70 + "\n")
            else:
                print("[WARN] No detection results found")
            
            detection_db.close()
        except Exception as e:
            print(f"[ERROR] {e}")


if __name__ == "__main__":
    main()
