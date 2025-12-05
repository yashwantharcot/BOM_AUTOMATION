#!/usr/bin/env python3
"""
Simple Web API for PDF Upload & Symbol Detection
Single endpoint: /upload - Upload PDF and display results on web page
"""

import os
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

try:
    from flask import Flask, render_template_string, request, jsonify, send_file
    from werkzeug.utils import secure_filename
except ImportError:
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "flask", "werkzeug"])
    from flask import Flask, render_template_string, request, jsonify, send_file
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

# HTML Template for upload page
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Symbol Detection - PDF Upload</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        
        .container {
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 900px;
            width: 100%;
            padding: 40px;
        }
        
        h1 {
            color: #333;
            margin-bottom: 10px;
            text-align: center;
            font-size: 28px;
        }
        
        .subtitle {
            text-align: center;
            color: #666;
            margin-bottom: 30px;
            font-size: 14px;
        }
        
        .upload-area {
            border: 2px dashed #667eea;
            border-radius: 10px;
            padding: 40px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
            background-color: #f8f9ff;
            margin-bottom: 20px;
        }
        
        .upload-area:hover {
            border-color: #764ba2;
            background-color: #f0f1ff;
        }
        
        .upload-area.dragover {
            border-color: #764ba2;
            background-color: #e8e9ff;
        }
        
        .upload-area input[type="file"] {
            display: none;
        }
        
        .upload-icon {
            font-size: 48px;
            margin-bottom: 15px;
        }
        
        .upload-text {
            color: #333;
            font-size: 16px;
            margin-bottom: 5px;
        }
        
        .upload-hint {
            color: #999;
            font-size: 13px;
        }
        
        .button-group {
            display: flex;
            gap: 10px;
            justify-content: center;
            margin-bottom: 30px;
        }
        
        button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 25px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
        }
        
        button:active {
            transform: translateY(0);
        }
        
        #uploadBtn {
            margin-top: 15px;
        }
        
        .loading {
            display: none;
            text-align: center;
            margin: 30px 0;
        }
        
        .spinner {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 10px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .error {
            background-color: #fee;
            color: #c33;
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
            border-left: 4px solid #c33;
            display: none;
        }
        
        .error.show {
            display: block;
        }
        
        .results {
            display: none;
            margin-top: 30px;
        }
        
        .results.show {
            display: block;
        }
        
        .result-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        
        .result-header h2 {
            font-size: 20px;
            margin-bottom: 5px;
        }
        
        .result-meta {
            font-size: 13px;
            opacity: 0.9;
        }
        
        .summary {
            background: #f8f9ff;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            border-left: 4px solid #667eea;
        }
        
        .summary h3 {
            color: #333;
            margin-bottom: 15px;
            font-size: 16px;
        }
        
        .symbol-count {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }
        
        .symbol-item {
            background: white;
            padding: 15px;
            border-radius: 8px;
            border: 1px solid #e0e0e0;
            transition: all 0.3s ease;
        }
        
        .symbol-item:hover {
            border-color: #667eea;
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.1);
        }
        
        .symbol-name {
            font-weight: 600;
            color: #333;
            margin-bottom: 5px;
        }
        
        .symbol-count-value {
            font-size: 28px;
            color: #667eea;
            font-weight: bold;
        }
        
        .pages-section {
            margin-top: 30px;
        }
        
        .pages-section h3 {
            color: #333;
            margin-bottom: 15px;
            font-size: 16px;
        }
        
        .page-item {
            background: #f8f9ff;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 15px;
            border-left: 4px solid #667eea;
        }
        
        .page-header {
            font-weight: 600;
            color: #333;
            margin-bottom: 10px;
        }
        
        .page-symbols {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 10px;
        }
        
        .page-symbol {
            background: white;
            padding: 10px;
            border-radius: 5px;
            border: 1px solid #e0e0e0;
            text-align: center;
        }
        
        .page-symbol-name {
            font-size: 12px;
            color: #666;
            margin-bottom: 5px;
        }
        
        .page-symbol-count {
            font-size: 20px;
            color: #667eea;
            font-weight: bold;
        }
        
        .detections-section {
            margin-top: 30px;
        }
        
        .detections-section h3 {
            color: #333;
            margin-bottom: 15px;
            font-size: 16px;
        }
        
        .detection-item {
            background: white;
            padding: 12px;
            border-radius: 5px;
            border-left: 3px solid #667eea;
            margin-bottom: 10px;
            font-size: 13px;
        }
        
        .detection-label {
            color: #666;
            margin-right: 10px;
        }
        
        .detection-value {
            color: #333;
            font-weight: 600;
        }
        
        .confidence {
            display: inline-block;
            background: #e8f5e9;
            color: #2e7d32;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 12px;
            margin-left: 5px;
        }
        
        .export-section {
            margin-top: 30px;
            text-align: center;
        }
        
        .export-section button {
            background: #4caf50;
        }
        
        .export-section button:hover {
            box-shadow: 0 10px 20px rgba(76, 175, 80, 0.3);
        }
        
        .info-box {
            background: #e3f2fd;
            border-left: 4px solid #2196f3;
            padding: 15px;
            border-radius: 5px;
            margin-top: 20px;
            font-size: 13px;
            color: #1565c0;
        }
        
        @media (max-width: 600px) {
            .container {
                padding: 20px;
            }
            
            h1 {
                font-size: 22px;
            }
            
            .upload-area {
                padding: 30px 20px;
            }
            
            .upload-icon {
                font-size: 36px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Symbol Detection</h1>
        <p class="subtitle">Upload a PDF and automatically count stored symbols</p>
        
        <div class="upload-area" id="uploadArea">
            <div class="upload-icon">📄</div>
            <div class="upload-text">Click to upload or drag and drop</div>
            <div class="upload-hint">PDF files up to 100MB</div>
            <input type="file" id="fileInput" accept=".pdf" />
        </div>
        
        <div class="button-group">
            <button id="uploadBtn">Upload & Detect</button>
            <button id="clearBtn" onclick="clearResults()">Clear</button>
        </div>
        
        <div class="error" id="errorMsg"></div>
        
        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p>Processing PDF and detecting symbols...</p>
        </div>
        
        <div class="results" id="results">
            <div class="result-header" id="resultHeader"></div>
            
            <div class="summary" id="summarySection"></div>
            
            <div class="pages-section" id="pagesSection"></div>
            
            <div class="detections-section" id="detectionsSection"></div>
            
            <div class="export-section">
                <button onclick="downloadJSON()">📥 Download Results (JSON)</button>
            </div>
            
            <div class="info-box">
                ℹ️ Results are stored in MongoDB for audit trail and future reference.
            </div>
        </div>
    </div>

    <script>
        let uploadedFile = null;
        let detectionResults = null;
        
        // File upload handling
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        const uploadBtn = document.getElementById('uploadBtn');
        
        uploadArea.addEventListener('click', () => fileInput.click());
        
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                fileInput.files = files;
                uploadedFile = files[0];
                uploadArea.querySelector('.upload-text').textContent = '✅ ' + files[0].name;
            }
        });
        
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                uploadedFile = e.target.files[0];
                uploadArea.querySelector('.upload-text').textContent = '✅ ' + e.target.files[0].name;
            }
        });
        
        // Upload and detect
        uploadBtn.addEventListener('click', async () => {
            if (!uploadedFile) {
                showError('Please select a PDF file');
                return;
            }
            
            clearError();
            showLoading(true);
            
            const formData = new FormData();
            formData.append('file', uploadedFile);
            
            try {
                const response = await fetch('/detect', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    detectionResults = data;
                    displayResults(data);
                    showLoading(false);
                } else {
                    showError(data.error || 'Error processing PDF');
                    showLoading(false);
                }
            } catch (error) {
                showError('Error: ' + error.message);
                showLoading(false);
            }
        });
        
        function showError(msg) {
            const errorDiv = document.getElementById('errorMsg');
            errorDiv.textContent = msg;
            errorDiv.classList.add('show');
        }
        
        function clearError() {
            const errorDiv = document.getElementById('errorMsg');
            errorDiv.classList.remove('show');
        }
        
        function showLoading(show) {
            document.getElementById('loading').style.display = show ? 'block' : 'none';
        }
        
        function displayResults(data) {
            const resultsDiv = document.getElementById('results');
            resultsDiv.classList.add('show');
            
            // Header
            const header = document.getElementById('resultHeader');
            header.innerHTML = `
                <h2>✅ Detection Complete</h2>
                <div class="result-meta">
                    <strong>File:</strong> ${data.file} | 
                    <strong>Time:</strong> ${new Date(data.timestamp).toLocaleString()}
                </div>
            `;
            
            // Summary
            const summary = document.getElementById('summarySection');
            let summaryHTML = '<h3>📈 Total Symbol Counts</h3><div class="symbol-count">';
            for (const [symbol, count] of Object.entries(data.total_symbols || {})) {
                summaryHTML += `
                    <div class="symbol-item">
                        <div class="symbol-name">${symbol}</div>
                        <div class="symbol-count-value">${count}</div>
                    </div>
                `;
            }
            summaryHTML += '</div>';
            summary.innerHTML = summaryHTML;
            
            // Pages
            if (data.pages && data.pages.length > 0) {
                const pagesDiv = document.getElementById('pagesSection');
                let pagesHTML = '<h3>📄 Per-Page Breakdown</h3>';
                
                for (const page of data.pages) {
                    pagesHTML += `
                        <div class="page-item">
                            <div class="page-header">Page ${page.page} (${page.image_width}×${page.image_height}px)</div>
                            <div class="page-symbols">
                    `;
                    
                    for (const symbol of page.symbols) {
                        pagesHTML += `
                            <div class="page-symbol">
                                <div class="page-symbol-name">${symbol.name}</div>
                                <div class="page-symbol-count">${symbol.count}</div>
                            </div>
                        `;
                    }
                    pagesHTML += '</div></div>';
                }
                pagesDiv.innerHTML = pagesHTML;
            }
            
            // Detections with confidence
            if (data.pages && data.pages.length > 0) {
                const detectionsDiv = document.getElementById('detectionsSection');
                let detectionsHTML = '<h3>🎯 Detailed Detections</h3>';
                
                for (const page of data.pages) {
                    for (const symbol of page.symbols) {
                        if (symbol.detections && symbol.detections.length > 0) {
                            detectionsHTML += `<div class="detection-item">
                                <strong>${symbol.name}</strong> - ${symbol.detections.length} detections on Page ${page.page}:`;
                            
                            for (const det of symbol.detections.slice(0, 5)) {
                                const conf = (det.score * 100).toFixed(1);
                                detectionsHTML += ` <span class="confidence">${conf}%</span>`;
                            }
                            
                            if (symbol.detections.length > 5) {
                                detectionsHTML += ` <span class="confidence">+${symbol.detections.length - 5} more</span>`;
                            }
                            detectionsHTML += `</div>`;
                        }
                    }
                }
                detectionsDiv.innerHTML = detectionsHTML;
            }
        }
        
        function downloadJSON() {
            if (!detectionResults) return;
            
            const dataStr = JSON.stringify(detectionResults, null, 2);
            const dataBlob = new Blob([dataStr], { type: 'application/json' });
            const url = URL.createObjectURL(dataBlob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `symbol_detection_${new Date().getTime()}.json`;
            link.click();
        }
        
        function clearResults() {
            document.getElementById('results').classList.remove('show');
            document.getElementById('fileInput').value = '';
            uploadArea.querySelector('.upload-text').textContent = 'Click to upload or drag and drop';
            uploadedFile = null;
            detectionResults = null;
            clearError();
        }
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    """Main upload page"""
    return render_template_string(HTML_TEMPLATE)


@app.route('/detect', methods=['POST'])
def detect():
    """Upload PDF and detect symbols"""
    try:
        # Check if file is provided
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'error': 'Only PDF files are supported'}), 400
        
        # Save PDF
        pdf_filename = secure_filename(file.filename)
        pdf_path = str(UPLOAD_FOLDER / pdf_filename)
        file.save(pdf_path)
        
        print(f"\n[*] Processing PDF: {pdf_filename}")
        
        # Get all symbols
        template_mgr = SymbolTemplate()
        symbols = template_mgr.list_symbols()
        
        if not symbols:
            template_mgr.close()
            return jsonify({
                'error': 'No symbol templates stored. Please upload symbol templates first.'
            }), 400
        
        print(f"[*] Found {len(symbols)} symbol templates")
        
        # Load templates
        templates_dict = {}
        for sym in symbols:
            img = template_mgr.get_symbol(sym['symbol_name'])
            if img is not None:
                templates_dict[sym['symbol_name']] = img
                print(f"  [OK] Loaded: {sym['symbol_name']}")
        
        template_mgr.close()
        
        # Run detection
        print("[*] Running symbol detection...")
        detector = SymbolDetector()
        results = detector.detect_symbols_in_pdf(pdf_path, templates_dict, dpi=300, match_thresh=0.75)
        
        # Prepare output
        output = {
            'file': pdf_filename,
            'timestamp': datetime.utcnow().isoformat(),
            'total_symbols': {},
            'pages': []
        }
        
        # Process pages
        for page_result in results['pages']:
            page_output = {
                'page': page_result['page'],
                'image_width': page_result['image_width'],
                'image_height': page_result['image_height'],
                'symbols': []
            }
            
            for sym in page_result['symbols']:
                page_output['symbols'].append({
                    'name': sym['symbol_name'],
                    'count': sym['count'],
                    'detections': sym['detections'][:5]  # Include first 5 detections
                })
                
                # Update total count
                if sym['symbol_name'] not in output['total_symbols']:
                    output['total_symbols'][sym['symbol_name']] = 0
                output['total_symbols'][sym['symbol_name']] += sym['count']
            
            output['pages'].append(page_output)
        
        # Store in MongoDB
        print("[*] Storing in MongoDB...")
        try:
            detection_db = SymbolDetectionDB()
            detection_db.create_indexes()
            detection_db.store_detection_results(pdf_filename, results)
            detection_db.close()
            print("[OK] Stored in MongoDB")
        except Exception as e:
            print(f"[WARN] MongoDB storage: {e}")
        
        print("[OK] Detection complete")
        print(f"\nSummary:")
        for sym_name, count in output['total_symbols'].items():
            print(f"  {sym_name}: {count}")
        
        return jsonify(output), 200
    
    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    try:
        template_mgr = SymbolTemplate()
        symbols = template_mgr.list_symbols()
        template_mgr.close()
        
        return jsonify({
            'status': 'healthy',
            'symbols_count': len(symbols)
        }), 200
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500


if __name__ == '__main__':
    print("\n" + "="*70)
    print("SYMBOL DETECTION - WEB UPLOAD API".center(70))
    print("="*70)
    print("\nEndpoints:")
    print("  GET  /              (Upload page with UI)")
    print("  POST /detect        (Upload PDF and detect)")
    print("  GET  /health        (Health check)")
    print("\n" + "="*70)
    print("Server running on http://127.0.0.1:5000".center(70))
    print("="*70 + "\n")
    
    app.run(host='127.0.0.1', port=5000, debug=False)
