#!/usr/bin/env python3
"""
MongoDB CAD Data Manager
Import, query, and manage CAD drawing data in MongoDB
"""

import sys
import json
from pathlib import Path
from datetime import datetime

try:
    import pymongo
    from pymongo import MongoClient
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pymongo"])
    import pymongo
    from pymongo import MongoClient


class MongoCADManager:
    """Manage CAD drawing data in MongoDB"""
    
    def __init__(self, uri="mongodb://localhost:27017/", db_name="cad_drawings"):
        self.uri = uri
        self.db_name = db_name
        self.client = None
        self.db = None
    
    def connect(self):
        """Connect to MongoDB"""
        try:
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
            self.client.admin.command('ping')
            self.db = self.client[self.db_name]
            print("[OK] Connected to MongoDB: {}".format(self.db_name))
            return True
        except Exception as e:
            print("[ERROR] Cannot connect to MongoDB: {}".format(e))
            return False
    
    def import_json(self, json_file):
        """Import JSON extracted data into MongoDB"""
        if not self.db:
            print("[ERROR] Not connected to MongoDB")
            return False
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Store main drawing
            drawings = self.db['drawings']
            doc = {
                'source_file': data['source_file'],
                'extraction_date': data['extraction_date'],
                'structured_data': data['structured_data'],
                'imported_at': datetime.now(),
                'raw_text_length': len(data.get('raw_text', ''))
            }
            result = drawings.insert_one(doc)
            drawing_id = result.inserted_id
            print("[OK] Imported drawing document with ID: {}".format(drawing_id))
            
            # Parse and store structured fields as key-value pairs
            fields = self.db['extracted_fields']
            field_docs = []
            
            for key, value in data['structured_data'].items():
                field_docs.append({
                    'drawing_id': drawing_id,
                    'field_name': key,
                    'field_value': value,
                    'data_type': str(type(value).__name__),
                    'created_at': datetime.now()
                })
            
            if field_docs:
                fields.insert_many(field_docs)
                print("[OK] Stored {} structured fields".format(len(field_docs)))
            
            # Index for faster queries
            drawings.create_index('source_file')
            fields.create_index('drawing_id')
            fields.create_index('field_name')
            
            return drawing_id
        
        except Exception as e:
            print("[ERROR] Failed to import JSON: {}".format(e))
            return False
    
    def get_drawing_by_id(self, drawing_id):
        """Retrieve drawing by MongoDB ObjectId"""
        if not self.db:
            return None
        try:
            from bson import ObjectId
            return self.db['drawings'].find_one({'_id': ObjectId(drawing_id)})
        except:
            return None
    
    def get_drawing_by_source(self, source_file):
        """Retrieve drawing by source file"""
        if not self.db:
            return None
        return self.db['drawings'].find_one({'source_file': source_file})
    
    def query_fields(self, field_name, value=None):
        """Query extracted fields"""
        if not self.db:
            return []
        
        query = {'field_name': field_name}
        if value:
            query['field_value'] = value
        
        return list(self.db['extracted_fields'].find(query))
    
    def get_drawing_fields(self, drawing_id):
        """Get all fields for a specific drawing"""
        if not self.db:
            return {}
        
        try:
            from bson import ObjectId
            fields = list(self.db['extracted_fields'].find({'drawing_id': ObjectId(drawing_id)}))
            result = {}
            for f in fields:
                result[f['field_name']] = f['field_value']
            return result
        except:
            return {}
    
    def list_all_drawings(self):
        """List all stored drawings"""
        if not self.db:
            return []
        return list(self.db['drawings'].find({}, {
            'source_file': 1,
            'extraction_date': 1,
            'imported_at': 1,
            'raw_text_length': 1
        }))
    
    def get_statistics(self):
        """Get database statistics"""
        if not self.db:
            return {}
        
        return {
            'total_drawings': self.db['drawings'].count_documents({}),
            'total_fields': self.db['extracted_fields'].count_documents({}),
            'collections': self.db.list_collection_names()
        }
    
    def export_drawing_as_json(self, drawing_id, output_file):
        """Export a drawing as JSON"""
        if not self.db:
            return False
        
        try:
            from bson import ObjectId
            drawing = self.db['drawings'].find_one({'_id': ObjectId(drawing_id)})
            if not drawing:
                print("[ERROR] Drawing not found")
                return False
            
            # Convert ObjectId to string for JSON serialization
            drawing['_id'] = str(drawing['_id'])
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(drawing, f, indent=2, default=str)
            
            print("[OK] Exported drawing to: {}".format(output_file))
            return True
        
        except Exception as e:
            print("[ERROR] Export failed: {}".format(e))
            return False
    
    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            print("[OK] MongoDB connection closed")


def print_interactive_menu():
    """Print interactive menu"""
    print("\n" + "="*70)
    print("MongoDB CAD DATA MANAGER")
    print("="*70)
    print("\n1. Import JSON extracted data")
    print("2. List all drawings")
    print("3. Query drawing by source file")
    print("4. Query by field name")
    print("5. Get drawing fields")
    print("6. Database statistics")
    print("7. Export drawing as JSON")
    print("8. Exit")
    print("-"*70)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--import':
        # Command-line import mode
        if len(sys.argv) < 3:
            print("Usage: python mongo_manager.py --import <json_file>")
            sys.exit(1)
        
        json_file = sys.argv[2]
        
        if not Path(json_file).exists():
            print("[ERROR] File not found: {}".format(json_file))
            sys.exit(1)
        
        manager = MongoCADManager()
        if manager.connect():
            drawing_id = manager.import_json(json_file)
            if drawing_id:
                print("\n[OK] Successfully imported to MongoDB")
                print("     Drawing ID: {}".format(drawing_id))
            manager.close()
        return
    
    # Interactive mode
    manager = MongoCADManager()
    
    if not manager.connect():
        print("\nNote: This tool requires MongoDB installed and running.")
        print("Install: https://www.mongodb.com/try/download/community")
        print("Run:     mongod --dbpath C:\\data\\db")
        sys.exit(1)
    
    while True:
        print_interactive_menu()
        choice = input("Enter choice (1-8): ").strip()
        
        if choice == '1':
            json_file = input("Enter JSON file path: ").strip()
            if Path(json_file).exists():
                drawing_id = manager.import_json(json_file)
            else:
                print("[ERROR] File not found")
        
        elif choice == '2':
            drawings = manager.list_all_drawings()
            if drawings:
                print("\n" + "-"*70)
                for i, d in enumerate(drawings, 1):
                    print("{}: {} ({})".format(i, d.get('source_file'), d.get('_id')))
            else:
                print("[INFO] No drawings found")
        
        elif choice == '3':
            source = input("Enter source file name: ").strip()
            drawing = manager.get_drawing_by_source(source)
            if drawing:
                print("\n[OK] Found drawing:")
                print("    ID: {}".format(drawing['_id']))
                print("    Extracted: {}".format(drawing['extraction_date']))
                print("    Fields: {}".format(len(drawing['structured_data'])))
            else:
                print("[ERROR] Drawing not found")
        
        elif choice == '4':
            field_name = input("Enter field name: ").strip()
            results = manager.query_fields(field_name)
            if results:
                print("\n[OK] Found {} fields with name '{}'".format(len(results), field_name))
                for r in results[:5]:
                    print("    - {}".format(r.get('field_value')))
            else:
                print("[ERROR] No fields found")
        
        elif choice == '5':
            drawing_id = input("Enter drawing ID (ObjectId string): ").strip()
            fields = manager.get_drawing_fields(drawing_id)
            if fields:
                print("\n[OK] Drawing fields:")
                for key, value in fields.items():
                    val_str = str(value)[:50]
                    print("    {}: {}".format(key, val_str))
            else:
                print("[ERROR] No fields found or invalid ID")
        
        elif choice == '6':
            stats = manager.get_statistics()
            print("\n" + "-"*70)
            print("DATABASE STATISTICS:")
            print("  Total Drawings: {}".format(stats.get('total_drawings', 0)))
            print("  Total Fields: {}".format(stats.get('total_fields', 0)))
            print("  Collections: {}".format(', '.join(stats.get('collections', []))))
        
        elif choice == '7':
            drawing_id = input("Enter drawing ID: ").strip()
            output_file = input("Enter output JSON file: ").strip()
            manager.export_drawing_as_json(drawing_id, output_file)
        
        elif choice == '8':
            break
        
        else:
            print("[ERROR] Invalid choice")
    
    manager.close()


if __name__ == "__main__":
    main()
