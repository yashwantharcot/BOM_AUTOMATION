#!/usr/bin/env python3
"""
All-in-One: Extract CAD data and store in MongoDB
Usage: python extract_and_store.py <pdf_file>
"""

import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime
import os

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def extract_pdf(pdf_file):
    """Step 1: Extract data from PDF"""
    output_file = pdf_file.replace('.pdf', '_extraction.json')
    
    print("="*70)
    print("STEP 1: EXTRACT CAD DATA FROM PDF")
    print("="*70)
    print(f"[*] Extracting from: {pdf_file}")
    print(f"[*] Output will be: {output_file}\n")
    
    try:
        script_dir = Path(__file__).parent.parent
        result = subprocess.run(
            [sys.executable, str(script_dir / "core" / "extract_cad.py"), pdf_file, "--output", output_file],
            capture_output=False,
            timeout=300
        )
        
        if result.returncode != 0:
            print("[ERROR] Extraction failed")
            return None
        
        if not Path(output_file).exists():
            print(f"[ERROR] Output file not created: {output_file}")
            return None
        
        print(f"[OK] Extraction complete: {output_file}\n")
        return output_file
    
    except subprocess.TimeoutExpired:
        print("[ERROR] Extraction timeout (>5 minutes)")
        return None
    except Exception as e:
        print(f"[ERROR] Extraction error: {e}")
        return None


def import_to_mongo(json_file):
    """Step 2: Import extracted data to MongoDB"""
    print("="*70)
    print("STEP 2: IMPORT TO MONGODB")
    print("="*70)
    print(f"[*] Importing: {json_file}\n")
    
    try:
        script_dir = Path(__file__).parent.parent
        result = subprocess.run(
            [sys.executable, str(script_dir / "database" / "import_to_mongo.py"), json_file],
            capture_output=False,
            timeout=120
        )
        
        if result.returncode != 0:
            print("[ERROR] Import failed")
            return False
        
        print("[OK] Import complete\n")
        return True
    
    except subprocess.TimeoutExpired:
        print("[ERROR] Import timeout (>2 minutes)")
        return False
    except Exception as e:
        print(f"[ERROR] Import error: {e}")
        return False


def main():
    """Main pipeline"""
    if len(sys.argv) < 2:
        print("Usage: python extract_and_store.py <pdf_file>")
        print("\nExample:")
        print("  python extract_and_store.py H.pdf")
        sys.exit(1)
    
    pdf_file = sys.argv[1]
    
    if not Path(pdf_file).exists():
        print(f"[ERROR] PDF file not found: {pdf_file}")
        sys.exit(1)
    
    print("\n" + "="*70)
    print("CAD EXTRACTION + MONGODB PIPELINE")
    print("="*70 + "\n")
    
    start_time = datetime.now()
    
    # Step 1: Extract
    json_file = extract_pdf(pdf_file)
    if not json_file:
        sys.exit(1)
    
    # Step 2: Import
    if not import_to_mongo(json_file):
        sys.exit(1)
    
    # Summary
    elapsed = datetime.now() - start_time
    print("="*70)
    print("PIPELINE COMPLETE")
    print("="*70)
    print(f"PDF: {pdf_file}")
    print(f"Extraction: {json_file}")
    print(f"Database: utkarshproduction")
    print(f"Collection: BOMAUTOMATION")
    print(f"Total Time: {elapsed.total_seconds():.1f} seconds")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
