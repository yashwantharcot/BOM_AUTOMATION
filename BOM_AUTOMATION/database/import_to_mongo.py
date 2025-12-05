#!/usr/bin/env python3
"""
MongoDB Import Script - Store extracted CAD data in BOMAUTOMATION collection
Usage: python import_to_mongo.py <json_file> [--db-name <name>]
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

try:
    from pymongo import MongoClient, ASCENDING, DESCENDING
    from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
except ImportError:
    print("[ERROR] pymongo not installed. Run: pip install pymongo python-dotenv")
    sys.exit(1)

# Load environment variables
load_dotenv()

class MongoImporter:
    def __init__(self, mongo_uri=None, db_name="utkarshproduction", collection_name="BOMAUTOMATION"):
        """Initialize MongoDB connection"""
        self.mongo_uri = mongo_uri or os.getenv("MONGO_URI")
        self.db_name = db_name
        self.collection_name = collection_name
        self.client = None
        self.db = None
        self.collection = None
        
        if not self.mongo_uri:
            raise ValueError("[ERROR] MONGO_URI not set in .env or parameters")
    
    def connect(self):
        """Establish MongoDB connection"""
        try:
            print(f"[*] Connecting to MongoDB...")
            self.client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=5000)
            # Test connection
            self.client.admin.command('ping')
            print("[OK] Connected to MongoDB")
            
            self.db = self.client[self.db_name]
            self.collection = self.db[self.collection_name]
            print(f"[OK] Using database: {self.db_name}")
            print(f"[OK] Using collection: {self.collection_name}")
            
            return True
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            print(f"[ERROR] Failed to connect: {e}")
            return False
    
    def create_indexes(self):
        """Create indexes for fast queries"""
        try:
            print("[*] Creating indexes...")
            self.collection.create_index([("text", ASCENDING)])
            self.collection.create_index([("source", ASCENDING)])
            self.collection.create_index([("final_confidence", DESCENDING)])
            self.collection.create_index([("has_values", ASCENDING)])
            self.collection.create_index([("filename", ASCENDING)])
            self.collection.create_index([("import_date", DESCENDING)])
            print("[OK] Indexes created")
        except Exception as e:
            print(f"[WARN] Index creation error: {e}")
    
    def import_json(self, json_file):
        """Import extracted data from JSON file"""
        if not Path(json_file).exists():
            print(f"[ERROR] File not found: {json_file}")
            return False
        
        try:
            print(f"[*] Reading file: {json_file}")
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, dict) or 'pages' not in data:
                print("[ERROR] Invalid JSON format. Expected 'pages' key.")
                return False
            
            total_items = 0
            filename = data.get('file', Path(json_file).stem)
            import_date = datetime.utcnow()
            
            # Process each page
            print(f"[*] Processing {len(data['pages'])} page(s)...")
            for page_data in data['pages']:
                page_num = page_data.get('page', 0)
                extracted_text = page_data.get('extracted_text', [])
                
                if not extracted_text:
                    print(f"[WARN] Page {page_num}: No extracted text")
                    continue
                
                # Add metadata to each item
                items_to_insert = []
                for item in extracted_text:
                    item['filename'] = filename
                    item['page'] = page_num
                    item['import_date'] = import_date
                    items_to_insert.append(item)
                
                # Insert to MongoDB
                result = self.collection.insert_many(items_to_insert)
                count = len(result.inserted_ids)
                total_items += count
                
                print(f"[OK] Page {page_num}: {count} items inserted")
            
            # Print summary statistics
            self.print_summary(total_items, filename)
            return True
        
        except json.JSONDecodeError as e:
            print(f"[ERROR] Invalid JSON file: {e}")
            return False
        except Exception as e:
            print(f"[ERROR] Import failed: {e}")
            return False
    
    def print_summary(self, total_items, filename):
        """Print import summary statistics"""
        print("\n" + "="*70)
        print("IMPORT SUMMARY")
        print("="*70)
        
        try:
            # Collection stats
            count = self.collection.count_documents({})
            stats = self.db.command('collStats', self.collection_name)
            
            print(f"\nDatabase: {self.db_name}")
            print(f"Collection: {self.collection_name}")
            print(f"File: {filename}")
            print(f"Items Imported: {total_items}")
            print(f"Total Documents: {count}")
            print(f"Collection Size: {stats.get('size', 0) / 1024 / 1024:.2f} MB")
            
            # Quality statistics
            high_conf = self.collection.count_documents({"final_confidence": {"$gte": 0.9}})
            medium_conf = self.collection.count_documents({"final_confidence": {"$gte": 0.7, "$lt": 0.9}})
            low_conf = self.collection.count_documents({"final_confidence": {"$lt": 0.7}})
            with_values = self.collection.count_documents({"has_values": True})
            
            print(f"\nQuality Statistics:")
            print(f"  High Confidence (>=0.9): {high_conf} ({high_conf/count*100:.1f}%)")
            print(f"  Medium Confidence (0.7-0.9): {medium_conf} ({medium_conf/count*100:.1f}%)")
            print(f"  Low Confidence (<0.7): {low_conf} ({low_conf/count*100:.1f}%)")
            print(f"  Items with Values: {with_values} ({with_values/count*100:.1f}%)")
            
            # Source statistics
            vector_count = self.collection.count_documents({"source": "vector"})
            ocr_count = self.collection.count_documents({"source": "ocr"})
            
            print(f"\nSource Statistics:")
            print(f"  Vector: {vector_count} ({vector_count/count*100:.1f}%)")
            print(f"  OCR: {ocr_count} ({ocr_count/count*100:.1f}%)")
            
        except Exception as e:
            print(f"[WARN] Could not retrieve statistics: {e}")
        
        print("="*70 + "\n")
    
    def query_samples(self, limit=5):
        """Show sample documents"""
        try:
            print(f"[*] Sample documents (high confidence):")
            samples = self.collection.find(
                {"final_confidence": {"$gte": 0.9}},
                limit=limit
            )
            
            for i, doc in enumerate(samples, 1):
                text = doc.get('text', '')[:50]
                conf = doc.get('final_confidence', 0)
                values = doc.get('values', [])
                print(f"  {i}. {text}... [confidence: {conf:.2f}] [values: {len(values)}]")
        except Exception as e:
            print(f"[WARN] Could not retrieve samples: {e}")
    
    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            print("[OK] MongoDB connection closed")


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python import_to_mongo.py <json_file> [--db-name <name>]")
        print("\nExample:")
        print("  python import_to_mongo.py H_full_extraction.json")
        print("  python import_to_mongo.py result.json --db-name utkarshproduction")
        sys.exit(1)
    
    json_file = sys.argv[1]
    db_name = "utkarshproduction"  # Default
    
    # Parse optional arguments
    if "--db-name" in sys.argv:
        idx = sys.argv.index("--db-name")
        if idx + 1 < len(sys.argv):
            db_name = sys.argv[idx + 1]
    
    try:
        importer = MongoImporter(db_name=db_name, collection_name="BOMAUTOMATION")
        
        if not importer.connect():
            sys.exit(1)
        
        importer.create_indexes()
        
        if importer.import_json(json_file):
            importer.query_samples(limit=5)
            print("[OK] Import completed successfully!")
        else:
            print("[ERROR] Import failed")
            sys.exit(1)
        
        importer.close()
    
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
