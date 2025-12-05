#!/usr/bin/env python3
"""
FastAPI Web Upload for PDF Symbol Detection
Modern, fast, async API with beautiful web UI
"""

import os
import json
import base64
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

try:
    from fastapi import FastAPI, UploadFile, File, HTTPException
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
except ImportError:
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "fastapi", "uvicorn", "python-multipart"])
    from fastapi import FastAPI, UploadFile, File, HTTPException
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.symbol_detector import SymbolTemplate, SymbolDetector, SymbolDetectionDB

load_dotenv()

# FastAPI app
app = FastAPI(
    title="Symbol Detection API",
    description="Upload PDFs and automatically detect stored symbols",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Upload folder
UPLOAD_FOLDER = Path("uploads")
UPLOAD_FOLDER.mkdir(exist_ok=True)

# HTML Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Symbol Detection - FastAPI</title>
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
        
        .badge {
            display: inline-block;
            background: #4caf50;
            color: white;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 12px;
            margin-left: 10px;
            font-weight: 600;
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
        
        button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
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
        
        .success {
            background-color: #efe;
            color: #3c3;
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
            border-left: 4px solid #3c3;
            display: none;
        }
        
        .success.show {
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
        <h1>📊 Symbol Detection <span class="badge">FastAPI</span></h1>
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
        <div class="success" id="successMsg"></div>
        
        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p>Processing PDF and detecting symbols...</p>
        </div>
        
        <div class="results" id="results">
            <div class="result-header" id="resultHeader"></div>
            
            <div class="summary" id="summarySection"></div>
            
            <div id="overlayContainer" style="text-align:center;margin-top:20px;"></div>
            
            <div class="pages-section" id="pagesSection"></div>
            
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
        
        uploadBtn.addEventListener('click', async () => {
            if (!uploadedFile) {
                showError('Please select a PDF file');
                return;
            }
            
            clearError();
            clearSuccess();
            showLoading(true);
            uploadBtn.disabled = true;
            
            const formData = new FormData();
            formData.append('file', uploadedFile);
            
            try {
                const response = await fetch('/api/detect', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    detectionResults = data;
                    displayResults(data);
                    showSuccess('✅ Detection completed successfully!');
                    showLoading(false);
                } else {
                    showError(data.detail || data.error || 'Error processing PDF');
                    showLoading(false);
                }
            } catch (error) {
                showError('Error: ' + error.message);
                showLoading(false);
            } finally {
                uploadBtn.disabled = false;
            }
        });
        
        function showError(msg) {
            const errorDiv = document.getElementById('errorMsg');
            errorDiv.textContent = msg;
            errorDiv.classList.add('show');
        }
        
        function clearError() {
            document.getElementById('errorMsg').classList.remove('show');
        }
        
        function showSuccess(msg) {
            const successDiv = document.getElementById('successMsg');
            successDiv.textContent = msg;
            successDiv.classList.add('show');
        }
        
        function clearSuccess() {
            document.getElementById('successMsg').classList.remove('show');
        }
        
        function showLoading(show) {
            document.getElementById('loading').style.display = show ? 'block' : 'none';
        }
        
        function displayResults(data) {
            const resultsDiv = document.getElementById('results');
            resultsDiv.classList.add('show');
            
            const header = document.getElementById('resultHeader');
            header.innerHTML = `
                <h2>✅ Detection Complete</h2>
                <div class="result-meta">
                    <strong>File:</strong> ${data.file} | 
                    <strong>Time:</strong> ${new Date(data.timestamp).toLocaleString()}
                </div>
            `;
            
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
            
            if (data.pages && data.pages.length > 0) {
                const pagesDiv = document.getElementById('pagesSection');
                let pagesHTML = '<h3>📄 Per-Page Breakdown</h3>';
                // show overlay of first page if present
                const overlayContainer = document.getElementById('overlayContainer');
                overlayContainer.innerHTML = '';
                if (data.pages[0] && data.pages[0].overlay_image) {
                    overlayContainer.innerHTML = `<h3>🖼️ Overlay (page ${data.pages[0].page})</h3><img src="${data.pages[0].overlay_image}" style="max-width:100%;border:1px solid #ddd;border-radius:8px;"/>`;
                }

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
            clearSuccess();
        }
    </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def index():
    """Main upload page"""
    return HTML_TEMPLATE


@app.post("/api/detect", response_class=JSONResponse)
async def detect(file: UploadFile = File(...)):
    """Upload PDF and detect symbols - Async endpoint"""
    try:
        # Validate file
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        # Save PDF
        pdf_filename = file.filename
        pdf_path = str(UPLOAD_FOLDER / pdf_filename)
        
        contents = await file.read()
        with open(pdf_path, 'wb') as f:
            f.write(contents)
        
        print(f"\n[*] Processing PDF: {pdf_filename}")
        
        # First try: use the prototype template-runner (works with inputs/templates)
        try:
            from prototypes.run_template_count import run as run_template_runner, OUT_DIR as RUN_OUT_DIR
            print('[*] Running prototype template matcher (prototypes/run_template_count)')
            rc = run_template_runner(pdf_path, dpi=300, thresh=0.75, scales=(0.9,1.0,1.1))
            out_json = Path(RUN_OUT_DIR) / 'template_counts.json'
            if out_json.exists():
                with open(out_json, 'r') as f:
                    results = json.load(f)
            else:
                raise RuntimeError('Prototype runner did not produce results')

        except Exception as e:
            # Fallback to DB-backed SymbolDetector
            print(f'[WARN] Prototype runner unavailable or failed: {e}')
            print('[*] Falling back to DB-backed SymbolDetector')

            # Get all symbols from DB
            template_mgr = SymbolTemplate()
            symbols = template_mgr.list_symbols()
            if not symbols:
                template_mgr.close()
                raise HTTPException(
                    status_code=400,
                    detail='No symbol templates stored and prototype runner unavailable.'
                )

            print(f"[*] Found {len(symbols)} symbol templates in DB")
            # Load templates
            templates_dict = {}
            for sym in symbols:
                img = template_mgr.get_symbol(sym['symbol_name'])
                if img is not None:
                    templates_dict[sym['symbol_name']] = img
                    print(f"  [OK] Loaded: {sym['symbol_name']}")
            template_mgr.close()

            # Run detection
            print('[*] Running symbol detection (SymbolDetector)')
            detector = SymbolDetector()
            results = detector.detect_symbols_in_pdf(pdf_path, templates_dict, dpi=300, match_thresh=0.75)
        
        # Normalize results into a consistent output structure
        output = {
            'file': pdf_filename,
            'timestamp': datetime.utcnow().isoformat(),
            'total_symbols': {},
            'pages': []
        }

        # Determine overlay directory (if prototype runner produced overlays)
        overlay_dir = None
        if 'RUN_OUT_DIR' in locals():
            overlay_dir = Path(RUN_OUT_DIR)
        else:
            overlay_dir = Path('outputs/template_counts')

        for page_result in results.get('pages', []):
            # Prototype format uses 'templates' dict and 'width'/'height'
            if 'templates' in page_result:
                page_num = page_result.get('page', 0)
                width = page_result.get('width') or page_result.get('image_width')
                height = page_result.get('height') or page_result.get('image_height')
                symbols = []
                for tname, tinfo in page_result.get('templates', {}).items():
                    count = tinfo.get('count', 0)
                    dets = tinfo.get('detections', [])
                    symbols.append({'name': tname, 'count': count, 'detections': dets[:10]})
                    output['total_symbols'][tname] = output['total_symbols'].get(tname, 0) + count

                page_output = {'page': page_num, 'image_width': width, 'image_height': height, 'symbols': symbols}

            # SymbolDetector format
            elif 'symbols' in page_result:
                page_num = page_result.get('page', 0)
                width = page_result.get('image_width') or page_result.get('width')
                height = page_result.get('image_height') or page_result.get('height')
                symbols = []
                for sym in page_result.get('symbols', []):
                    name = sym.get('symbol_name') or sym.get('name')
                    count = sym.get('count', 0)
                    dets = sym.get('detections', [])
                    symbols.append({'name': name, 'count': count, 'detections': dets[:10]})
                    output['total_symbols'][name] = output['total_symbols'].get(name, 0) + count

                page_output = {'page': page_num, 'image_width': width, 'image_height': height, 'symbols': symbols}

            else:
                # Unknown page format - include raw content
                page_output = {'page': page_result.get('page', 0), 'raw': page_result}

            # Attach overlay image if present
            try:
                overlay_path = overlay_dir / f'page_{page_output["page"]}_overlay.png'
                if overlay_path.exists():
                    with open(overlay_path, 'rb') as f:
                        b = f.read()
                    page_output['overlay_image'] = 'data:image/png;base64,' + base64.b64encode(b).decode('ascii')
                else:
                    page_output['overlay_image'] = None
            except Exception:
                page_output['overlay_image'] = None

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
        
        return output
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health", response_class=JSONResponse)
async def health():
    """Health check endpoint"""
    try:
        template_mgr = SymbolTemplate()
        symbols = template_mgr.list_symbols()
        template_mgr.close()
        
        return {
            'status': 'healthy',
            'symbols_count': len(symbols),
            'api': 'FastAPI',
            'timestamp': datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/api/info", response_class=JSONResponse)
async def info():
    """API information endpoint"""
    return {
        'name': 'Symbol Detection API',
        'version': '1.0.0',
        'framework': 'FastAPI',
        'endpoints': {
            'GET /': 'Web upload interface',
            'POST /api/detect': 'Upload PDF and detect symbols',
            'GET /api/health': 'Health check',
            'GET /api/info': 'API information'
        }
    }


if __name__ == '__main__':
    print("\n" + "="*70)
    print("SYMBOL DETECTION - FASTAPI SERVER".center(70))
    print("="*70)
    print("\nEndpoints:")
    print("  GET  /              (Web interface)")
    print("  POST /api/detect    (Upload PDF and detect)")
    print("  GET  /api/health    (Health check)")
    print("  GET  /api/info      (API information)")
    print("\n" + "="*70)
    print("Server running on http://127.0.0.1:8000".center(70))
    print("API Docs available at http://127.0.0.1:8000/docs".center(70))
    print("="*70 + "\n")
    
    uvicorn.run(
        "fastapi_upload_api:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info"
    )
