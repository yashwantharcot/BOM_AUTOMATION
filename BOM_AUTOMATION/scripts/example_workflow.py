
#!/usr/bin/env python3
"""
Symbol Detection - Quick Start Example
Demonstrates all features of the symbol detection system
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Import our modules
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.symbol_detector import SymbolTemplate, SymbolDetector, SymbolDetectionDB

load_dotenv()


def print_header(title):
    """Print formatted header"""
    print("\n" + "="*70)
    print(title.center(70))
    print("="*70)


def example_workflow():
    """Complete example workflow"""
    
    print_header("SYMBOL DETECTION - COMPLETE WORKFLOW")
    
    # Step 1: Check MongoDB connection
    print("\n[STEP 1] Checking MongoDB connection...")
    try:
        template_mgr = SymbolTemplate()
        symbols = template_mgr.list_symbols()
        print(f"[OK] Connected to MongoDB")
        print(f"[OK] Found {len(symbols)} existing symbols")
        template_mgr.close()
    except Exception as e:
        print(f"[ERROR] MongoDB connection failed: {e}")
        print("[TIP] Ensure MONGO_URI is set in .env file")
        return
    
    # Step 2: Create sample symbol templates
    print("\n[STEP 2] Creating sample symbol templates...")
    
    sample_symbols_dir = Path("sample_symbols")
    sample_symbols_dir.mkdir(exist_ok=True)
    
    try:
        import numpy as np
        import cv2
        
        symbols_to_create = [
            ("circle", "Circle symbol", cv2.CHAIN_APPROX_SIMPLE),
            ("square", "Square symbol", None),
            ("triangle", "Triangle symbol", None)
        ]
        
        for symbol_name, description, _ in symbols_to_create:
            symbol_path = sample_symbols_dir / f"{symbol_name}.png"
            
            if not symbol_path.exists():
                # Create synthetic symbol
                img = np.ones((150, 150, 3), dtype=np.uint8) * 255  # white bg
                
                if symbol_name == "circle":
                    cv2.circle(img, (75, 75), 40, (0, 0, 0), 3)  # black circle
                elif symbol_name == "square":
                    cv2.rectangle(img, (35, 35), (115, 115), (0, 0, 0), 3)
                elif symbol_name == "triangle":
                    pts = np.array([[75, 35], [115, 115], [35, 115]], np.int32)
                    cv2.polylines(img, [pts], True, (0, 0, 0), 3)
                
                cv2.imwrite(str(symbol_path), img)
                print(f"  [OK] Created: {symbol_name}.png ({description})")
            else:
                print(f"  [SKIP] Already exists: {symbol_name}.png")
    
    except ImportError:
        print("  [WARN] numpy/cv2 not available, skipping sample creation")
        print("  [TIP] Provide your own symbol PNG files")
    
    # Step 3: Upload symbols to MongoDB
    print("\n[STEP 3] Uploading symbols to MongoDB...")
    try:
        template_mgr = SymbolTemplate()
        
        for symbol_file in sorted(sample_symbols_dir.glob("*.png")):
            symbol_name = symbol_file.stem
            doc_id = template_mgr.upload_symbol(symbol_name, str(symbol_file))
            if doc_id:
                print(f"  [OK] {symbol_name}: {doc_id}")
        
        template_mgr.close()
    except Exception as e:
        print(f"  [ERROR] Upload failed: {e}")
    
    # Step 4: List all symbols
    print("\n[STEP 4] Listing stored symbols...")
    try:
        template_mgr = SymbolTemplate()
        symbols = template_mgr.list_symbols()
        
        if symbols:
            for sym in symbols:
                print(f"  • {sym['symbol_name']}: {sym['file_size']} bytes")
        else:
            print("  [INFO] No symbols found")
        
        template_mgr.close()
    except Exception as e:
        print(f"  [ERROR] List failed: {e}")
    
    # Step 5: Test detection on sample PDF
    print("\n[STEP 5] Testing detection on H.pdf...")
    
    if not Path("H.pdf").exists():
        print("  [WARN] H.pdf not found, skipping detection test")
        print("  [TIP] Provide PDF file to test detection")
    else:
        try:
            # Load templates
            template_mgr = SymbolTemplate()
            symbols = template_mgr.list_symbols()
            
            if not symbols:
                print("  [WARN] No symbols stored")
                template_mgr.close()
            else:
                print(f"  [*] Loading {len(symbols)} templates...")
                templates_dict = {}
                for sym in symbols:
                    img = template_mgr.get_symbol(sym['symbol_name'])
                    if img is not None:
                        templates_dict[sym['symbol_name']] = img
                        print(f"    [OK] {sym['symbol_name']}")
                
                template_mgr.close()
                
                # Run detection
                print("\n  [*] Running detection...")
                detector = SymbolDetector()
                results = detector.detect_symbols_in_pdf("H.pdf", templates_dict, dpi=300)
                
                # Display results
                print("\n  [RESULTS]:")
                for page_result in results['pages']:
                    print(f"    Page {page_result['page']}:")
                    for sym in page_result['symbols']:
                        print(f"      {sym['symbol_name']}: {sym['count']} detections")
                
                # Save results
                output_file = "H_example_detections.json"
                with open(output_file, 'w') as f:
                    json.dump(results, f, indent=2, default=str)
                print(f"\n  [OK] Saved to: {output_file}")
                
                # Store in MongoDB
                print("\n  [*] Storing in MongoDB...")
                try:
                    detection_db = SymbolDetectionDB()
                    detection_db.create_indexes()
                    detection_db.store_detection_results("H.pdf", results)
                    detection_db.close()
                    print("  [OK] Stored in SYMBOL_DETECTIONS collection")
                except Exception as e:
                    print(f"  [WARN] MongoDB storage: {e}")
        
        except Exception as e:
            print(f"  [ERROR] Detection failed: {e}")
    
    # Step 6: Query results from MongoDB
    print("\n[STEP 6] Querying detection results from MongoDB...")
    try:
        detection_db = SymbolDetectionDB()
        summary = detection_db.get_summary("H.pdf")
        
        if summary and summary['pages']:
            print("\n  [SUMMARY]:")
            for page in summary['pages']:
                print(f"    Page {page['page']}:")
                for sym in page['symbols']:
                    print(f"      {sym['name']}: {sym['count']}")
            
            print("\n  [TOTALS]:")
            for sym_name, count in summary['total_symbols'].items():
                print(f"    {sym_name}: {count}")
        else:
            print("  [INFO] No results found in database")
        
        detection_db.close()
    except Exception as e:
        print(f"  [WARN] Query failed: {e}")
    
    # Step 7: Display API commands
    print("\n" + "="*70)
    print("NEXT STEPS - API COMMANDS".center(70))
    print("="*70)
    
    print("""
1. Start API Server:
   python api_server.py

2. Upload symbol via API:
   curl -X POST http://127.0.0.1:5000/api/v1/symbols \\
     -F "name=weld_circle" \\
     -F "file=@sample_symbols/circle.png"

3. List symbols via API:
   curl http://127.0.0.1:5000/api/v1/symbols

4. Upload PDF via API:
   curl -X POST http://127.0.0.1:5000/api/v1/upload \\
     -F "file=@H.pdf"

5. Get results via API:
   curl http://127.0.0.1:5000/api/v1/results/<job_id>

6. Check system stats:
   curl http://127.0.0.1:5000/api/v1/stats
""")
    
    print("="*70 + "\n")


if __name__ == "__main__":
    try:
        example_workflow()
    except KeyboardInterrupt:
        print("\n\n[INFO] Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)
