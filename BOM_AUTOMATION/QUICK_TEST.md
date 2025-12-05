# Quick Test Guide - Symbol Detection API

## Step 1: Start the API Server

```bash
python api/test_symbol_detection_api.py
```

The API will start on `http://localhost:5001`

## Step 2: Upload Symbol Template

Using curl:
```bash
curl -X POST http://localhost:5001/api/test/upload-template \
  -F "file=@inputs/templates/image4545.png" \
  -F "name=test_symbol"
```

Using Python:
```python
import requests

with open('inputs/templates/image4545.png', 'rb') as f:
    files = {'file': ('image4545.png', f, 'image/png')}
    data = {'name': 'test_symbol'}
    response = requests.post('http://localhost:5001/api/test/upload-template', files=files, data=data)
    print(response.json())
```

## Step 3: Test Detection on PDF

Using curl:
```bash
curl -X POST http://localhost:5001/api/test/detect \
  -F "file=@uploads/H.pdf"
```

Using Python:
```python
import requests

with open('uploads/H.pdf', 'rb') as f:
    files = {'file': ('H.pdf', f, 'application/pdf')}
    response = requests.post('http://localhost:5001/api/test/detect', files=files)
    print(response.json())
```

## Step 4: View Results

The response will include:
- Total symbol counts per symbol type
- Page-by-page results
- Detection details with bounding boxes

## Alternative: Direct Python Test

If API has issues, you can test directly:

```python
from core.symbol_detector import SymbolTemplate, SymbolDetector
from pathlib import Path

# Upload template
template_mgr = SymbolTemplate()
template_mgr.upload_symbol("test_symbol", "inputs/templates/image4545.png")
template_mgr.close()

# Load templates
template_mgr = SymbolTemplate()
symbols = template_mgr.list_symbols()
templates_dict = {}
for sym in symbols:
    img = template_mgr.get_symbol(sym['symbol_name'])
    if img is not None:
        templates_dict[sym['symbol_name']] = img
template_mgr.close()

# Detect
detector = SymbolDetector()
results = detector.detect_symbols_in_pdf("uploads/H.pdf", templates_dict, dpi=300)

# Print results
for page_result in results['pages']:
    print(f"Page {page_result['page'] + 1}:")
    for symbol_name, symbol_data in page_result['symbols'].items():
        print(f"  {symbol_name}: {symbol_data['count']}")
```





