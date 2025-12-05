#!/usr/bin/env python3
"""
MongoDB Query Utility - Work with extracted BOM data
Usage: python query_bom.py [command] [options]
"""

import json
import sys
import os
from dotenv import load_dotenv
from datetime import datetime

try:
    from pymongo import MongoClient
except ImportError:
    print("[ERROR] pymongo not installed. Run: pip install pymongo python-dotenv")
    sys.exit(1)

load_dotenv()

class BOMQuery:
    def __init__(self, db_name="utkarshproduction", collection_name="BOMAUTOMATION"):
        """Initialize MongoDB connection"""
        mongo_uri = os.getenv("MONGO_URI")
        if not mongo_uri:
            raise ValueError("[ERROR] MONGO_URI not set in .env")
        
        self.client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]
        
        # Test connection
        self.client.admin.command('ping')
        print(f"[OK] Connected to {db_name}.{collection_name}")
    
    def stats(self):
        """Show collection statistics"""
        count = self.collection.count_documents({})
        print(f"\nTotal Documents: {count}")
        
        high = self.collection.count_documents({"final_confidence": {"$gte": 0.9}})
        medium = self.collection.count_documents({"final_confidence": {"$gte": 0.7, "$lt": 0.9}})
        low = self.collection.count_documents({"final_confidence": {"$lt": 0.7}})
        
        print(f"\nConfidence Distribution:")
        print(f"  High (≥0.9): {high} ({high/count*100:.1f}%)")
        print(f"  Medium (0.7-0.9): {medium} ({medium/count*100:.1f}%)")
        print(f"  Low (<0.7): {low} ({low/count*100:.1f}%)")
        
        vector = self.collection.count_documents({"source": "vector"})
        ocr = self.collection.count_documents({"source": "ocr"})
        
        print(f"\nSource Distribution:")
        print(f"  Vector: {vector} ({vector/count*100:.1f}%)")
        print(f"  OCR: {ocr} ({ocr/count*100:.1f}%)")
        
        with_values = self.collection.count_documents({"has_values": True})
        print(f"\nItems with Values: {with_values} ({with_values/count*100:.1f}%)")
    
    def find_text(self, search_text, limit=10):
        """Search for text"""
        results = list(self.collection.find(
            {"text": {"$regex": search_text, "$options": "i"}},
            limit=limit
        ))
        
        print(f"\nFound {len(results)} items matching '{search_text}':")
        for i, doc in enumerate(results, 1):
            text = doc.get('text', '')[:60]
            conf = doc.get('final_confidence', 0)
            print(f"  {i}. {text}... [confidence: {conf:.2f}]")
    
    def find_high_confidence(self, limit=20):
        """Find high confidence items"""
        results = list(self.collection.find(
            {"final_confidence": {"$gte": 0.9}},
            sort=[("final_confidence", -1)],
            limit=limit
        ))
        
        print(f"\nTop {len(results)} High-Confidence Items:")
        for i, doc in enumerate(results, 1):
            text = doc.get('text', '')[:50]
            conf = doc.get('final_confidence', 0)
            source = doc.get('source', '')
            values = doc.get('values', [])
            
            if values:
                val_str = f" [values: {values}]"
            else:
                val_str = ""
            
            print(f"  {i}. {text}... [{source}:{conf:.2f}]{val_str}")
    
    def find_with_values(self, limit=20):
        """Find items with parsed values"""
        results = list(self.collection.find(
            {"has_values": True},
            sort=[("final_confidence", -1)],
            limit=limit
        ))
        
        print(f"\nItems with Parsed Values ({len(results)} found):")
        for i, doc in enumerate(results, 1):
            text = doc.get('text', '')
            values = doc.get('values', [])
            conf = doc.get('final_confidence', 0)
            
            val_list = ", ".join([f"{v['type']}:{v['value']}" for v in values])
            print(f"  {i}. {text}")
            print(f"     → {val_list} [confidence: {conf:.2f}]")
    
    def export_by_confidence(self, min_confidence=0.9, output_file="export.json"):
        """Export items above confidence threshold"""
        results = list(self.collection.find(
            {"final_confidence": {"$gte": min_confidence}},
            sort=[("final_confidence", -1)]
        ))
        
        data = {
            "export_date": datetime.utcnow().isoformat(),
            "min_confidence": min_confidence,
            "count": len(results),
            "items": results
        }
        
        # Remove MongoDB _id field
        for item in data["items"]:
            if "_id" in item:
                del item["_id"]
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
        
        print(f"[OK] Exported {len(results)} items to {output_file}")
    
    def find_by_page(self, page_num, limit=100):
        """Find items from specific page"""
        results = list(self.collection.find(
            {"page": page_num},
            limit=limit
        ))
        
        print(f"\nPage {page_num}: {len(results)} items")
        for i, doc in enumerate(results, 1):
            text = doc.get('text', '')[:50]
            conf = doc.get('final_confidence', 0)
            print(f"  {i}. {text}... [{conf:.2f}]")
    
    def find_low_confidence(self, max_confidence=0.75, limit=20):
        """Find low confidence items for review"""
        results = list(self.collection.find(
            {"final_confidence": {"$lt": max_confidence}},
            sort=[("final_confidence", 1)],
            limit=limit
        ))
        
        print(f"\nLow-Confidence Items for Review ({len(results)} found):")
        for i, doc in enumerate(results, 1):
            text = doc.get('text', '')[:60]
            conf = doc.get('final_confidence', 0)
            source = doc.get('source', '')
            
            print(f"  {i}. {text}... [{source}:{conf:.2f}] ⚠️ REVIEW")
    
    def get_collection_info(self):
        """Get detailed collection information"""
        stats = self.db.command('collStats', 'BOMAUTOMATION')
        
        print(f"\nCollection: BOMAUTOMATION")
        print(f"Documents: {stats.get('count', 0)}")
        print(f"Size: {stats.get('size', 0) / 1024 / 1024:.2f} MB")
        print(f"Average Document Size: {stats.get('avgObjSize', 0) / 1024:.2f} KB")
        print(f"Indexes: {len(stats.get('indexSizes', {}))}")
    
    def close(self):
        """Close connection"""
        self.client.close()


def main():
    """Interactive CLI"""
    try:
        query = BOMQuery()
        
        if len(sys.argv) < 2:
            # Interactive mode
            print("\n" + "="*70)
            print("MONGODB BOM QUERY UTILITY")
            print("="*70)
            
            while True:
                print("\nCommands:")
                print("  1. stats              - Show collection statistics")
                print("  2. high               - Show high-confidence items")
                print("  3. values             - Show items with values")
                print("  4. low                - Show low-confidence items")
                print("  5. search <text>      - Search for text")
                print("  6. page <num>         - Show items from page")
                print("  7. export [conf]      - Export items (default 0.9)")
                print("  8. info               - Collection information")
                print("  0. exit               - Exit")
                
                cmd = input("\nEnter command: ").strip().lower().split()
                
                if not cmd or cmd[0] == '0' or cmd[0] == 'exit':
                    break
                elif cmd[0] == '1' or cmd[0] == 'stats':
                    query.stats()
                elif cmd[0] == '2' or cmd[0] == 'high':
                    query.find_high_confidence()
                elif cmd[0] == '3' or cmd[0] == 'values':
                    query.find_with_values()
                elif cmd[0] == '4' or cmd[0] == 'low':
                    query.find_low_confidence()
                elif cmd[0] == '5' or cmd[0] == 'search':
                    text = input("Search text: ")
                    query.find_text(text)
                elif cmd[0] == '6' or cmd[0] == 'page':
                    page = int(input("Page number: "))
                    query.find_by_page(page)
                elif cmd[0] == '7' or cmd[0] == 'export':
                    conf = float(cmd[1]) if len(cmd) > 1 else 0.9
                    query.export_by_confidence(conf)
                elif cmd[0] == '8' or cmd[0] == 'info':
                    query.get_collection_info()
                else:
                    print("[ERROR] Unknown command")
        else:
            # Command line mode
            cmd = sys.argv[1]
            
            if cmd == 'stats':
                query.stats()
            elif cmd == 'high':
                query.find_high_confidence()
            elif cmd == 'values':
                query.find_with_values()
            elif cmd == 'low':
                query.find_low_confidence()
            elif cmd == 'search' and len(sys.argv) > 2:
                query.find_text(sys.argv[2])
            elif cmd == 'page' and len(sys.argv) > 2:
                query.find_by_page(int(sys.argv[2]))
            elif cmd == 'export':
                conf = float(sys.argv[2]) if len(sys.argv) > 2 else 0.9
                query.export_by_confidence(conf)
            elif cmd == 'info':
                query.get_collection_info()
            else:
                print("Usage: python query_bom.py [command] [options]")
                print("\nCommands:")
                print("  stats              - Show statistics")
                print("  high               - High-confidence items")
                print("  values             - Items with values")
                print("  low                - Low-confidence items")
                print("  search <text>      - Search for text")
                print("  page <num>         - Items from page")
                print("  export [conf]      - Export items")
                print("  info               - Collection info")
        
        query.close()
    
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
