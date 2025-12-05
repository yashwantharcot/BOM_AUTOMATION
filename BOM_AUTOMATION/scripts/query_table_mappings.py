#!/usr/bin/env python3
"""
Query Table Cell Mappings from MongoDB
View and search key-value pairs extracted from PDF tables
"""

import json
import sys
import os
from dotenv import load_dotenv

try:
    from pymongo import MongoClient
except ImportError:
    print("[ERROR] pymongo not installed. Run: pip install pymongo python-dotenv")
    sys.exit(1)

load_dotenv()

class TableMappingQuery:
    def __init__(self, db_name="utkarshproduction", collection_name="TABLE_MAPPINGS"):
        """Initialize MongoDB connection"""
        mongo_uri = os.getenv("MONGO_URI")
        if not mongo_uri:
            raise ValueError("[ERROR] MONGO_URI not set in .env")
        
        self.client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]
        self.client.admin.command('ping')
        print(f"[OK] Connected to {db_name}.{collection_name}")
    
    def stats(self):
        """Show collection statistics"""
        count = self.collection.count_documents({})
        print(f"\nTable Mappings Statistics:")
        print(f"  Total Stored: {count}")
        
        # By file
        files = self.collection.distinct('filename')
        print(f"  Files: {len(files)}")
        for f in files:
            file_count = self.collection.count_documents({'filename': f})
            print(f"    {f}: {file_count} mappings")
        
        # By page
        pages = self.collection.distinct('page')
        print(f"  Pages: {sorted(pages)}")
    
    def show_all_tables(self, limit=100):
        """Show all table mappings"""
        docs = list(self.collection.find().limit(limit))
        
        print(f"\nAll Table Mappings ({len(docs)} found):")
        for i, doc in enumerate(docs, 1):
            print(f"\n  {i}. {doc['filename']} - Page {doc['page']}, Table {doc['table_index']}")
            print(f"     Size: {doc['raw_rows']}x{doc['raw_columns']}")
            
            if doc.get('header_data'):
                print(f"     Header Data:")
                for k, v in list(doc['header_data'].items())[:5]:
                    print(f"       {k}: {v}")
            
            if doc.get('key_value_pairs'):
                print(f"     Cell Mappings: {len(doc['key_value_pairs'])} pairs")
                for k, v in list(doc['key_value_pairs'].items())[:3]:
                    v_short = str(v)[:50]
                    print(f"       {k}: {v_short}")
    
    def show_by_filename(self, filename):
        """Show all tables from specific file"""
        docs = list(self.collection.find({'filename': filename}))
        
        print(f"\nTables from {filename} ({len(docs)} found):")
        for doc in docs:
            print(f"\n  Page {doc['page']}, Table {doc['table_index']}:")
            print(f"    Size: {doc['raw_rows']} rows x {doc['raw_columns']} columns")
            
            if doc.get('header_data'):
                print(f"    Header Data:")
                for k, v in doc['header_data'].items():
                    print(f"      {k}: {v}")
            
            if doc.get('key_value_pairs'):
                print(f"    Cell Key-Value Pairs ({len(doc['key_value_pairs'])} total):")
                for k, v in list(doc['key_value_pairs'].items())[:10]:
                    print(f"      {k}: {v}")
                if len(doc['key_value_pairs']) > 10:
                    print(f"      ... and {len(doc['key_value_pairs']) - 10} more")
    
    def show_by_page(self, page_num):
        """Show tables from specific page"""
        docs = list(self.collection.find({'page': page_num}))
        
        print(f"\nTables on Page {page_num} ({len(docs)} found):")
        for doc in docs:
            print(f"\n  Table {doc['table_index']} ({doc['filename']}):")
            print(f"    Dimensions: {doc['raw_rows']}x{doc['raw_columns']}")
            
            if doc.get('header_data'):
                print(f"    Header: {doc['header_data']}")
            
            if doc.get('key_value_pairs'):
                print(f"    Mappings: {len(doc['key_value_pairs'])} pairs")
    
    def export_all_as_json(self, output_file="table_mappings_export.json"):
        """Export all mappings as JSON"""
        docs = list(self.collection.find())
        
        export_data = {}
        for i, doc in enumerate(docs):
            if '_id' in doc:
                del doc['_id']
            if 'raw_table' in doc:
                del doc['raw_table']  # Remove raw table to reduce size
            if 'import_date' in doc:
                doc['import_date'] = str(doc['import_date'])  # Convert datetime to string
            
            export_data[f"table_{i}"] = doc
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"[OK] Exported {len(docs)} tables to {output_file}")
    
    def export_by_filename(self, filename, output_file=None):
        """Export tables from specific file"""
        if not output_file:
            output_file = f"{filename.split('.')[0]}_table_export.json"
        
        docs = list(self.collection.find({'filename': filename}))
        
        export_data = {}
        for i, doc in enumerate(docs):
            if '_id' in doc:
                del doc['_id']
            if 'raw_table' in doc:
                del doc['raw_table']
            if 'import_date' in doc:
                doc['import_date'] = str(doc['import_date'])  # Convert datetime to string
            
            export_data[f"table_{i}"] = doc
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"[OK] Exported {len(docs)} tables from {filename} to {output_file}")
    
    def find_by_key(self, key_name):
        """Find tables containing specific key"""
        docs = list(self.collection.find({f'key_value_pairs.{key_name}': {'$exists': True}}))
        
        print(f"\nTables with key '{key_name}' ({len(docs)} found):")
        for doc in docs:
            if key_name in doc.get('key_value_pairs', {}):
                value = doc['key_value_pairs'][key_name]
                print(f"  {doc['filename']} (Page {doc['page']}, Table {doc['table_index']})")
                print(f"    {key_name}: {value}")
    
    def find_by_value(self, search_value):
        """Find tables containing specific value"""
        docs = list(self.collection.find({'key_value_pairs': {'$regex': search_value}}))
        
        print(f"\nTables with value containing '{search_value}' ({len(docs)} found):")
        for doc in docs:
            print(f"  {doc['filename']} (Page {doc['page']}, Table {doc['table_index']})")
            # Find matching pairs
            for k, v in doc.get('key_value_pairs', {}).items():
                if search_value.lower() in str(v).lower():
                    print(f"    {k}: {v}")
    
    def close(self):
        """Close connection"""
        self.client.close()


def main():
    """Interactive CLI"""
    try:
        query = TableMappingQuery()
        
        if len(sys.argv) < 2:
            # Interactive mode
            print("\n" + "="*80)
            print("TABLE CELL MAPPING QUERY TOOL")
            print("="*80)
            
            while True:
                print("\nCommands:")
                print("  1. stats                  - Show statistics")
                print("  2. all                    - Show all tables")
                print("  3. file <filename>        - Show tables from file")
                print("  4. page <num>             - Show tables from page")
                print("  5. key <keyname>          - Find tables with key")
                print("  6. value <text>           - Find tables with value")
                print("  7. export                 - Export all to JSON")
                print("  8. export-file <fname>    - Export file to JSON")
                print("  0. exit                   - Exit")
                
                cmd = input("\nEnter command: ").strip().split(maxsplit=1)
                
                if not cmd or cmd[0] == '0' or cmd[0] == 'exit':
                    break
                elif cmd[0] == '1' or cmd[0] == 'stats':
                    query.stats()
                elif cmd[0] == '2' or cmd[0] == 'all':
                    query.show_all_tables()
                elif cmd[0] == '3' or cmd[0] == 'file':
                    if len(cmd) > 1:
                        query.show_by_filename(cmd[1])
                    else:
                        fname = input("Filename: ")
                        query.show_by_filename(fname)
                elif cmd[0] == '4' or cmd[0] == 'page':
                    if len(cmd) > 1:
                        query.show_by_page(int(cmd[1]))
                    else:
                        page = int(input("Page number: "))
                        query.show_by_page(page)
                elif cmd[0] == '5' or cmd[0] == 'key':
                    if len(cmd) > 1:
                        query.find_by_key(cmd[1])
                    else:
                        key = input("Key name: ")
                        query.find_by_key(key)
                elif cmd[0] == '6' or cmd[0] == 'value':
                    if len(cmd) > 1:
                        query.find_by_value(cmd[1])
                    else:
                        val = input("Value to search: ")
                        query.find_by_value(val)
                elif cmd[0] == '7' or cmd[0] == 'export':
                    query.export_all_as_json()
                elif cmd[0] == '8' or cmd[0] == 'export-file':
                    if len(cmd) > 1:
                        query.export_by_filename(cmd[1])
                    else:
                        fname = input("Filename: ")
                        query.export_by_filename(fname)
                else:
                    print("[ERROR] Unknown command")
        else:
            # Command line mode
            cmd = sys.argv[1]
            
            if cmd == 'stats':
                query.stats()
            elif cmd == 'all':
                query.show_all_tables()
            elif cmd == 'file' and len(sys.argv) > 2:
                query.show_by_filename(sys.argv[2])
            elif cmd == 'page' and len(sys.argv) > 2:
                query.show_by_page(int(sys.argv[2]))
            elif cmd == 'key' and len(sys.argv) > 2:
                query.find_by_key(sys.argv[2])
            elif cmd == 'value' and len(sys.argv) > 2:
                query.find_by_value(sys.argv[2])
            elif cmd == 'export':
                query.export_all_as_json()
            elif cmd == 'export-file' and len(sys.argv) > 2:
                query.export_by_filename(sys.argv[2])
            else:
                print("Usage: python query_table_mappings.py [command] [args]")
                print("\nCommands:")
                print("  stats                - Statistics")
                print("  all                  - Show all tables")
                print("  file <filename>      - Show tables from file")
                print("  page <num>           - Show tables from page")
                print("  key <keyname>        - Find tables with key")
                print("  value <text>         - Find tables with value")
                print("  export               - Export all")
                print("  export-file <fname>  - Export file")
        
        query.close()
    
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
