#!/usr/bin/env python3
"""
FastAPI Symbol Counting API
Upload a symbol template image and PDF, get count of occurrences
"""

import os
import json
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Optional

try:
    from fastapi import FastAPI, UploadFile, File, HTTPException, Form
    from fastapi.responses import JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
except ImportError:
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "fastapi", "uvicorn", "python-multipart"])
    from fastapi import FastAPI, UploadFile, File, HTTPException, Form
    from fastapi.responses import JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import counting function
from count_symbol import count_symbol_in_pdf

# FastAPI app
app = FastAPI(
    title="Symbol Counting API",
    description="Upload symbol template and PDF to count occurrences",
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
OUTPUT_FOLDER = Path("outputs")
OUTPUT_FOLDER.mkdir(exist_ok=True)


@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "Symbol Counting API",
        "version": "1.0.0",
        "endpoints": {
            "/count": "POST - Upload PDF and symbol template to count occurrences",
            "/health": "GET - Health check"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.post("/count")
async def count_symbol(
    pdf_file: UploadFile = File(..., description="PDF file to search in"),
    symbol_file: UploadFile = File(..., description="Symbol template image (PNG/JPG)"),
    threshold: Optional[float] = Form(0.65, description="Matching threshold (0.0-1.0)"),
    dpi: Optional[int] = Form(300, description="Rasterization DPI")
):
    """
    Count occurrences of a symbol template in a PDF
    
    Parameters:
    - pdf_file: PDF file to search
    - symbol_file: Symbol template image (PNG/JPG)
    - threshold: Matching threshold (default: 0.65, lower = more matches)
    - dpi: Rasterization DPI (default: 300, higher = more accurate but slower)
    
    Returns:
    - total_count: Total number of symbol occurrences
    - pages: Per-page breakdown
    - details: Full detection details
    """
    
    # Validate threshold
    if not 0.0 <= threshold <= 1.0:
        raise HTTPException(status_code=400, detail="Threshold must be between 0.0 and 1.0")
    
    if dpi < 100 or dpi > 1200:
        raise HTTPException(status_code=400, detail="DPI must be between 100 and 1200")
    
    # Validate file types
    if not pdf_file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="PDF file must have .pdf extension")
    
    valid_image_extensions = ['.png', '.jpg', '.jpeg']
    if not any(symbol_file.filename.lower().endswith(ext) for ext in valid_image_extensions):
        raise HTTPException(status_code=400, detail="Symbol file must be PNG or JPG")
    
    # Save uploaded files temporarily
    pdf_path = None
    symbol_path = None
    
    try:
        # Save PDF
        pdf_path = UPLOAD_FOLDER / f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{pdf_file.filename}"
        with open(pdf_path, 'wb') as f:
            content = await pdf_file.read()
            f.write(content)
        
        # Save symbol template
        symbol_path = UPLOAD_FOLDER / f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{symbol_file.filename}"
        with open(symbol_path, 'wb') as f:
            content = await symbol_file.read()
            f.write(content)
        
        # Count symbols
        print(f"[API] Counting symbols in {pdf_file.filename} using template {symbol_file.filename}")
        print(f"[API] Threshold: {threshold}, DPI: {dpi}")
        
        results = count_symbol_in_pdf(
            str(pdf_path),
            str(symbol_path),
            dpi=dpi,
            match_thresh=threshold
        )
        
        if results is None:
            raise HTTPException(status_code=500, detail="Symbol counting failed")
        
        # Prepare response
        response = {
            "status": "success",
            "pdf_filename": pdf_file.filename,
            "symbol_filename": symbol_file.filename,
            "total_count": results['total_count'],
            "pages": [
                {
                    "page": page_result['page'],
                    "count": page_result['count'],
                    "detections": [
                        {
                            "bbox": det['bbox'],
                            "score": det['score'],
                            "scale": det.get('scale', 1.0)
                        }
                        for det in page_result['detections']
                    ]
                }
                for page_result in results['pages']
            ],
            "summary": {
                "total_pages": len(results['pages']),
                "pages_with_symbols": sum(1 for p in results['pages'] if p['count'] > 0),
                "average_confidence": (
                    sum(d['score'] for page in results['pages'] for d in page['detections']) / 
                    max(1, results['total_count'])
                ) if results['total_count'] > 0 else 0.0
            },
            "parameters": {
                "threshold": threshold,
                "dpi": dpi
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return JSONResponse(content=response)
    
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
    
    finally:
        # Clean up temporary files
        if pdf_path and pdf_path.exists():
            try:
                pdf_path.unlink()
            except:
                pass
        if symbol_path and symbol_path.exists():
            try:
                symbol_path.unlink()
            except:
                pass


@app.post("/count/local")
async def count_symbol_local(
    pdf_filename: str = Form(..., description="PDF filename in uploads folder"),
    symbol_filename: str = Form(..., description="Symbol template filename"),
    threshold: Optional[float] = Form(0.65),
    dpi: Optional[int] = Form(300)
):
    """
    Count symbols using files already in the uploads folder
    
    Parameters:
    - pdf_filename: Name of PDF file in uploads folder
    - symbol_filename: Name of symbol template in uploads folder or root directory
    - threshold: Matching threshold (default: 0.65)
    - dpi: Rasterization DPI (default: 300)
    """
    
    # Find PDF file
    pdf_path = UPLOAD_FOLDER / pdf_filename
    if not pdf_path.exists():
        pdf_path = Path(pdf_filename)
        if not pdf_path.exists():
            raise HTTPException(status_code=404, detail=f"PDF file not found: {pdf_filename}")
    
    # Find symbol file
    symbol_path = UPLOAD_FOLDER / symbol_filename
    if not symbol_path.exists():
        symbol_path = Path(symbol_filename)
        if not symbol_path.exists():
            raise HTTPException(status_code=404, detail=f"Symbol file not found: {symbol_filename}")
    
    try:
        results = count_symbol_in_pdf(
            str(pdf_path),
            str(symbol_path),
            dpi=dpi,
            match_thresh=threshold
        )
        
        if results is None:
            raise HTTPException(status_code=500, detail="Symbol counting failed")
        
        response = {
            "status": "success",
            "pdf_filename": pdf_filename,
            "symbol_filename": symbol_filename,
            "total_count": results['total_count'],
            "pages": [
                {
                    "page": page_result['page'],
                    "count": page_result['count']
                }
                for page_result in results['pages']
            ],
            "timestamp": datetime.now().isoformat()
        }
        
        return JSONResponse(content=response)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


if __name__ == "__main__":
    print("="*70)
    print("Symbol Counting FastAPI Server")
    print("="*70)
    print("\nStarting server on http://127.0.0.1:8000")
    print("\nEndpoints:")
    print("  POST /count - Upload PDF and symbol template")
    print("  POST /count/local - Use files from uploads folder")
    print("  GET /health - Health check")
    print("  GET /docs - API documentation")
    print("\nExample usage:")
    print('  curl -X POST "http://127.0.0.1:8000/count/local" \\')
    print('    -F "pdf_filename=H.pdf" \\')
    print('    -F "symbol_filename=image.png" \\')
    print('    -F "threshold=0.65" \\')
    print('    -F "dpi=300"')
    print("\n" + "="*70 + "\n")
    
    uvicorn.run(app, host="127.0.0.1", port=8000)

