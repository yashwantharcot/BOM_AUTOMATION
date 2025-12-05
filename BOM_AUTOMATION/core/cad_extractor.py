#!/usr/bin/env python3
"""
CAD Drawing Extractor & MongoDB Mapper
Extracts vectors, text, and geometry from PDF CAD drawings
Converts to DXF format and stores structured data in MongoDB
"""

import sys
import json
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict

try:
    import pdfplumber
    import numpy as np
    from PIL import Image
    import pymongo
    from pymongo import MongoClient
except ImportError:
    print("Installing required packages...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", 
                          "pdfplumber", "numpy", "pillow", "pymongo"])
    import pdfplumber
    import numpy as np
    from PIL import Image
    import pymongo
    from pymongo import MongoClient

try:
    from dxfwrite import DXFEngine as dxf
except ImportError:
    print("Installing dxfwrite...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "dxfwrite"])
    from dxfwrite import DXFEngine as dxf


class CADExtractor:
    """Extract geometry and text from CAD PDFs"""
    
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.data = {
            'source_file': str(pdf_path),
            'extraction_date': datetime.now().isoformat(),
            'pages': [],
            'text_blocks': [],
            'geometries': [],
            'dimensions': [],
            'annotations': [],
            'metadata': {}
        }
    
    def extract_metadata(self):
        """Extract PDF metadata and drawing information"""
        with pdfplumber.open(self.pdf_path) as pdf:
            # Get PDF info
            if pdf.metadata:
                self.data['metadata'] = {
                    'title': pdf.metadata.get('Title', ''),
                    'author': pdf.metadata.get('Author', ''),
                    'subject': pdf.metadata.get('Subject', ''),
                    'created': str(pdf.metadata.get('CreationDate', '')),
                    'modified': str(pdf.metadata.get('ModDate', ''))
                }
            
            # Extract key information from text
            full_text = ""
            for page in pdf.pages:
                full_text += page.extract_text() or ""
            
            # Extract common CAD fields
            self.data['metadata'].update(self._extract_cad_fields(full_text))
        
        return self.data['metadata']
    
    def _extract_cad_fields(self, text):
        """Extract common CAD drawing fields"""
        fields = {}
        
        # Item number
        item_match = re.search(r'Item\s*(?:no|number)[.:]\s*(\d+)', text, re.IGNORECASE)
        if item_match:
            fields['item_number'] = item_match.group(1)
        
        # Material
        material_match = re.search(r'Material[:\s]+([A-Za-z0-9\-+ \.]+?)(?:\n|Scale|Form)', text, re.IGNORECASE)
        if material_match:
            fields['material'] = material_match.group(1).strip()
        
        # Scale
        scale_match = re.search(r'Scale[:\s]+([\d:\.]+)', text, re.IGNORECASE)
        if scale_match:
            fields['scale'] = scale_match.group(1)
        
        # Tolerance
        tolerance_match = re.search(r'Tolerances?\s+(?:acc\.|according)\s+to[:\s]+([A-Za-z0-9\s\-\.]+?)(?:\n|All)', text, re.IGNORECASE)
        if tolerance_match:
            fields['tolerance_standard'] = tolerance_match.group(1).strip()
        
        # Part description
        desc_match = re.search(r'(?:description|Description)[:\s]+([A-Za-z0-9\s\-,\.]+?)(?:\n|Scale|Material)', text, re.IGNORECASE)
        if desc_match:
            fields['description'] = desc_match.group(1).strip()
        
        # Dimensions in mm
        dim_matches = re.findall(r'(\d+(?:\.\d+)?)\s*(?:mm|Ø|×|x)', text)
        if dim_matches:
            fields['dimensions_found'] = dim_matches[:10]  # Top 10 dimensions
        
        # Date created
        date_match = re.search(r'(?:Created|Date)[:\s]+(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})', text)
        if date_match:
            fields['created_date'] = date_match.group(1)
        
        # Form/Standard references
        form_matches = re.findall(r'Form\s+(?:acc\.|according)\s+to\s+([A-Z]+)', text)
        if form_matches:
            fields['form_standards'] = list(set(form_matches))
        
        return fields
    
    def extract_geometry(self):
        """Extract geometric elements from PDF"""
        with pdfplumber.open(self.pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                page_data = {
                    'page': page_num,
                    'width': page.width,
                    'height': page.height,
                    'elements': []
                }
                
                # Extract rectangles
                for rect in page.rects:
                    page_data['elements'].append({
                        'type': 'rectangle',
                        'x0': rect['x0'],
                        'y0': rect['y0'],
                        'x1': rect['x1'],
                        'y1': rect['y1'],
                        'width': rect['x1'] - rect['x0'],
                        'height': rect['y1'] - rect['y0'],
                        'linewidth': rect.get('linewidth', 1)
                    })
                
                # Extract lines
                for line in page.lines[:500]:  # Limit to first 500 lines
                    page_data['elements'].append({
                        'type': 'line',
                        'x0': line['x0'],
                        'y0': line['y0'],
                        'x1': line['x1'],
                        'y1': line['y1'],
                        'length': np.sqrt((line['x1']-line['x0'])**2 + (line['y1']-line['y0'])**2),
                        'linewidth': line.get('linewidth', 1)
                    })
                
                # Extract curves
                for i, curve in enumerate(page.curves[:200]):  # Limit to first 200 curves
                    page_data['elements'].append({
                        'type': 'curve',
                        'points': len(curve),
                        'linewidth': curve.get('linewidth', 1)
                    })
                
                self.data['pages'].append(page_data)
        
        return self.data['pages']
    
    def extract_text_blocks(self):
        """Extract text and associate with positions"""
        with pdfplumber.open(self.pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                # Extract text with position info
                for char in page.chars:
                    self.data['text_blocks'].append({
                        'page': page_num,
                        'text': char['text'],
                        'x': char['x0'],
                        'y': char['y0'],
                        'size': char['size'],
                        'font': char.get('font', 'unknown'),
                        'matrix': char.get('matrix', [])
                    })
        
        return self.data['text_blocks']
    
    def extract_dimensions(self):
        """Extract dimension values and callouts"""
        with pdfplumber.open(self.pdf_path) as pdf:
            all_text = ""
            for page in pdf.pages:
                all_text += page.extract_text() or ""
        
        # Find dimensions (numbers with units)
        dimension_patterns = [
            (r'(\d+(?:\.\d+)?)\s*(?:mm|Ø)', 'length_mm'),
            (r'(\d+(?:\.\d+)?)\s*×\s*(\d+(?:\.\d+)?)', 'cross_product'),
            (r'(\d+)\s*x\s*(\d+)', 'product'),
            (r'±\s*(\d+(?:\.\d+)?)', 'tolerance'),
        ]
        
        for pattern, dim_type in dimension_patterns:
            matches = re.finditer(pattern, all_text, re.IGNORECASE)
            for match in matches:
                self.data['dimensions'].append({
                    'type': dim_type,
                    'value': match.group(1),
                    'full_match': match.group(0),
                    'position': match.span()
                })
        
        return self.data['dimensions']
    
    def extract_annotations(self):
        """Extract annotations, notes, and callouts"""
        with pdfplumber.open(self.pdf_path) as pdf:
            all_text = ""
            for page in pdf.pages:
                all_text += page.extract_text() or ""
        
        # Split by common section markers
        lines = all_text.split('\n')
        current_section = None
        current_content = []
        
        section_keywords = ['note', 'warning', 'caution', 'item', 'material', 'tolerance', 'form', 'specification']
        
        for line in lines:
            line_lower = line.lower()
            # Check if this is a section header
            if any(keyword in line_lower for keyword in section_keywords):
                if current_section:
                    self.data['annotations'].append({
                        'section': current_section,
                        'content': '\n'.join(current_content).strip()
                    })
                current_section = line.strip()
                current_content = []
            else:
                if line.strip():
                    current_content.append(line)
        
        # Add last section
        if current_section:
            self.data['annotations'].append({
                'section': current_section,
                'content': '\n'.join(current_content).strip()
            })
        
        return self.data['annotations']
    
    def extract_all(self):
        """Run all extraction methods"""
        print("\n" + "="*60)
        print("CAD DRAWING EXTRACTION")
        print("="*60)
        
        print("\n[1/5] Extracting metadata...")
        self.extract_metadata()
        print(f"      ✓ Found: {len(self.data['metadata'])} metadata fields")
        
        print("[2/5] Extracting geometry...")
        self.extract_geometry()
        print(f"      ✓ Found: {sum(len(p['elements']) for p in self.data['pages'])} geometric elements")
        
        print("[3/5] Extracting text blocks...")
        self.extract_text_blocks()
        print(f"      ✓ Found: {len(self.data['text_blocks'])} text elements")
        
        print("[4/5] Extracting dimensions...")
        self.extract_dimensions()
        print(f"      ✓ Found: {len(self.data['dimensions'])} dimension values")
        
        print("[5/5] Extracting annotations...")
        self.extract_annotations()
        print(f"      ✓ Found: {len(self.data['annotations'])} annotation sections")
        
        return self.data


class DXFExporter:
    """Export extracted data to DXF format"""
    
    @staticmethod
    def export(data, output_path):
        """Export geometry data to DXF"""
        drawing = dxf.DXFEngine.create(str(output_path))
        
        # Add layers
        drawing.add_layer('GEOMETRY', color=7)
        drawing.add_layer('TEXT', color=1)
        drawing.add_layer('DIMENSIONS', color=3)
        drawing.add_layer('ANNOTATIONS', color=5)
        
        # Export geometric elements
        for page in data['pages']:
            for elem in page['elements']:
                if elem['type'] == 'rectangle':
                    drawing.add(dxf.rectangle(
                        (elem['x0'], elem['y0']),
                        elem['width'],
                        elem['height'],
                        layer='GEOMETRY'
                    ))
                elif elem['type'] == 'line':
                    drawing.add(dxf.line(
                        (elem['x0'], elem['y0']),
                        (elem['x1'], elem['y1']),
                        layer='GEOMETRY'
                    ))
        
        # Export text
        for text_block in data['text_blocks'][:100]:  # First 100 text elements
            try:
                drawing.add(dxf.text(
                    text_block['text'],
                    point=(text_block['x'], text_block['y']),
                    height=text_block['size'],
                    layer='TEXT'
                ))
            except:
                pass
        
        drawing.save()
        return output_path


class MongoDBMapper:
    """Map extracted data to MongoDB"""
    
    def __init__(self, connection_string="mongodb://localhost:27017/"):
        self.client = None
        self.db = None
        self.connection_string = connection_string
    
    def connect(self, database_name="cad_drawings"):
        """Connect to MongoDB"""
        try:
            self.client = MongoClient(self.connection_string, serverSelectionTimeoutMS=5000)
            self.client.admin.command('ping')
            self.db = self.client[database_name]
            print(f"✓ Connected to MongoDB: {database_name}")
            return True
        except Exception as e:
            print(f"✗ MongoDB connection failed: {e}")
            print("  Note: Ensure MongoDB is running. Use: mongod --dbpath C:\\data\\db")
            return False
    
    def store_drawing(self, data):
        """Store extracted drawing data in MongoDB"""
        if not self.db:
            print("Not connected to MongoDB")
            return None
        
        drawing_collection = self.db['drawings']
        
        # Prepare document
        doc = {
            'source_file': data['source_file'],
            'extraction_date': data['extraction_date'],
            'metadata': data['metadata'],
            'geometry_summary': {
                'total_pages': len(data['pages']),
                'total_elements': sum(len(p['elements']) for p in data['pages']),
                'rectangles': sum(1 for p in data['pages'] for e in p['elements'] if e['type'] == 'rectangle'),
                'lines': sum(1 for p in data['pages'] for e in p['elements'] if e['type'] == 'line'),
                'curves': sum(1 for p in data['pages'] for e in p['elements'] if e['type'] == 'curve'),
            },
            'dimensions': data['dimensions'],
            'text_elements': len(data['text_blocks']),
            'annotations': data['annotations']
        }
        
        # Insert and get ID
        result = drawing_collection.insert_one(doc)
        print(f"\n✓ Drawing stored in MongoDB with ID: {result.inserted_id}")
        
        # Store geometric elements
        if data['pages']:
            geometry_collection = self.db['geometries']
            geometry_docs = []
            for page in data['pages']:
                for elem in page['elements']:
                    elem['drawing_id'] = result.inserted_id
                    elem['page'] = page['page']
                    geometry_docs.append(elem)
            if geometry_docs:
                geometry_collection.insert_many(geometry_docs)
                print(f"✓ Stored {len(geometry_docs)} geometric elements")
        
        # Store text blocks
        if data['text_blocks']:
            text_collection = self.db['text_elements']
            text_docs = [{'drawing_id': result.inserted_id, **tb} for tb in data['text_blocks']]
            text_collection.insert_many(text_docs)
            print(f"✓ Stored {len(text_docs)} text elements")
        
        return result.inserted_id
    
    def query_by_material(self, material):
        """Query drawings by material"""
        if not self.db:
            return []
        collection = self.db['drawings']
        return list(collection.find({'metadata.material': {'$regex': material, '$options': 'i'}}))
    
    def query_by_item_number(self, item_no):
        """Query drawings by item number"""
        if not self.db:
            return []
        collection = self.db['drawings']
        return list(collection.find({'metadata.item_number': str(item_no)}))
    
    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()


def main():
    if len(sys.argv) < 2:
        print("Usage: python cad_extractor.py <pdf_path> [--export-dxf] [--mongodb]")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    export_dxf = '--export-dxf' in sys.argv
    use_mongodb = '--mongodb' in sys.argv
    
    if not Path(pdf_path).exists():
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)
    
    # Extract data
    extractor = CADExtractor(pdf_path)
    data = extractor.extract_all()
    
    # Save JSON
    json_path = Path(pdf_path).stem + "_extracted.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, default=str)
    print(f"\n✓ Saved extracted data to: {json_path}")
    
    # Export to DXF
    if export_dxf:
        dxf_path = Path(pdf_path).stem + "_converted.dxf"
        try:
            DXFExporter.export(data, dxf_path)
            print(f"✓ Exported to DXF: {dxf_path}")
        except Exception as e:
            print(f"✗ DXF export failed: {e}")
    
    # Store in MongoDB
    if use_mongodb:
        mapper = MongoDBMapper()
        if mapper.connect():
            mapper.store_drawing(data)
            mapper.close()
    
    # Display summary
    print("\n" + "="*60)
    print("EXTRACTION SUMMARY")
    print("="*60)
    print(f"Material: {data['metadata'].get('material', 'N/A')}")
    print(f"Description: {data['metadata'].get('description', 'N/A')}")
    print(f"Scale: {data['metadata'].get('scale', 'N/A')}")
    print(f"Item Number: {data['metadata'].get('item_number', 'N/A')}")
    print(f"Dimensions Found: {len(data['dimensions'])}")
    print(f"Total Annotations: {len(data['annotations'])}")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
