#!/usr/bin/env python3
"""
FastAPI Symbol Extraction & Counting API
Upload PDF -> Extract symbols -> Return counts with symbol images
"""

import os
import json
import base64
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict
import tempfile

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

# Import extraction modules
from core.vector_symbol_extractor import VectorSymbolExtractor

# FastAPI app
app = FastAPI(
    title="Symbol Extraction & Counting API",
    description="Upload PDF to extract symbols and get counts with symbol representations",
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

# Directories
UPLOAD_FOLDER = Path("uploads")
UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER = Path("outputs")
OUTPUT_FOLDER.mkdir(exist_ok=True)
SYMBOLS_FOLDER = OUTPUT_FOLDER / "vector_symbols"
SYMBOLS_FOLDER.mkdir(exist_ok=True)


def image_to_base64(image_path: Path) -> str:
    """Convert image file to base64 string"""
    try:
        with open(image_path, 'rb') as f:
            image_data = f.read()
            base64_str = base64.b64encode(image_data).decode('utf-8')
            # Determine image type
            ext = image_path.suffix.lower()
            if ext == '.png':
                return f"data:image/png;base64,{base64_str}"
            elif ext in ['.jpg', '.jpeg']:
                return f"data:image/jpeg;base64,{base64_str}"
            else:
                return f"data:image/png;base64,{base64_str}"
    except Exception as e:
        print(f"[WARN] Failed to encode image {image_path}: {e}")
        return ""


@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "Symbol Extraction & Counting API",
        "version": "1.0.0",
        "endpoints": {
            "/extract": "POST - Upload PDF to extract symbols and get counts",
            "/extract/local": "POST - Extract symbols from PDF in uploads folder",
            "/health": "GET - Health check"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.post("/extract")
async def extract_symbols(
    pdf_file: UploadFile = File(..., description="PDF file to extract symbols from"),
    min_count: Optional[int] = Form(1, description="Minimum occurrences to include symbol (default: 1)"),
    include_images: Optional[bool] = Form(True, description="Include base64-encoded symbol images"),
    save_templates: Optional[bool] = Form(True, description="Save symbol templates to disk")
):
    """
    Extract symbols from PDF and return counts with symbol representations
    
    Parameters:
    - pdf_file: PDF file to analyze
    - min_count: Minimum occurrences to include symbol (default: 1)
    - include_images: Include base64-encoded images in response (default: True)
    - save_templates: Save symbol templates to outputs/vector_symbols/ (default: True)
    
    Returns:
    - symbols: List of symbols with counts and representations
    - summary: Overall statistics
    - pages: Per-page breakdown
    """
    
    # Validate PDF file
    if not pdf_file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    pdf_path = None
    
    try:
        # Save uploaded PDF temporarily
        pdf_path = UPLOAD_FOLDER / f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{pdf_file.filename}"
        with open(pdf_path, 'wb') as f:
            content = await pdf_file.read()
            f.write(content)
        
        print(f"[API] Extracting symbols from {pdf_file.filename}")
        
        # Extract symbols using vector extractor
        extractor = VectorSymbolExtractor(str(pdf_path))
        results = extractor.extract_all_pages()
        
        # Save templates if requested
        template_files = []
        if save_templates:
            template_files = extractor.save_symbol_templates(
                output_dir=str(SYMBOLS_FOLDER),
                min_count=min_count
            )
        
        extractor.close()
        
        # Build response with symbol representations
        symbols_list = []
        symbol_templates_map = {Path(f).stem: f for f in template_files}
        
        # Group symbols by signature across all pages
        all_symbols_by_sig = {}
        for page_result in results['pages']:
            for sym in page_result['symbols']:
                sig = sym['signature']
                if sig not in all_symbols_by_sig:
                    all_symbols_by_sig[sig] = {
                        'signature': sig,
                        'instances': [],
                        'bbox': sym['bbox'],
                        'width': sym['width'],
                        'height': sym['height'],
                        'area': sym['area'],
                        'aspect_ratio': sym['aspect_ratio']
                    }
                all_symbols_by_sig[sig]['instances'].append({
                    'page': page_result['page'],
                    'bbox': sym['bbox']
                })
        
        # Build symbols list with counts and images
        for sig, sym_data in all_symbols_by_sig.items():
            count = len(sym_data['instances'])
            
            if count < min_count:
                continue
            
            symbol_item = {
                'signature': sig,
                'count': count,
                'width': sym_data['width'],
                'height': sym_data['height'],
                'area': sym_data['area'],
                'aspect_ratio': sym_data['aspect_ratio'],
                'instances': sym_data['instances']
            }
            
            # Add image representation if available
            if include_images:
                # Find template file for this signature
                template_path = None
                for template_file in template_files:
                    if sig in Path(template_file).stem or any(
                        sig_hash in Path(template_file).stem 
                        for sig_hash in [sig[:8], sig[-8:]]
                    ):
                        template_path = Path(template_file)
                        break
                
                if template_path and template_path.exists():
                    symbol_item['image_base64'] = image_to_base64(template_path)
                    symbol_item['image_filename'] = template_path.name
                else:
                    symbol_item['image_base64'] = None
                    symbol_item['image_filename'] = None
            
            symbols_list.append(symbol_item)
        
        # Sort by count (descending)
        symbols_list.sort(key=lambda x: x['count'], reverse=True)
        
        # Build response
        response = {
            "status": "success",
            "pdf_filename": pdf_file.filename,
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_symbols": sum(s['count'] for s in symbols_list),
                "unique_symbols": len(symbols_list),
                "total_pages": results['summary']['total_pages'],
                "symbols_with_images": sum(1 for s in symbols_list if s.get('image_base64'))
            },
            "symbols": symbols_list,
            "pages": [
                {
                    "page": page_result['page'],
                    "symbol_count": page_result['total_symbols'],
                    "unique_patterns": page_result['unique_patterns']
                }
                for page_result in results['pages']
            ]
        }
        
        return JSONResponse(content=response)
    
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")
    
    finally:
        # Clean up temporary PDF file
        if pdf_path and pdf_path.exists():
            try:
                pdf_path.unlink()
            except:
                pass


@app.post("/extract/local")
async def extract_symbols_local(
    pdf_filename: str = Form(..., description="PDF filename in uploads folder or root"),
    min_count: Optional[int] = Form(1),
    include_images: Optional[bool] = Form(True),
    save_templates: Optional[bool] = Form(True)
):
    """
    Extract symbols from PDF file already in the system
    
    Parameters:
    - pdf_filename: Name of PDF file (in uploads folder or root directory)
    - min_count: Minimum occurrences to include symbol
    - include_images: Include base64-encoded images
    - save_templates: Save symbol templates to disk
    """
    
    # Find PDF file
    pdf_path = UPLOAD_FOLDER / pdf_filename
    if not pdf_path.exists():
        pdf_path = Path(pdf_filename)
        if not pdf_path.exists():
            raise HTTPException(status_code=404, detail=f"PDF file not found: {pdf_filename}")
    
    try:
        print(f"[API] Extracting symbols from {pdf_filename}")
        
        # Extract symbols
        extractor = VectorSymbolExtractor(str(pdf_path))
        results = extractor.extract_all_pages()
        
        # Save templates if requested
        template_files = []
        if save_templates:
            template_files = extractor.save_symbol_templates(
                output_dir=str(SYMBOLS_FOLDER),
                min_count=min_count
            )
        
        extractor.close()
        
        # Build response (same logic as /extract endpoint)
        symbols_list = []
        all_symbols_by_sig = {}
        
        for page_result in results['pages']:
            for sym in page_result['symbols']:
                sig = sym['signature']
                if sig not in all_symbols_by_sig:
                    all_symbols_by_sig[sig] = {
                        'signature': sig,
                        'instances': [],
                        'bbox': sym['bbox'],
                        'width': sym['width'],
                        'height': sym['height'],
                        'area': sym['area'],
                        'aspect_ratio': sym['aspect_ratio']
                    }
                all_symbols_by_sig[sig]['instances'].append({
                    'page': page_result['page'],
                    'bbox': sym['bbox']
                })
        
        for sig, sym_data in all_symbols_by_sig.items():
            count = len(sym_data['instances'])
            
            if count < min_count:
                continue
            
            symbol_item = {
                'signature': sig,
                'count': count,
                'width': sym_data['width'],
                'height': sym_data['height'],
                'area': sym_data['area'],
                'aspect_ratio': sym_data['aspect_ratio'],
                'instances': sym_data['instances']
            }
            
            if include_images:
                template_path = None
                for template_file in template_files:
                    if sig in Path(template_file).stem:
                        template_path = Path(template_file)
                        break
                
                if template_path and template_path.exists():
                    symbol_item['image_base64'] = image_to_base64(template_path)
                    symbol_item['image_filename'] = template_path.name
                else:
                    symbol_item['image_base64'] = None
                    symbol_item['image_filename'] = None
            
            symbols_list.append(symbol_item)
        
        symbols_list.sort(key=lambda x: x['count'], reverse=True)
        
        response = {
            "status": "success",
            "pdf_filename": pdf_filename,
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_symbols": sum(s['count'] for s in symbols_list),
                "unique_symbols": len(symbols_list),
                "total_pages": results['summary']['total_pages']
            },
            "symbols": symbols_list,
            "pages": [
                {
                    "page": page_result['page'],
                    "symbol_count": page_result['total_symbols'],
                    "unique_patterns": page_result['unique_patterns']
                }
                for page_result in results['pages']
            ]
        }
        
        return JSONResponse(content=response)
    
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


if __name__ == "__main__":
    print("="*70)
    print("Symbol Extraction & Counting FastAPI Server")
    print("="*70)
    print("\nStarting server on http://127.0.0.1:8001")
    print("\nEndpoints:")
    print("  POST /extract - Upload PDF to extract symbols")
    print("  POST /extract/local - Extract from PDF in uploads folder")
    print("  GET /health - Health check")
    print("  GET /docs - API documentation (Swagger UI)")
    print("\nExample usage:")
    print('  curl -X POST "http://127.0.0.1:8001/extract/local" \\')
    print('    -F "pdf_filename=H.pdf" \\')
    print('    -F "min_count=2" \\')
    print('    -F "include_images=true"')
    print("\n" + "="*70 + "\n")
    
    uvicorn.run(app, host="127.0.0.1", port=8001)

