#!/usr/bin/env python3
"""
ERP Integration Examples - Export BOM data from MongoDB to ERP systems
Usage: python erp_export.py [format] [confidence_threshold]
"""

import json
import csv
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

try:
    from pymongo import MongoClient
except ImportError:
    print("[ERROR] pymongo not installed. Run: pip install pymongo python-dotenv")
    sys.exit(1)

load_dotenv()

class ERPExporter:
    def __init__(self, db_name="utkarshproduction", collection_name="BOMAUTOMATION"):
        """Initialize MongoDB connection"""
        mongo_uri = os.getenv("MONGO_URI")
        if not mongo_uri:
            raise ValueError("[ERROR] MONGO_URI not set in .env")
        
        self.client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]
        self.client.admin.command('ping')
    
    def get_items(self, min_confidence=0.9):
        """Get items from database"""
        return list(self.collection.find(
            {"final_confidence": {"$gte": min_confidence}},
            sort=[("final_confidence", -1)]
        ))
    
    def export_json(self, min_confidence=0.9, output_file="bom_export.json"):
        """Export to JSON format"""
        items = self.get_items(min_confidence)
        
        # Remove MongoDB _id field
        for item in items:
            if "_id" in item:
                del item["_id"]
        
        data = {
            "export_date": datetime.now().isoformat(),
            "database": "utkarshproduction",
            "collection": "BOMAUTOMATION",
            "min_confidence": min_confidence,
            "total_items": len(items),
            "items": items
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
        
        print(f"[OK] Exported {len(items)} items to {output_file}")
        return output_file
    
    def export_csv(self, min_confidence=0.9, output_file="bom_export.csv"):
        """Export to CSV format"""
        items = self.get_items(min_confidence)
        
        if not items:
            print("[WARN] No items to export")
            return None
        
        # Flatten structure for CSV
        rows = []
        for item in items:
            values_str = " | ".join([f"{v.get('type')}:{v.get('value')}" 
                                   for v in item.get('values', [])])
            
            row = {
                'text': item.get('text', ''),
                'page': item.get('page', ''),
                'source': item.get('source', ''),
                'confidence': item.get('final_confidence', 0),
                'has_values': item.get('has_values', False),
                'values': values_str,
                'bbox_x0': item.get('bbox', [0,0,0,0])[0],
                'bbox_y0': item.get('bbox', [0,0,0,0])[1],
                'bbox_x1': item.get('bbox', [0,0,0,0])[2],
                'bbox_y1': item.get('bbox', [0,0,0,0])[3],
            }
            rows.append(row)
        
        # Write CSV
        if rows:
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
        
        print(f"[OK] Exported {len(rows)} items to {output_file}")
        return output_file
    
    def export_sap_format(self, min_confidence=0.9, output_file="bom_sap.txt"):
        """Export to SAP import format"""
        items = self.get_items(min_confidence)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("*BOM Import Format\n")
            f.write(f"*Export Date: {datetime.now().isoformat()}\n")
            f.write(f"*Source: MongoDB utkarshproduction.BOMAUTOMATION\n")
            f.write(f"*Confidence Threshold: {min_confidence}\n")
            f.write("*\n")
            f.write("ITEM_NO\tDESCRIPTION\tQUANTITY\tUNIT\tCONFIDENCE\tSOURCE\n")
            
            for i, item in enumerate(items, 1):
                desc = item.get('text', '')[:100]
                qty = "1"
                unit = "PC"
                conf = item.get('final_confidence', 0)
                source = item.get('source', '')
                
                # Try to extract quantity from values
                for val in item.get('values', []):
                    if val.get('type') == 'quantity':
                        qty = str(val.get('value', 1))
                        break
                
                f.write(f"{i}\t{desc}\t{qty}\t{unit}\t{conf:.2f}\t{source}\n")
        
        print(f"[OK] Exported {len(items)} items to SAP format: {output_file}")
        return output_file
    
    def export_odoo_format(self, min_confidence=0.9, output_file="bom_odoo.csv"):
        """Export to Odoo format"""
        items = self.get_items(min_confidence)
        
        rows = []
        for item in items:
            values_str = " | ".join([f"{v.get('type')}:{v.get('value')}" 
                                   for v in item.get('values', [])])
            
            qty = 1
            for val in item.get('values', []):
                if val.get('type') == 'quantity':
                    qty = int(val.get('value', 1))
                    break
            
            row = {
                'Internal Reference': f"CAD-{item.get('filename', 'N/A').replace('.pdf', '')}-{item.get('page', 0)}",
                'Product Name': item.get('text', '')[:100],
                'Quantity': qty,
                'UoM': 'Unit(s)',
                'Confidence': f"{item.get('final_confidence', 0):.2f}",
                'Source': item.get('source', ''),
                'Specifications': values_str,
                'Notes': f"Imported from {item.get('filename', 'N/A')}, Page {item.get('page', 0)}"
            }
            rows.append(row)
        
        if rows:
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
        
        print(f"[OK] Exported {len(rows)} items to Odoo format: {output_file}")
        return output_file
    
    def export_netsuite_format(self, min_confidence=0.9, output_file="bom_netsuite.csv"):
        """Export to NetSuite format"""
        items = self.get_items(min_confidence)
        
        rows = []
        for item in items:
            row = {
                'Name': item.get('text', '')[:100],
                'Description': item.get('text', '')[:255],
                'Quantity': 1,
                'Unit Cost': '',
                'Weight': '',
                'Notes': f"Source: {item.get('source', '')}, Confidence: {item.get('final_confidence', 0):.2f}",
                'Category': 'Imported Items',
            }
            rows.append(row)
        
        if rows:
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
        
        print(f"[OK] Exported {len(rows)} items to NetSuite format: {output_file}")
        return output_file
    
    def export_json_with_values(self, min_confidence=0.9, output_file="bom_structured.json"):
        """Export as structured JSON with parsed values"""
        items = self.get_items(min_confidence)
        
        structured = []
        for item in items:
            entry = {
                "part_number": f"{item.get('page', 0)}-{item.get('text', '')[:20].replace(' ', '_')}",
                "description": item.get('text', ''),
                "quantity": 1,
                "specifications": {},
                "location": {
                    "page": item.get('page', 0),
                    "bbox": item.get('bbox', []),
                    "center": item.get('center', [])
                },
                "confidence": {
                    "score": item.get('final_confidence', 0),
                    "method": item.get('source', '')
                }
            }
            
            # Add parsed values
            for val in item.get('values', []):
                val_type = val.get('type', '').lower()
                entry["specifications"][val_type] = val.get('value', '')
            
            structured.append(entry)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({"bom": structured}, f, indent=2, default=str)
        
        print(f"[OK] Exported {len(structured)} items to structured JSON: {output_file}")
        return output_file
    
    def close(self):
        """Close connection"""
        self.client.close()


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python erp_export.py [format] [confidence]")
        print("\nFormats:")
        print("  json        - Generic JSON (default)")
        print("  csv         - Spreadsheet format")
        print("  sap         - SAP import format")
        print("  odoo        - Odoo import format")
        print("  netsuite    - NetSuite import format")
        print("  structured  - Structured JSON with specifications")
        print("  all         - Export all formats")
        print("\nExamples:")
        print("  python erp_export.py json")
        print("  python erp_export.py sap 0.95")
        print("  python erp_export.py all 0.9")
        sys.exit(1)
    
    format_type = sys.argv[1].lower()
    confidence = float(sys.argv[2]) if len(sys.argv) > 2 else 0.9
    
    try:
        exporter = ERPExporter()
        
        if format_type == 'json':
            exporter.export_json(confidence)
        elif format_type == 'csv':
            exporter.export_csv(confidence)
        elif format_type == 'sap':
            exporter.export_sap_format(confidence)
        elif format_type == 'odoo':
            exporter.export_odoo_format(confidence)
        elif format_type == 'netsuite':
            exporter.export_netsuite_format(confidence)
        elif format_type == 'structured':
            exporter.export_json_with_values(confidence)
        elif format_type == 'all':
            print("[*] Exporting all formats...\n")
            exporter.export_json(confidence)
            exporter.export_csv(confidence)
            exporter.export_json_with_values(confidence)
            exporter.export_sap_format(confidence)
            exporter.export_odoo_format(confidence)
            exporter.export_netsuite_format(confidence)
            print("[OK] All exports complete!")
        else:
            print(f"[ERROR] Unknown format: {format_type}")
            sys.exit(1)
        
        exporter.close()
    
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
