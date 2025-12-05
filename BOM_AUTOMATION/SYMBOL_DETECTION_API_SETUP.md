# Symbol Detection API - Setup Complete

## ✅ What Has Been Created

1. **Test API Server** (`api/test_symbol_detection_api.py`)
   - Flask-based REST API for symbol detection
   - Endpoints for uploading templates and detecting symbols
   - Runs on `http://localhost:5001`

2. **Test Scripts**:
   - `test_symbol_detection.py` - API client test script
   - `test_direct.py` - Direct test using MongoDB
   - `test_symbol_simple.py` - Standalone test (no MongoDB)

3. **Documentation**:
   - `API_TEST_INSTRUCTIONS.md` - Detailed API usage
   - `QUICK_TEST.md` - Quick reference guide

## 🚀 Quick Start

### Option 1: Simple Standalone Test (Recommended)

This test doesn't require MongoDB or API server:

```bash
python test_symbol_simple.py
```

**Requirements:**
- OpenCV (opencv-python)
- PyMuPDF
- NumPy

### Option 2: API Server Test

1. **Start API Server:**
   ```bash
   python api/test_symbol_detection_api.py
   ```

2. **Upload Template:**
   ```bash
   python test_symbol_detection.py
   ```
   Or manually:
   ```python
   import requests
   with open('inputs/templates/image4545.png', 'rb') as f:
       files = {'file': ('image4545.png', f, 'image/png')}
       data = {'name': 'test_symbol'}
       response = requests.post('http://localhost:5001/api/test/upload-template', files=files, data=data)
       print(response.json())
   ```

3. **Detect Symbols:**
   ```python
   import requests
   with open('uploads/H.pdf', 'rb') as f:
       files = {'file': ('H.pdf', f, 'application/pdf')}
       response = requests.post('http://localhost:5001/api/test/detect', files=files)
       result = response.json()
       print(f"Symbol counts: {result['results']['symbol_counts']}")
   ```

## 🔧 Troubleshooting OpenCV DLL Error

### Windows Fix:

1. **Install Visual C++ Redistributable:**
   - File is in `config/vc_redist.x64.exe`
   - Run it to install

2. **Reinstall OpenCV:**
   ```bash
   pip uninstall opencv-python opencv-python-headless
   pip install opencv-python
   ```

3. **Alternative - Use opencv-python-headless:**
   ```bash
   pip install opencv-python-headless
   ```

4. **Check Python Architecture:**
   - Ensure Python is 64-bit
   - OpenCV must match Python architecture

### Verify OpenCV Installation:

```python
import cv2
print(cv2.__version__)
```

## 📋 API Endpoints

### Test API (`api/test_symbol_detection_api.py`)

- `GET /api/test/health` - Health check
- `POST /api/test/upload-template` - Upload symbol template
  - Form data: `file` (image), `name` (symbol name)
- `POST /api/test/detect` - Detect symbols in PDF
  - Form data: `file` (PDF)
- `GET /api/test/templates` - List uploaded templates
- `POST /api/test/clear` - Clear all templates

### Example Response:

```json
{
  "status": "success",
  "results": {
    "pdf_file": "H.pdf",
    "symbol_counts": {
      "test_symbol": 12
    },
    "page_results": [
      {
        "page": 1,
        "symbols": {
          "test_symbol": {
            "count": 12,
            "detections": [
              {
                "bbox": [100, 150, 140, 190],
                "score": 0.85,
                "rotation": 0,
                "scale": 1.0
              }
            ]
          }
        }
      }
    ]
  }
}
```

## 🎯 Features

1. **Multi-Scale Detection**: Detects symbols at different scales (0.8x to 1.2x)
2. **Multi-Rotation**: Handles rotations (0°, 90°, 180°, 270°)
3. **Non-Maximum Suppression**: Removes duplicate detections
4. **Page-by-Page Results**: Detailed results for each PDF page
5. **Bounding Boxes**: Precise location of each detected symbol

## 📝 Test Files

- **Template**: `inputs/templates/image4545.png`
- **PDFs**: `uploads/H.pdf` (or any PDF in uploads folder)

## 🔍 Detection Parameters

Default parameters (can be adjusted in code):
- **DPI**: 300 (PDF rasterization resolution)
- **Threshold**: 0.75 (confidence threshold)
- **Scales**: [0.8, 0.9, 1.0, 1.1, 1.2]
- **Rotations**: [0, 90, 180, 270]
- **NMS IoU Threshold**: 0.25

## 📚 Next Steps

1. **Fix OpenCV DLL issue** (see troubleshooting above)
2. **Run simple test**: `python test_symbol_simple.py`
3. **Start API server**: `python api/test_symbol_detection_api.py`
4. **Test with your PDFs**: Upload templates and test detection

## 💡 Usage Example

```python
# 1. Upload template
import requests

with open('inputs/templates/image4545.png', 'rb') as f:
    files = {'file': ('image4545.png', f, 'image/png')}
    data = {'name': 'weld_symbol'}
    response = requests.post('http://localhost:5001/api/test/upload-template', files=files, data=data)
    print(response.json())

# 2. Detect symbols
with open('uploads/H.pdf', 'rb') as f:
    files = {'file': ('H.pdf', f, 'application/pdf')}
    response = requests.post('http://localhost:5001/api/test/detect', files=files)
    result = response.json()
    
    # Print results
    print(f"Total symbols found: {sum(result['results']['symbol_counts'].values())}")
    for symbol_name, count in result['results']['symbol_counts'].items():
        print(f"  {symbol_name}: {count}")
```

## ⚠️ Known Issues

1. **OpenCV DLL Error**: Common on Windows - see troubleshooting section
2. **MongoDB Required**: For API server (test_symbol_simple.py doesn't need it)
3. **Template Quality**: Low-quality templates may have false positives/negatives

## ✅ Status

- ✅ API endpoints created
- ✅ Test scripts ready
- ✅ Documentation complete
- ⚠️ OpenCV DLL issue needs resolution (Windows-specific)

Once OpenCV is properly installed, all tests should work correctly!





