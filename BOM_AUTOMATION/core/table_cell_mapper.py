#!/usr/bin/env python3
"""
CAD Table & Cells to Key-Value Mapper
Extracts tables from CAD PDFs and maps cells as key-value pairs
Stores structured table data in MongoDB
"""

import sys
import json
import re
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

try:
    import pdfplumber
    from pymongo import MongoClient
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", 
                          "pdfplumber", "pymongo", "python-dotenv"])
    import pdfplumber
    from pymongo import MongoClient

load_dotenv()

class TableExtractor:
    """Extract and map table cells as key-value pairs"""
    
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.tables = []
        self.extracted_tables = {}
    
    def extract_tables(self):
        """Extract all tables from PDF"""
        with pdfplumber.open(self.pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                tables = page.extract_tables()
                if tables:
                    print(f"[OK] Found {len(tables)} table(s) on page {page_num}")
                    for table_idx, table in enumerate(tables):
                        self.tables.append({
                            'page': page_num,
                            'table_index': table_idx,
                            'raw_data': table
                        })
        return self.tables
    
    def clean_cell_value(self, value):
        """Clean and normalize cell value"""
        if value is None:
            return None
        if isinstance(value, str):
            # Remove extra whitespace and special characters
            cleaned = value.strip()
            # Remove embedded unicode characters like (cid:1)
            cleaned = re.sub(r'\(cid:\d+\)', '', cleaned)
            cleaned = re.sub(r'\s+', ' ', cleaned)  # Normalize spaces
            return cleaned if cleaned else None
        return value
    
    def extract_key_value_from_table(self, table):
        """Map table rows/cells as key-value pairs"""
        key_values = {}
        
        if not table or len(table) < 2:
            return key_values
        
        # Strategy 1: First column as keys, second column as values
        for row in table:
            if len(row) >= 2:
                key = self.clean_cell_value(row[0])
                value = self.clean_cell_value(row[1])
                
                if key and value and len(key) > 0 and len(value) > 0:
                    # Clean key (remove special chars, normalize)
                    key_clean = re.sub(r'[^a-zA-Z0-9_\s]', '', key).strip().replace(' ', '_').lower()
                    if key_clean:
                        key_values[key_clean] = value
        
        return key_values
    
    def extract_header_data(self, table):
        """Extract header information as key-value pairs"""
        header_data = {}
        
        # Look for common header patterns
        all_text = []
        for row in table:
            for cell in row:
                if cell:
                    all_text.append(str(cell))
        
        full_text = ' '.join(all_text)
        
        # Item Number
        match = re.search(r'Item\s*no\.?\s*:\s*(\w+)', full_text, re.IGNORECASE)
        if match:
            header_data['item_number'] = match.group(1)
        
        # Mass/Weight
        match = re.search(r'Mass\s*\(kg\)\s*:\s*([\d.]+)', full_text, re.IGNORECASE)
        if match:
            header_data['mass_kg'] = float(match.group(1))
        
        # Material
        match = re.search(r'Material\s*/?.*?:\s*([A-Z0-9\-\+\s\.]+?)(?:\n|$)', full_text, re.IGNORECASE)
        if match:
            header_data['material'] = match.group(1).strip()
        
        # Drawing Number
        match = re.search(r'Drawing\s*no\.?\s*:\s*(\d+)', full_text, re.IGNORECASE)
        if match:
            header_data['drawing_number'] = match.group(1)
        
        # Date
        match = re.search(r'(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})', full_text)
        if match:
            header_data['date'] = match.group(1)
        
        # Scale
        match = re.search(r'Scale\s*:\s*([\d:.]+)', full_text, re.IGNORECASE)
        if match:
            header_data['scale'] = match.group(1)
        
        # Description/Title
        match = re.search(r'(?:Description|Proj)\s*:\s*(.+?)(?:\n|Scale|$)', full_text, re.IGNORECASE)
        if match:
            header_data['description'] = match.group(1).strip()
        
        return header_data
    
    def extract_all_tables_as_kv(self):
        """Extract all tables and convert to key-value pairs"""
        result = {}
        
        for idx, table_info in enumerate(self.tables):
            table = table_info['raw_data']
            page = table_info['page']
            
            table_key = f"table_page{page}_{idx}"
            
            # Extract key-value pairs from table
            kv_pairs = self.extract_key_value_from_table(table)
            header_data = self.extract_header_data(table)
            
            result[table_key] = {
                'page': page,
                'table_index': idx,
                'raw_rows': len(table),
                'raw_columns': len(table[0]) if table else 0,
                'key_value_pairs': kv_pairs,
                'header_data': header_data,
                'raw_table': table
            }
        
        self.extracted_tables = result
        return result


class MongoTableStorage:
    """Store extracted table data in MongoDB"""
    
    def __init__(self, db_name="utkarshproduction", collection_name="TABLE_MAPPINGS"):
        mongo_uri = os.getenv("MONGO_URI")
        if not mongo_uri:
            raise ValueError("[ERROR] MONGO_URI not set in .env")
        
        self.mongo_uri = mongo_uri
        self.db_name = db_name
        self.collection_name = collection_name
        self.client = None
        self.db = None
        self.collection = None
    
    def connect(self):
        """Connect to MongoDB"""
        try:
            self.client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=5000)
            self.client.admin.command('ping')
            self.db = self.client[self.db_name]
            self.collection = self.db[self.collection_name]
            print(f"[OK] Connected to MongoDB")
            print(f"[OK] Database: {self.db_name}")
            print(f"[OK] Collection: {self.collection_name}")
            return True
        except Exception as e:
            print(f"[ERROR] MongoDB connection failed: {e}")
            return False
    
    def create_indexes(self):
        """Create indexes for fast queries"""
        try:
            self.collection.create_index([("filename", 1)])
            self.collection.create_index([("page", 1)])
            self.collection.create_index([("table_index", 1)])
            self.collection.create_index([("import_date", -1)])
            print("[OK] Indexes created")
        except Exception as e:
            print(f"[WARN] Index creation: {e}")
    
    def store_table_mapping(self, filename, extracted_tables):
        """Store extracted table mappings in MongoDB"""
        try:
            for table_key, table_data in extracted_tables.items():
                doc = {
                    'filename': filename,
                    'page': table_data['page'],
                    'table_index': table_data['table_index'],
                    'raw_rows': table_data['raw_rows'],
                    'raw_columns': table_data['raw_columns'],
                    'key_value_pairs': table_data['key_value_pairs'],
                    'header_data': table_data['header_data'],
                    'import_date': datetime.utcnow(),
                    'raw_table': table_data['raw_table']
                }
                
                result = self.collection.insert_one(doc)
                print(f"[OK] Stored table mapping: {result.inserted_id}")
            
            return True
        except Exception as e:
            print(f"[ERROR] Failed to store table mapping: {e}")
            return False
    
    def query_all_mappings(self):
        """Query all table mappings"""
        try:
            docs = list(self.collection.find())
            return docs
        except Exception as e:
            print(f"[ERROR] Query failed: {e}")
            return []
    
    def query_by_filename(self, filename):
        """Query mappings by filename"""
        try:
            docs = list(self.collection.find({'filename': filename}))
            return docs
        except Exception as e:
            print(f"[ERROR] Query failed: {e}")
            return []
    
    def close(self):
        """Close connection"""
        if self.client:
            self.client.close()
            print("[OK] MongoDB connection closed")


def print_table_summary(extracted_tables):
    """Print extracted table mappings"""
    print("\n" + "="*80)
    print("TABLE EXTRACTION SUMMARY - KEY-VALUE MAPPINGS")
    print("="*80)
    
    for table_key, table_data in extracted_tables.items():
        print(f"\n{table_key}:")
        print(f"  Page: {table_data['page']}")
        print(f"  Dimensions: {table_data['raw_rows']} rows x {table_data['raw_columns']} columns")
        
        # Print header data
        if table_data['header_data']:
            print(f"  Header Data (Key-Value):")
            for k, v in table_data['header_data'].items():
                print(f"    {k}: {v}")
        
        # Print first few key-value pairs
        if table_data['key_value_pairs']:
            print(f"  Cell Mappings (Key-Value):")
            for i, (k, v) in enumerate(list(table_data['key_value_pairs'].items())[:5]):
                print(f"    {k}: {v}")
            if len(table_data['key_value_pairs']) > 5:
                print(f"    ... and {len(table_data['key_value_pairs']) - 5} more")
    
    print("\n" + "="*80)


def save_json_export(data, output_path):
    """Save extracted mappings as JSON"""
    # Convert to JSON-serializable format
    json_data = {}
    for key, table in data.items():
        json_data[key] = {
            'page': table['page'],
            'table_index': table['table_index'],
            'raw_rows': table['raw_rows'],
            'raw_columns': table['raw_columns'],
            'key_value_pairs': table['key_value_pairs'],
            'header_data': table['header_data']
        }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    print(f"[OK] Saved JSON export to: {output_path}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python table_cell_mapper.py <pdf_path> [--store-mongo]")
        print("\nExample:")
        print("  python table_cell_mapper.py H.pdf")
        print("  python table_cell_mapper.py H.pdf --store-mongo")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    store_mongo = '--store-mongo' in sys.argv
    
    if not Path(pdf_path).exists():
        print(f"[ERROR] File not found: {pdf_path}")
        sys.exit(1)
    
    print("\n" + "="*80)
    print("PDF TABLE CELL EXTRACTOR - KEY-VALUE MAPPER")
    print("="*80)
    
    # Extract tables
    print(f"\n[*] Extracting tables from: {pdf_path}")
    extractor = TableExtractor(pdf_path)
    tables = extractor.extract_tables()
    
    if not tables:
        print("[WARN] No tables found in PDF")
        sys.exit(0)
    
    # Convert to key-value pairs
    print(f"\n[*] Converting {len(tables)} table(s) to key-value pairs...")
    extracted_tables = extractor.extract_all_tables_as_kv()
    
    # Print summary
    print_table_summary(extracted_tables)
    
    # Save JSON
    json_path = str(Path(pdf_path).stem) + "_table_mappings.json"
    save_json_export(extracted_tables, json_path)
    
    # Store in MongoDB
    if store_mongo:
        print("\n[*] Storing table mappings in MongoDB...")
        storage = MongoTableStorage()
        if storage.connect():
            storage.create_indexes()
            if storage.store_table_mapping(pdf_path, extracted_tables):
                print(f"[OK] Stored {len(extracted_tables)} table(s) in MongoDB")
            storage.close()
    
    print("\n" + "="*80)
    print("EXTRACTION COMPLETE")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
