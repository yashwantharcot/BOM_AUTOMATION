#!/usr/bin/env python3
"""
CAD to MongoDB Mapper
Extracts text, geometry, and structured data from CAD PDFs
Maps relationships as key-value pairs in MongoDB
"""

import sys
import json
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict

try:
    import pdfplumber
    import pymongo
    from pymongo import MongoClient
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", 
                          "pdfplumber", "pymongo"])
    import pdfplumber
    import pymongo
    from pymongo import MongoClient


class CADTextExtractor:
    """Extract structured data from CAD PDF text"""
    
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.raw_text = ""
        self.extracted_data = {}
    
    def extract_raw_text(self):
        """Extract all text from PDF"""
        with pdfplumber.open(self.pdf_path) as pdf:
            for page in pdf.pages:
                self.raw_text += page.extract_text() or ""
        return self.raw_text
    
    def extract_structured_data(self):
        """Parse text into structured key-value data"""
        data = {}
        
        # Item Number
        match = re.search(r'Item\s*(?:no|number)[.:\s]+(\d+)', self.raw_text, re.IGNORECASE)
        if match:
            data['item_number'] = int(match.group(1))
        
        # Mass/Weight
        match = re.search(r'Mass\s*\(kg\)[.:\s]+(\d+(?:\.\d+)?)', self.raw_text, re.IGNORECASE)
        if match:
            data['mass_kg'] = float(match.group(1))
        
        # Material specifications
        materials = []
        material_patterns = [
            r'Material\s*/?[\s:]+([A-Za-z0-9\-+ \.]+?)(?:\n|Scale|Form|Tolerance)',
            r'EN\s*(\d+:?\d+[A-Za-z\d\-+\.]*)',
        ]
        for pattern in material_patterns:
            matches = re.findall(pattern, self.raw_text, re.IGNORECASE)
            materials.extend(matches)
        if materials:
            data['materials'] = [m.strip() for m in materials if m.strip()]
        
        # Scale
        match = re.search(r'Scale\s*[.:\s]+([0-9:.]+)', self.raw_text, re.IGNORECASE)
        if match:
            data['scale'] = match.group(1)
        
        # Tolerance standards
        match = re.search(r'Tolerances?\s+(?:acc|according)\s+to\s*[.:\s]+([A-Za-z0-9\s\-\.]+?)(?:\n|All|To)', self.raw_text, re.IGNORECASE)
        if match:
            data['tolerance_standard'] = match.group(1).strip()
        
        # Part description
        match = re.search(r'(?:Description|Proj)[.:\s]+(.+?)(?:\n|Scale|Material)', self.raw_text, re.IGNORECASE)
        if match:
            data['description'] = match.group(1).strip()
        
        # Dimensions - extract all numbers with mm
        dimensions = re.findall(r'(\d+(?:\.\d+)?)\s*(?:mm|Ø|×)', self.raw_text)
        if dimensions:
            data['dimensions_mm'] = [float(d) for d in dimensions]
        
        # Quantities
        quantities = re.findall(r'(?:QTY|Quantity|Qty)[.:\s]+(\d+)', self.raw_text, re.IGNORECASE)
        if quantities:
            data['quantities'] = [int(q) for q in quantities]
        
        # Forms/Standards
        forms = re.findall(r'(?:Form|Standard)\s+(?:acc|according)\s+to\s+([A-Z]+)', self.raw_text)
        if forms:
            data['form_standards'] = list(set(forms))
        
        # Created/Revised dates
        dates = re.findall(r'(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})', self.raw_text)
        if dates:
            data['dates_found'] = dates
        
        # Extract key-value pairs from text blocks
        lines = self.raw_text.split('\n')
        key_value_pairs = []
        
        for line in lines:
            line = line.strip()
            # Match patterns like "Label: value" or "Label = value"
            if re.search(r'[A-Za-z\s]+[.:\s=]+[A-Za-z0-9\s\-\.]', line) and len(line) > 5:
                key_value_pairs.append(line)
        
        if key_value_pairs:
            data['text_lines'] = key_value_pairs
        
        self.extracted_data = data
        return data
    
    def get_all_data(self):
        """Extract all data"""
        self.extract_raw_text()
        self.extract_structured_data()
        return {
            'source_file': str(self.pdf_path),
            'extraction_date': datetime.now().isoformat(),
            'raw_text': self.raw_text,
            'structured_data': self.extracted_data
        }


class MongoDBStorage:
    """Store and retrieve CAD data in MongoDB"""
    
    def __init__(self, connection_string="mongodb://localhost:27017/", db_name="utkarshindia"):
        self.connection_string = connection_string
        self.db_name = db_name
        self.client = None
        self.db = None
    
    def connect(self):
        """Connect to MongoDB"""
        try:
            self.client = MongoClient(self.connection_string, serverSelectionTimeoutMS=5000)
            self.client.admin.command('ping')
            self.db = self.client[self.db_name]
            print("[OK] Connected to MongoDB: {}".format(self.db_name))
            return True
        except Exception as e:
            print("[ERROR] MongoDB connection failed: {}".format(e))
            print("  Install MongoDB or ensure it is running")
            return False
    
    def store_extraction(self, data):
        """Store extracted CAD data in MongoDB"""
        if not self.db:
            print("[ERROR] Not connected to MongoDB")
            return None
        
        try:
            # Main drawing collection
            collection = self.db['drawings']
            doc = {
                'source_file': data['source_file'],
                'extraction_date': data['extraction_date'],
                'structured_data': data['structured_data'],
                'created_at': datetime.now()
            }
            
            result = collection.insert_one(doc)
            print("[OK] Stored drawing with ID: {}".format(result.inserted_id))
            
            # Store each extracted field as separate document
            fields_collection = self.db['fields']
            for key, value in data['structured_data'].items():
                fields_collection.insert_one({
                    'drawing_id': result.inserted_id,
                    'field_name': key,
                    'field_value': value,
                    'data_type': type(value).__name__
                })
            
            print("[OK] Stored {} fields in MongoDB".format(len(data['structured_data'])))
            return result.inserted_id
        
        except Exception as e:
            print("[ERROR] Failed to store in MongoDB: {}".format(e))
            return None
    
    def query_by_field(self, field_name, field_value):
        """Query drawings by structured field"""
        if not self.db:
            return []
        try:
            collection = self.db['drawings']
            results = list(collection.find({
                'structured_data.{}'.format(field_name): field_value
            }))
            return results
        except:
            return []
    
    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()


def print_extraction_summary(data):
    """Print nicely formatted summary"""
    print("\n" + "="*70)
    print("CAD EXTRACTION SUMMARY")
    print("="*70)
    
    struct_data = data['structured_data']
    
    print("\nEXTRACTED FIELDS:")
    print("-"*70)
    for key, value in struct_data.items():
        if isinstance(value, list):
            value_str = str(value)[:50]
        else:
            value_str = str(value)[:50]
        print("{:<30} = {}".format(key, value_str))
    
    print("\n" + "="*70)
    print("TEXT EXTRACTION (first 500 chars):")
    print("="*70)
    print(data['raw_text'][:500])
    print("\n... ({}total characters)".format(len(data['raw_text'])))


def save_json_export(data, output_path):
    """Save extracted data as JSON"""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, default=str)
    print("[OK] Saved JSON export to: {}".format(output_path))


def main():
    if len(sys.argv) < 2:
        print("Usage: python cad_mongo_mapper.py <pdf_path> [--mongodb]")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    use_mongodb = '--mongodb' in sys.argv
    
    if not Path(pdf_path).exists():
        print("[ERROR] File not found: {}".format(pdf_path))
        sys.exit(1)
    
    print("\n" + "="*70)
    print("CAD PDF TEXT EXTRACTION & STRUCTURE MAPPING")
    print("="*70)
    
    # Extract data
    print("\nExtracting CAD data from PDF...")
    extractor = CADTextExtractor(pdf_path)
    data = extractor.get_all_data()
    
    # Print summary
    print_extraction_summary(data)
    
    # Save JSON
    json_path = str(Path(pdf_path).stem) + "_extracted.json"
    save_json_export(data, json_path)
    
    # Store in MongoDB
    if use_mongodb:
        print("\nConnecting to MongoDB...")
        storage = MongoDBStorage()
        if storage.connect():
            drawing_id = storage.store_extraction(data)
            if drawing_id:
                print("[OK] Drawing ID in MongoDB: {}".format(drawing_id))
            storage.close()
    
    print("\n" + "="*70)
    print("EXTRACTION COMPLETE")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
