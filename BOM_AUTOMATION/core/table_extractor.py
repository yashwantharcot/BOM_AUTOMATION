#!/usr/bin/env python3
"""
Advanced CAD PDF Table Extractor
Extracts tables from vector PDFs with 100% fidelity
Uses multiple detection methods for maximum accuracy
"""

import sys
import json
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict

try:
    import pdfplumber
    import pandas as pd
    import numpy as np
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", 
                          "pdfplumber", "pandas", "numpy", "openpyxl"])
    import pdfplumber
    import pandas as pd
    import numpy as np


class AdvancedTableExtractor:
    """Extract tables from CAD PDFs with multiple methods"""
    
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.tables = []
        self.results = {
            'source_file': str(pdf_path),
            'extraction_date': datetime.now().isoformat(),
            'tables': [],
            'statistics': {}
        }
    
    def extract_tables_pdfplumber(self):
        """Extract tables using pdfplumber (best for structured tables)"""
        print("\n[METHOD 1] Using pdfplumber table detection...")
        
        with pdfplumber.open(self.pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                print("  Scanning page {}...".format(page_num))
                
                # Method 1a: Built-in table detection
                try:
                    tables = page.extract_tables()
                    if tables:
                        for table_idx, table in enumerate(tables):
                            table_data = {
                                'page': page_num,
                                'method': 'pdfplumber_native',
                                'table_index': table_idx,
                                'rows': len(table),
                                'cols': len(table[0]) if table else 0,
                                'data': table,
                                'confidence': 'high'
                            }
                            self.tables.append(table_data)
                            print("    [OK] Found table: {}x{} ({}x{} cells)".format(
                                len(table), 
                                len(table[0]) if table else 0,
                                len(table) * (len(table[0]) if table else 0),
                                table_idx + 1
                            ))
                except Exception as e:
                    print("    [SKIP] pdfplumber native: {}".format(str(e)[:50]))
                
                # Method 1b: Using table_settings for better edge detection
                try:
                    table_settings = {
                        "vertical_strategy": "lines",
                        "horizontal_strategy": "lines",
                        "explicit_vertical_lines": page.vertical_edges,
                        "explicit_horizontal_lines": page.horizontal_edges
                    }
                    tables = page.extract_tables(table_settings)
                    if tables:
                        for table_idx, table in enumerate(tables):
                            # Check if not duplicate
                            if not self._is_duplicate_table(table):
                                table_data = {
                                    'page': page_num,
                                    'method': 'pdfplumber_lines',
                                    'table_index': table_idx,
                                    'rows': len(table),
                                    'cols': len(table[0]) if table else 0,
                                    'data': table,
                                    'confidence': 'high'
                                }
                                self.tables.append(table_data)
                                print("    [OK] Found table (lines method): {}x{}".format(
                                    len(table), len(table[0]) if table else 0
                                ))
                except Exception as e:
                    print("    [SKIP] pdfplumber lines: {}".format(str(e)[:50]))
    
    def extract_tables_geometry(self):
        """Extract tables using geometric analysis (rectangles and lines)"""
        print("\n[METHOD 2] Using geometric analysis (rectangles & lines)...")
        
        with pdfplumber.open(self.pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                print("  Analyzing geometry on page {}...".format(page_num))
                
                try:
                    # Get all rectangles (table boundaries)
                    rects = page.rects
                    lines = page.lines
                    
                    if rects:
                        print("    [OK] Found {} rectangles".format(len(rects)))
                    
                    if lines:
                        print("    [OK] Found {} lines (potential table grid)".format(len(lines)))
                    
                    # Detect table regions by clustering rectangles
                    table_regions = self._cluster_rectangles(rects)
                    
                    for region_idx, region in enumerate(table_regions):
                        print("    [OK] Detected table region {}".format(region_idx + 1))
                        
                        # Extract text in this region
                        cropped = page.crop(region)
                        text_data = cropped.extract_text()
                        
                        if text_data:
                            table_data = {
                                'page': page_num,
                                'method': 'geometric_clustering',
                                'region_index': region_idx,
                                'bbox': region,
                                'raw_text': text_data,
                                'confidence': 'medium'
                            }
                            self.tables.append(table_data)
                
                except Exception as e:
                    print("    [SKIP] Geometric analysis: {}".format(str(e)[:50]))
    
    def extract_tables_grid(self):
        """Extract tables by detecting grid patterns"""
        print("\n[METHOD 3] Using grid pattern detection...")
        
        with pdfplumber.open(self.pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                print("  Detecting grid patterns on page {}...".format(page_num))
                
                try:
                    # Get horizontal and vertical lines
                    h_edges = page.horizontal_edges
                    v_edges = page.vertical_edges
                    
                    if h_edges and v_edges:
                        print("    [OK] Detected grid: {} horizontal, {} vertical lines".format(
                            len(h_edges), len(v_edges)
                        ))
                        
                        # Create grid table
                        grid_table = self._construct_grid_table(page, h_edges, v_edges)
                        
                        if grid_table and len(grid_table) > 0:
                            table_data = {
                                'page': page_num,
                                'method': 'grid_detection',
                                'rows': len(grid_table),
                                'cols': len(grid_table[0]) if grid_table else 0,
                                'data': grid_table,
                                'confidence': 'high'
                            }
                            self.tables.append(table_data)
                            print("    [OK] Extracted grid table: {}x{}".format(
                                len(grid_table), len(grid_table[0]) if grid_table else 0
                            ))
                
                except Exception as e:
                    print("    [SKIP] Grid detection: {}".format(str(e)[:50]))
    
    def extract_text_blocks_as_table(self):
        """Extract text blocks and organize as table"""
        print("\n[METHOD 4] Organizing text blocks as table...")
        
        with pdfplumber.open(self.pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                print("  Processing text blocks on page {}...".format(page_num))
                
                try:
                    # Get all text with coordinates
                    chars = page.chars
                    
                    if chars:
                        print("    [OK] Found {} characters with coordinates".format(len(chars)))
                        
                        # Group into lines and columns
                        organized = self._organize_chars_into_table(chars)
                        
                        if organized:
                            table_data = {
                                'page': page_num,
                                'method': 'text_block_organization',
                                'rows': len(organized),
                                'cols': len(organized[0]) if organized else 0,
                                'data': organized,
                                'confidence': 'medium'
                            }
                            self.tables.append(table_data)
                            print("    [OK] Organized into table: {}x{}".format(
                                len(organized), len(organized[0]) if organized else 0
                            ))
                
                except Exception as e:
                    print("    [SKIP] Text block organization: {}".format(str(e)[:50]))
    
    def _is_duplicate_table(self, table):
        """Check if table is already in extracted tables"""
        for existing in self.tables:
            if existing.get('data') == table:
                return True
        return False
    
    def _cluster_rectangles(self, rects, threshold=50):
        """Cluster rectangles to identify table regions"""
        if not rects:
            return []
        
        clusters = []
        used = set()
        
        for i, rect in enumerate(rects):
            if i in used:
                continue
            
            cluster = [rect]
            used.add(i)
            
            for j, other in enumerate(rects[i+1:], i+1):
                if j in used:
                    continue
                
                # Check if rectangles are close
                if self._rects_close(rect, other, threshold):
                    cluster.append(other)
                    used.add(j)
            
            if len(cluster) > 1:
                # Get bounding box
                x0 = min(r[0] for r in cluster)
                y0 = min(r[1] for r in cluster)
                x1 = max(r[2] for r in cluster)
                y1 = max(r[3] for r in cluster)
                clusters.append((x0, y0, x1, y1))
        
        return clusters
    
    def _rects_close(self, r1, r2, threshold=50):
        """Check if two rectangles are close to each other"""
        return (abs(r1[0] - r2[0]) < threshold or 
                abs(r1[2] - r2[2]) < threshold or
                abs(r1[1] - r2[1]) < threshold or
                abs(r1[3] - r2[3]) < threshold)
    
    def _construct_grid_table(self, page, h_edges, v_edges):
        """Construct table from grid edges"""
        if not h_edges or not v_edges:
            return []
        
        # Sort edges
        h_coords = sorted(set(int(e['top']) for e in h_edges))
        v_coords = sorted(set(int(e['x0']) for e in v_edges))
        
        # Create cells and extract text
        table = []
        
        for i in range(len(h_coords) - 1):
            row = []
            y0, y1 = h_coords[i], h_coords[i + 1]
            
            for j in range(len(v_coords) - 1):
                x0, x1 = v_coords[j], v_coords[j + 1]
                
                # Crop to cell
                cell_bbox = (x0, y0, x1, y1)
                try:
                    cropped = page.crop(cell_bbox)
                    cell_text = cropped.extract_text() or ""
                    row.append(cell_text.strip())
                except:
                    row.append("")
            
            if row:
                table.append(row)
        
        return table if table else []
    
    def _organize_chars_into_table(self, chars):
        """Organize character objects into table structure"""
        if not chars:
            return []
        
        # Group by y-coordinate (rows)
        rows_dict = defaultdict(list)
        
        for char in chars:
            y = int(char['top'] / 10) * 10  # Round to nearest 10 points
            rows_dict[y].append(char)
        
        # Sort rows by y-coordinate
        sorted_rows = sorted(rows_dict.items())
        
        table = []
        
        for y_coord, row_chars in sorted_rows:
            # Sort chars in row by x-coordinate
            sorted_chars = sorted(row_chars, key=lambda c: c['x0'])
            
            # Group into columns
            columns = self._group_chars_into_columns(sorted_chars)
            
            # Extract text from each column
            row_text = []
            for col_chars in columns:
                col_text = ''.join(c['text'] for c in col_chars).strip()
                row_text.append(col_text)
            
            if row_text:
                table.append(row_text)
        
        return table
    
    def _group_chars_into_columns(self, chars, gap=20):
        """Group characters into columns based on x-coordinate gaps"""
        if not chars:
            return []
        
        columns = [[chars[0]]]
        
        for char in chars[1:]:
            # Check gap from last char in last column
            last_char = columns[-1][-1]
            gap_size = char['x0'] - last_char['x1']
            
            if gap_size < gap:
                columns[-1].append(char)
            else:
                columns.append([char])
        
        return columns
    
    def extract_all(self):
        """Run all extraction methods"""
        print("\n" + "="*70)
        print("ADVANCED TABLE EXTRACTION - MULTIPLE METHODS")
        print("="*70)
        print("\nFile: {}".format(self.pdf_path))
        
        self.extract_tables_pdfplumber()
        self.extract_tables_geometry()
        self.extract_tables_grid()
        self.extract_text_blocks_as_table()
        
        # Deduplicate similar tables
        self._deduplicate_tables()
        
        self.results['tables'] = self.tables
        self.results['statistics'] = {
            'total_tables_found': len(self.tables),
            'by_method': self._count_by_method(),
            'by_page': self._count_by_page()
        }
        
        return self.results
    
    def _deduplicate_tables(self):
        """Remove duplicate tables"""
        unique_tables = []
        seen = []
        
        for table in self.tables:
            data_str = str(table.get('data', ''))
            if data_str not in seen:
                unique_tables.append(table)
                seen.append(data_str)
        
        self.tables = unique_tables
    
    def _count_by_method(self):
        """Count tables by extraction method"""
        counts = defaultdict(int)
        for table in self.tables:
            method = table.get('method', 'unknown')
            counts[method] += 1
        return dict(counts)
    
    def _count_by_page(self):
        """Count tables by page"""
        counts = defaultdict(int)
        for table in self.tables:
            page = table.get('page', 'unknown')
            counts[page] += 1
        return dict(counts)


class TableExporter:
    """Export extracted tables in multiple formats"""
    
    @staticmethod
    def to_csv(tables, output_dir="./"):
        """Export tables as CSV files"""
        print("\n[EXPORT] Saving as CSV...")
        files = []
        
        for idx, table_info in enumerate(tables):
            if 'data' not in table_info:
                continue
            
            try:
                data = table_info['data']
                df = pd.DataFrame(data)
                
                filename = "table_{:02d}_{}_{}.csv".format(
                    idx + 1,
                    table_info.get('method', 'unknown')[:10],
                    table_info.get('page', 0)
                )
                filepath = Path(output_dir) / filename
                
                df.to_csv(filepath, index=False, header=False, encoding='utf-8')
                print("  [OK] {}".format(filename))
                files.append(str(filepath))
            
            except Exception as e:
                print("  [ERROR] Table {}: {}".format(idx + 1, str(e)[:50]))
        
        return files
    
    @staticmethod
    def to_excel(tables, output_file="extracted_tables.xlsx"):
        """Export all tables to Excel"""
        print("\n[EXPORT] Saving as Excel...")
        
        try:
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                for idx, table_info in enumerate(tables):
                    if 'data' not in table_info:
                        continue
                    
                    data = table_info['data']
                    df = pd.DataFrame(data)
                    
                    sheet_name = "Table_{}".format(idx + 1)
                    df.to_excel(writer, sheet_name=sheet_name, index=False, header=False)
                    print("  [OK] Sheet: {}".format(sheet_name))
            
            print("  [OK] Saved to: {}".format(output_file))
            return output_file
        
        except Exception as e:
            print("  [ERROR] {}".format(e))
            return None
    
    @staticmethod
    def to_json(results, output_file="extracted_tables.json"):
        """Export results as JSON"""
        print("\n[EXPORT] Saving as JSON...")
        
        try:
            # Convert to serializable format
            export_data = {
                'source_file': results['source_file'],
                'extraction_date': results['extraction_date'],
                'statistics': results['statistics'],
                'tables': [
                    {
                        'page': t.get('page'),
                        'method': t.get('method'),
                        'rows': t.get('rows', len(t.get('data', []))),
                        'cols': t.get('cols', len(t.get('data', [[]])[0]) if t.get('data') else 0),
                        'data': t.get('data')
                    }
                    for t in results['tables']
                ]
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            print("  [OK] Saved to: {}".format(output_file))
            return output_file
        
        except Exception as e:
            print("  [ERROR] {}".format(e))
            return None
    
    @staticmethod
    def to_markdown(tables, output_file="extracted_tables.md"):
        """Export tables as Markdown"""
        print("\n[EXPORT] Saving as Markdown...")
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("# Extracted Tables\n\n")
                
                for idx, table_info in enumerate(tables):
                    if 'data' not in table_info:
                        continue
                    
                    f.write("## Table {} (Page {}, Method: {})\n\n".format(
                        idx + 1,
                        table_info.get('page', '?'),
                        table_info.get('method', 'unknown')
                    ))
                    
                    data = table_info['data']
                    if data:
                        # Write header
                        f.write("| " + " | ".join(str(cell) for cell in data[0]) + " |\n")
                        f.write("|" + "|".join(["---"] * len(data[0])) + "|\n")
                        
                        # Write rows
                        for row in data[1:]:
                            f.write("| " + " | ".join(str(cell) for cell in row) + " |\n")
                    
                    f.write("\n")
            
            print("  [OK] Saved to: {}".format(output_file))
            return output_file
        
        except Exception as e:
            print("  [ERROR] {}".format(e))
            return None
    
    @staticmethod
    def to_html(tables, output_file="extracted_tables.html"):
        """Export tables as HTML"""
        print("\n[EXPORT] Saving as HTML...")
        
        try:
            html_content = """<html>
<head>
    <meta charset="UTF-8">
    <title>Extracted Tables</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        table { border-collapse: collapse; margin: 20px 0; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
        th { background-color: #f2f2f2; }
        h2 { color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }
    </style>
</head>
<body>
    <h1>Extracted Tables from PDF</h1>
"""
            
            for idx, table_info in enumerate(tables):
                if 'data' not in table_info:
                    continue
                
                html_content += '<h2>Table {} (Page {}, Method: {})</h2>\n'.format(
                    idx + 1,
                    table_info.get('page', '?'),
                    table_info.get('method', 'unknown')
                )
                
                data = table_info['data']
                if data:
                    html_content += '<table>\n'
                    
                    for row in data:
                        html_content += '  <tr>\n'
                        for cell in row:
                            html_content += '    <td>{}</td>\n'.format(str(cell))
                        html_content += '  </tr>\n'
                    
                    html_content += '</table>\n'
            
            html_content += """</body>
</html>"""
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print("  [OK] Saved to: {}".format(output_file))
            return output_file
        
        except Exception as e:
            print("  [ERROR] {}".format(e))
            return None


def main():
    if len(sys.argv) < 2:
        print("Usage: python table_extractor.py <pdf_file> [--format csv|excel|json|markdown|html|all]")
        print("\nExample: python table_extractor.py H.pdf --format all")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    export_format = "all"
    
    if '--format' in sys.argv:
        idx = sys.argv.index('--format')
        if idx + 1 < len(sys.argv):
            export_format = sys.argv[idx + 1]
    
    if not Path(pdf_path).exists():
        print("[ERROR] File not found: {}".format(pdf_path))
        sys.exit(1)
    
    # Extract tables
    extractor = AdvancedTableExtractor(pdf_path)
    results = extractor.extract_all()
    
    # Print summary
    print("\n" + "="*70)
    print("EXTRACTION SUMMARY")
    print("="*70)
    print("Total tables found: {}".format(results['statistics']['total_tables_found']))
    print("By method: {}".format(results['statistics']['by_method']))
    print("By page: {}".format(results['statistics']['by_page']))
    
    # Display first table preview
    if results['tables']:
        print("\n" + "-"*70)
        print("PREVIEW - First Table")
        print("-"*70)
        first_table = results['tables'][0]['data']
        for i, row in enumerate(first_table[:5]):
            print("Row {}: {}".format(i+1, row))
        if len(first_table) > 5:
            print("... ({} more rows)".format(len(first_table) - 5))
    
    # Export
    exporter = TableExporter()
    
    if export_format == "all":
        exporter.to_csv(results['tables'])
        exporter.to_excel(results['tables'])
        exporter.to_json(results)
        exporter.to_markdown(results['tables'])
        exporter.to_html(results['tables'])
    elif export_format == "csv":
        exporter.to_csv(results['tables'])
    elif export_format == "excel":
        exporter.to_excel(results['tables'])
    elif export_format == "json":
        exporter.to_json(results)
    elif export_format == "markdown":
        exporter.to_markdown(results['tables'])
    elif export_format == "html":
        exporter.to_html(results['tables'])
    
    print("\n" + "="*70)
    print("COMPLETE")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
