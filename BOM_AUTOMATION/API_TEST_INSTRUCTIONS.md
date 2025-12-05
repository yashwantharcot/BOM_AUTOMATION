# API Test Instructions - Symbol Detection

## Prerequisites

1. **Install OpenCV** (required for symbol detection):
   ```bash
   pip install opencv-python-headless
   ```
   
   If you get DLL errors on Windows, try:
   ```bash
   pip install opencv-python
   ```
   Or install Visual C++ Redistributable (vc_redist.x64.exe is in config/ folder)

2. **MongoDB Connection**: Ensure `.env` file has `MONGO_URI` set

3. **Required Files**:
   - Symbol template: `inputs/templates/image4545.png`
   - PDF file: `uploads/H.pdf` (or any PDF in uploads folder)

## Method 1: Direct Python Test (Recommended)

This bypasses the API and tests directly:

```bash
python test_direct.py
```

This will:
1. Upload the template from `inputs/templates/image4545.png`
2. Load templates from MongoDB
3. Detect symbols in `uploads/H.pdf`
4. Print results

## Method 2: API Test

### Step 1: Start API Server

```bash
python api/test_symbol_detection_api.py
```

Server starts on `http://localhost:5001`

### Step 2: Upload Template

Using Python:
```python
import requests

with open('inputs/templates/image4545.png', 'rb') as f:
    files = {'file': ('image4545.png', f, 'image/png')}
    data = {'name': 'test_symbol'}
    response = requests.post('http://localhost:5001/api/test/upload-template', files=files, data=data)
    print(response.json())
```

Or using curl:
```bash
curl -X POST http://localhost:5001/api/test/upload-template -F "file=@inputs/templates/image4545.png" -F "name=test_symbol"
```

### Step 3: Test Detection

Using Python:
```python
import requests

with open('uploads/H.pdf', 'rb') as f:
    files = {'file': ('H.pdf', f, 'application/pdf')}
    response = requests.post('http://localhost:5001/api/test/detect', files=files)
    result = response.json()
    print(f"Status: {result['status']}")
    print(f"Symbol counts: {result['results']['symbol_counts']}")
```

Or using curl:
```bash
curl -X POST http://localhost:5001/api/test/detect -F "file=@uploads/H.pdf"
```

### Step 4: View Templates

```bash
curl http://localhost:5001/api/test/templates
```

## Expected Output

The detection will return:
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
            "detections": [...]
          }
        }
      }
    ]
  }
}
```

## Troubleshooting

### OpenCV DLL Error
- Install Visual C++ Redistributable
- Or use `opencv-python-headless` instead of `opencv-python`

### MongoDB Connection Error
- Check `.env` file has `MONGO_URI` set
- Ensure MongoDB is running
- Check network connectivity

### No Templates Found
- Upload template first using `/api/test/upload-template`
- Check MongoDB connection

### No Symbols Detected
- Lower threshold: Modify `match_thresh=0.75` to `0.65` in code
- Check template image quality
- Verify PDF contains the symbol

## API Endpoints

- `GET /api/test/health` - Health check
- `POST /api/test/upload-template` - Upload symbol template (form: file, name)
- `POST /api/test/detect` - Detect symbols in PDF (form: file)
- `GET /api/test/templates` - List uploaded templates
- `POST /api/test/clear` - Clear all templates





