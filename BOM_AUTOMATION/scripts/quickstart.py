#!/usr/bin/env python3
"""
QUICKSTART - CAD Drawing to MongoDB BOM Automation
One-command setup and processing
"""

import sys
import subprocess
from pathlib import Path

def print_banner():
    print("""
╔═══════════════════════════════════════════════════════════════╗
║     CAD DRAWING EXTRACTION & MONGODB BOM AUTOMATION          ║
║                    QUICKSTART SETUP                          ║
╚═══════════════════════════════════════════════════════════════╝
    """)

def check_requirements():
    """Check if required Python packages are installed"""
    print("\n[1/4] Checking Python dependencies...")
    
    required = ['pdfplumber', 'pymongo']
    missing = []
    
    for package in required:
        try:
            __import__(package)
            print("      [OK] {} installed".format(package))
        except ImportError:
            missing.append(package)
            print("      [MISSING] {}".format(package))
    
    if missing:
        print("\n[INFO] Installing missing packages...")
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
        print("      [OK] Dependencies installed")
    
    return True

def analyze_pdf(pdf_path):
    """Run symbol analysis"""
    print("\n[2/4] Analyzing PDF symbols...")
    
    if not Path(pdf_path).exists():
        print("      [ERROR] File not found: {}".format(pdf_path))
        return False
    
    script_dir = Path(__file__).parent.parent
    result = subprocess.run([
        sys.executable, str(script_dir / "core" / "symbol_counter.py"), pdf_path
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        print("      [OK] Symbol analysis complete")
        return True
    else:
        print("      [ERROR] {}".format(result.stderr))
        return False

def extract_data(pdf_path):
    """Run CAD extraction"""
    print("\n[3/4] Extracting CAD data to structured format...")
    
    script_dir = Path(__file__).parent.parent
    result = subprocess.run([
        sys.executable, str(script_dir / "database" / "cad_mongo_mapper.py"), pdf_path
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        print("      [OK] Data extraction complete")
        # Print summary
        for line in result.stdout.split('\n'):
            if 'Saved JSON' in line or 'EXTRACTED' in line:
                print("      {}".format(line.strip()))
        return True
    else:
        print("      [ERROR] {}".format(result.stderr))
        return False

def show_results(pdf_path):
    """Display extraction results"""
    print("\n[4/4] Results Summary")
    print("-" * 65)
    
    json_file = Path(pdf_path).stem + "_extracted.json"
    
    if json_file.exists():
        import json
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print("\nEXTRACTED DATA:")
        for key, value in data['structured_data'].items():
            if isinstance(value, list):
                print("  {} ({}): {}...".format(
                    key, 
                    len(value),
                    str(value)[:40]
                ))
            else:
                print("  {}: {}".format(key, value))
    
    print("\nGENERATED FILES:")
    print("  - H_extracted.json - Structured data (JSON)")
    print("  - README.md - Full documentation")
    
    print("\nNEXT STEPS:")
    print("  1. Install MongoDB: https://www.mongodb.com/try/download/community")
    print("  2. Start MongoDB: mongod --dbpath C:\\data\\db")
    script_dir = Path(__file__).parent.parent
    print("  3. Import to MongoDB: python {} --import {}".format(
        script_dir / "database" / "mongo_manager.py", json_file))
    print("  4. Query data: python {}".format(script_dir / "database" / "mongo_manager.py"))

def main():
    print_banner()
    
    if len(sys.argv) < 2:
        print("Usage: python quickstart.py <pdf_file>")
        print("\nExample: python quickstart.py H.pdf")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    try:
        if check_requirements():
            if analyze_pdf(pdf_path):
                if extract_data(pdf_path):
                    show_results(pdf_path)
                    print("\n" + "="*65)
                    print("QUICKSTART COMPLETE")
                    print("="*65 + "\n")
    except Exception as e:
        print("\n[ERROR] {}".format(e))
        sys.exit(1)

if __name__ == "__main__":
    main()
