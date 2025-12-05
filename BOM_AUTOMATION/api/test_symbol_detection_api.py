#!/usr/bin/env python3
"""
Simple Test API for Symbol Detection
Upload symbol template + PDF → Get symbol count
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

try:
    from flask import Flask, request, jsonify
    from werkzeug.utils import secure_filename
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "flask", "werkzeug"])
    from flask import Flask, request, jsonify
    from werkzeug.utils import secure_filename

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.symbol_detector import SymbolTemplate, SymbolDetector

app = Flask(__name__)
UPLOAD_FOLDER = Path("uploads")
UPLOAD_FOLDER.mkdir(exist_ok=True)
app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB

# Store templates temporarily
temp_template_path = UPLOAD_FOLDER / "temp_templates"
temp_template_path.mkdir(exist_ok=True)


@app.route('/api/test/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({"status": "healthy", "message": "Test API is running"}), 200


@app.route('/api/test/upload-template', methods=['POST'])
def upload_template():
    """Upload symbol template image"""
    try:
        if 'file' not in request.files:
            return jsonify({"status": "error", "error": "No file provided"}), 400
        
        if 'name' not in request.form:
            return jsonify({"status": "error", "error": "No symbol name provided"}), 400
        
        file = request.files['file']
        symbol_name = request.form['name']
        
        if file.filename == '':
            return jsonify({"status": "error", "error": "No file selected"}), 400
        
        # Save template file
        template_path = temp_template_path / secure_filename(file.filename)
        file.save(str(template_path))
        
        # Upload to MongoDB (using existing infrastructure)
        template_mgr = SymbolTemplate()
        doc_id = template_mgr.upload_symbol(symbol_name, str(template_path))
        template_mgr.close()
        
        # Keep temp file for now
        # template_path.unlink()  # Don't delete, keep for reference
        
        if doc_id:
            return jsonify({
                "status": "success",
                "message": f"Symbol template '{symbol_name}' uploaded",
                "symbol_name": symbol_name,
                "id": str(doc_id)
            }), 200
        else:
            return jsonify({"status": "error", "error": "Upload failed"}), 500
    
    except Exception as e:
        import traceback
        return jsonify({
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@app.route('/api/test/detect', methods=['POST'])
def detect_symbols():
    """Detect symbols in PDF using uploaded templates"""
    try:
        if 'file' not in request.files:
            return jsonify({"status": "error", "error": "No PDF file provided"}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({"status": "error", "error": "No file selected"}), 400
        
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({"status": "error", "error": "Only PDF files are supported"}), 400
        
        # Save PDF
        pdf_filename = secure_filename(file.filename)
        pdf_path = app.config['UPLOAD_FOLDER'] / pdf_filename
        file.save(str(pdf_path))
        
        print(f"\n[*] Processing PDF: {pdf_filename}")
        
        # Get all symbols from MongoDB
        template_mgr = SymbolTemplate()
        symbols = template_mgr.list_symbols()
        
        if not symbols:
            template_mgr.close()
            return jsonify({
                "status": "error",
                "error": "No symbol templates stored. Please upload templates first using /api/test/upload-template"
            }), 400
        
        print(f"[*] Found {len(symbols)} symbol template(s)")
        
        # Load templates
        templates_dict = {}
        for sym in symbols:
            img = template_mgr.get_symbol(sym['symbol_name'])
            if img is not None:
                templates_dict[sym['symbol_name']] = img
                print(f"  [OK] Loaded: {sym['symbol_name']}")
        
        template_mgr.close()
        
        if not templates_dict:
            return jsonify({
                "status": "error",
                "error": "Failed to load symbol templates"
            }), 500
        
        # Run detection using existing SymbolDetector
        print("[*] Running symbol detection...")
        detector = SymbolDetector()
        results = detector.detect_symbols_in_pdf(
            str(pdf_path),
            templates_dict,
            dpi=300,
            match_thresh=0.75
        )
        
        # Format results
        output = {
            'pdf_file': pdf_filename,
            'timestamp': datetime.utcnow().isoformat(),
            'symbol_counts': {},
            'page_results': []
        }
        
        # Aggregate symbol counts
        for page_result in results.get('pages', []):
            page_num = page_result.get('page', 0)
            page_output = {
                'page': page_num + 1,
                'symbols': {}
            }
            
            for symbol_name, symbol_data in page_result.get('symbols', {}).items():
                count = symbol_data.get('count', 0)
                detections = symbol_data.get('detections', [])
                
                page_output['symbols'][symbol_name] = {
                    'count': count,
                    'detections': detections
                }
                
                # Aggregate total counts
                if symbol_name not in output['symbol_counts']:
                    output['symbol_counts'][symbol_name] = 0
                output['symbol_counts'][symbol_name] += count
            
            output['page_results'].append(page_output)
        
        print(f"\n[*] Detection complete!")
        print(f"[*] Total counts: {output['symbol_counts']}")
        
        return jsonify({
            "status": "success",
            "results": output
        }), 200
    
    except Exception as e:
        import traceback
        return jsonify({
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@app.route('/api/test/templates', methods=['GET'])
def list_templates():
    """List uploaded templates"""
    try:
        template_mgr = SymbolTemplate()
        symbols = template_mgr.list_symbols()
        template_mgr.close()
        
        result = []
        for sym in symbols:
            result.append({
                'name': sym.get('symbol_name'),
                'filename': sym.get('image_filename'),
                'created_at': sym.get('created_at').isoformat() if sym.get('created_at') else None
            })
        
        return jsonify({
            "status": "success",
            "templates": result,
            "count": len(result)
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


@app.route('/api/test/clear', methods=['POST'])
def clear_templates():
    """Clear all templates (delete from MongoDB)"""
    try:
        template_mgr = SymbolTemplate()
        symbols = template_mgr.list_symbols()
        
        deleted_count = 0
        for sym in symbols:
            symbol_name = sym.get('symbol_name')
            if template_mgr.delete_symbol(symbol_name):
                deleted_count += 1
        
        template_mgr.close()
        
        return jsonify({
            "status": "success",
            "message": f"Deleted {deleted_count} template(s)"
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


if __name__ == '__main__':
    print("=" * 70)
    print("Symbol Detection Test API")
    print("=" * 70)
    print("\nEndpoints:")
    print("  POST /api/test/upload-template  - Upload symbol template (form: file, name)")
    print("  POST /api/test/detect           - Detect symbols in PDF (form: file)")
    print("  GET  /api/test/templates        - List uploaded templates")
    print("  POST /api/test/clear            - Clear all templates")
    print("  GET  /api/test/health           - Health check")
    print("\nStarting server on http://localhost:5001")
    print("=" * 70)
    
    app.run(host='0.0.0.0', port=5001, debug=True)
