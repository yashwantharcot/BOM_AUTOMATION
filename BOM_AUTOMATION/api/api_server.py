#!/usr/bin/env python3
"""
Symbol Detection REST API
Upload PDF → Count stored symbols → Get exact counts
"""

import os
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

try:
    from flask import Flask, request, jsonify, send_file
    from werkzeug.utils import secure_filename
except ImportError:
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "flask", "werkzeug"])
    from flask import Flask, request, jsonify, send_file
    from werkzeug.utils import secure_filename

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.symbol_detector import SymbolTemplate, SymbolDetector, SymbolDetectionDB

load_dotenv()

app = Flask(__name__)
UPLOAD_FOLDER = Path("uploads")
UPLOAD_FOLDER.mkdir(exist_ok=True)
app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max

# Store job IDs in memory (in production, use Redis)
jobs = {}


@app.route('/api/v1/health', methods=['GET'])
def health():
    """Health check"""
    try:
        template_mgr = SymbolTemplate()
        template_mgr.close()
        return jsonify({"status": "healthy"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500


@app.route('/api/v1/symbols', methods=['GET'])
def list_symbols():
    """List all stored symbol templates"""
    try:
        template_mgr = SymbolTemplate()
        symbols = template_mgr.list_symbols()
        template_mgr.close()
        
        result = []
        for sym in symbols:
            result.append({
                'id': str(sym.get('_id')),
                'name': sym.get('symbol_name'),
                'image_filename': sym.get('image_filename'),
                'file_size': sym.get('file_size'),
                'created_at': sym.get('created_at').isoformat() if sym.get('created_at') else None
            })
        
        return jsonify({
            "status": "success",
            "count": len(result),
            "symbols": result
        }), 200
    
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route('/api/v1/symbols', methods=['POST'])
def upload_symbol():
    """Upload symbol template"""
    try:
        if 'file' not in request.files:
            return jsonify({"status": "error", "error": "No file provided"}), 400
        
        if 'name' not in request.form:
            return jsonify({"status": "error", "error": "No symbol name provided"}), 400
        
        file = request.files['file']
        symbol_name = request.form['name']
        
        if file.filename == '':
            return jsonify({"status": "error", "error": "No file selected"}), 400
        
        # Save temp file
        temp_path = app.config['UPLOAD_FOLDER'] + "/" + secure_filename(file.filename)
        file.save(temp_path)
        
        # Upload to MongoDB
        template_mgr = SymbolTemplate()
        doc_id = template_mgr.upload_symbol(symbol_name, temp_path)
        template_mgr.close()
        
        # Clean up temp file
        Path(temp_path).unlink()
        
        if doc_id:
            return jsonify({
                "status": "success",
                "message": f"Symbol '{symbol_name}' uploaded",
                "id": str(doc_id)
            }), 201
        else:
            return jsonify({"status": "error", "error": "Upload failed"}), 500
    
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route('/api/v1/symbols/<symbol_name>', methods=['DELETE'])
def delete_symbol(symbol_name):
    """Delete symbol template"""
    try:
        template_mgr = SymbolTemplate()
        success = template_mgr.delete_symbol(symbol_name)
        template_mgr.close()
        
        if success:
            return jsonify({"status": "success", "message": f"Symbol '{symbol_name}' deleted"}), 200
        else:
            return jsonify({"status": "error", "error": "Symbol not found"}), 404
    
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route('/api/v1/upload', methods=['POST'])
def upload_pdf():
    """Upload PDF for symbol detection"""
    try:
        if 'file' not in request.files:
            return jsonify({"status": "error", "error": "No file provided"}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({"status": "error", "error": "No file selected"}), 400
        
        # Save PDF
        pdf_filename = secure_filename(file.filename)
        pdf_path = str(app.config['UPLOAD_FOLDER'] / pdf_filename)
        file.save(pdf_path)
        
        # Create job ID
        job_id = f"job_{int(datetime.utcnow().timestamp() * 1000)}"
        
        # Start detection (in production, use Celery/async)
        print(f"[*] Starting detection job: {job_id}")
        
        try:
            # Get all symbols
            template_mgr = SymbolTemplate()
            symbols = template_mgr.list_symbols()
            
            if not symbols:
                return jsonify({
                    "status": "error",
                    "error": "No symbol templates stored. Please upload symbol templates first."
                }), 400
            
            # Load templates
            templates_dict = {}
            for sym in symbols:
                img = template_mgr.get_symbol(sym['symbol_name'])
                if img is not None:
                    templates_dict[sym['symbol_name']] = img
            
            template_mgr.close()
            
            # Run detection
            detector = SymbolDetector()
            results = detector.detect_symbols_in_pdf(pdf_path, templates_dict, dpi=300, match_thresh=0.75)
            
            # Store in MongoDB
            detection_db = SymbolDetectionDB()
            detection_db.create_indexes()
            detection_db.store_detection_results(pdf_filename, results)
            detection_db.close()
            
            # Save job
            jobs[job_id] = {
                'status': 'completed',
                'file': pdf_filename,
                'results': results,
                'created_at': datetime.utcnow().isoformat()
            }
            
            print(f"[OK] Job completed: {job_id}")
            
            return jsonify({
                "status": "success",
                "job_id": job_id,
                "message": "PDF uploaded and processed"
            }), 202
        
        except Exception as e:
            jobs[job_id] = {
                'status': 'failed',
                'error': str(e),
                'created_at': datetime.utcnow().isoformat()
            }
            return jsonify({
                "status": "error",
                "job_id": job_id,
                "error": str(e)
            }), 500
    
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route('/api/v1/results/<job_id>', methods=['GET'])
def get_results(job_id):
    """Get detection results for job"""
    try:
        if job_id not in jobs:
            return jsonify({"status": "error", "error": "Job not found"}), 404
        
        job = jobs[job_id]
        
        if job['status'] == 'completed':
            results = job['results']
            
            # Build summary
            summary = {
                "job_id": job_id,
                "file": job['file'],
                "pages": [],
                "total_symbols": {}
            }
            
            for page_result in results['pages']:
                page_summary = {
                    "page": page_result['page'],
                    "image_width": page_result['image_width'],
                    "image_height": page_result['image_height'],
                    "symbols": []
                }
                
                for sym in page_result['symbols']:
                    page_summary['symbols'].append({
                        "name": sym['symbol_name'],
                        "count": sym['count'],
                        "detections_count": len(sym['detections'])
                    })
                    
                    if sym['symbol_name'] not in summary['total_symbols']:
                        summary['total_symbols'][sym['symbol_name']] = 0
                    summary['total_symbols'][sym['symbol_name']] += sym['count']
                
                summary['pages'].append(page_summary)
            
            return jsonify({
                "status": "success",
                "data": summary
            }), 200
        
        elif job['status'] == 'failed':
            return jsonify({
                "status": "error",
                "error": job.get('error', 'Unknown error')
            }), 500
        
        else:
            return jsonify({
                "status": "processing",
                "job_id": job_id
            }), 202
    
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route('/api/v1/results/<job_id>/detailed', methods=['GET'])
def get_detailed_results(job_id):
    """Get detailed detection results with bounding boxes"""
    try:
        if job_id not in jobs:
            return jsonify({"status": "error", "error": "Job not found"}), 404
        
        job = jobs[job_id]
        
        if job['status'] != 'completed':
            return jsonify({"status": "error", "error": "Job not completed"}), 400
        
        return jsonify({
            "status": "success",
            "data": job['results']
        }), 200
    
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route('/api/v1/results/<job_id>/audit', methods=['GET'])
def get_audit_trail(job_id):
    """Get audit trail from MongoDB"""
    try:
        if job_id not in jobs:
            return jsonify({"status": "error", "error": "Job not found"}), 404
        
        job = jobs[job_id]
        
        if job['status'] != 'completed':
            return jsonify({"status": "error", "error": "Job not completed"}), 400
        
        filename = job['file']
        
        detection_db = SymbolDetectionDB()
        summary = detection_db.get_summary(filename)
        detection_db.close()
        
        if summary:
            return jsonify({
                "status": "success",
                "data": summary
            }), 200
        else:
            return jsonify({"status": "error", "error": "No audit trail found"}), 404
    
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route('/api/v1/stats', methods=['GET'])
def get_stats():
    """Get system statistics"""
    try:
        template_mgr = SymbolTemplate()
        symbols = template_mgr.list_symbols()
        template_mgr.close()
        
        return jsonify({
            "status": "success",
            "data": {
                "total_symbols": len(symbols),
                "total_jobs": len(jobs),
                "completed_jobs": len([j for j in jobs.values() if j['status'] == 'completed']),
                "failed_jobs": len([j for j in jobs.values() if j['status'] == 'failed'])
            }
        }), 200
    
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


if __name__ == '__main__':
    print("\n" + "="*70)
    print("SYMBOL DETECTION REST API")
    print("="*70)
    print("\nEndpoints:")
    print("  GET  /api/v1/health")
    print("  GET  /api/v1/symbols")
    print("  POST /api/v1/symbols (upload template)")
    print("  DEL  /api/v1/symbols/<name>")
    print("  POST /api/v1/upload (upload PDF)")
    print("  GET  /api/v1/results/<job_id>")
    print("  GET  /api/v1/results/<job_id>/detailed")
    print("  GET  /api/v1/results/<job_id>/audit")
    print("  GET  /api/v1/stats")
    print("\n" + "="*70)
    print("Server running on http://127.0.0.1:5000")
    print("="*70 + "\n")
    
    app.run(host='127.0.0.1', port=5000, debug=False)
