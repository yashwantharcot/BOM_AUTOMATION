## Web Upload API - Simple PDF Detection Interface

**Status:** ✅ Ready to Use  
**File:** `web_upload_api.py`

---

## Quick Start

### 1. Start the Web Server
```bash
python web_upload_api.py
```

Output:
```
======================================================================
SYMBOL DETECTION - WEB UPLOAD API
======================================================================

Endpoints:
  GET  /              (Upload page with UI)
  POST /detect        (Upload PDF and detect)
  GET  /health        (Health check)

======================================================================
Server running on http://127.0.0.1:5000
======================================================================
```

### 2. Open in Browser
Go to: **http://127.0.0.1:5000**

### 3. Upload PDF
1. Click upload area or drag & drop PDF
2. Click "Upload & Detect" button
3. Wait for results (5-10 seconds per page)
4. View counts in browser
5. Download results as JSON

---

## Features

### Beautiful Web Interface
- ✅ Modern, responsive design
- ✅ Drag & drop PDF upload
- ✅ Real-time progress indicator
- ✅ Professional result display
- ✅ Mobile-friendly layout

### Result Display
- ✅ **Total Symbol Counts** - Summary of all symbols found
- ✅ **Per-Page Breakdown** - Count for each page
- ✅ **Detailed Detections** - Confidence scores for each match
- ✅ **Download JSON** - Export full results

### Error Handling
- ✅ File validation (PDF only)
- ✅ Size limit checking (100MB max)
- ✅ Friendly error messages
- ✅ Symbol template verification

---

## Endpoints

### 1. GET / (Main Page)
**Description:** Upload page with embedded UI  
**Access:** http://127.0.0.1:5000/

**Returns:** HTML page with upload form and results display

### 2. POST /detect
**Description:** Upload PDF and detect symbols  
**Request:** Multipart form data with PDF file  
**Response:** JSON with detection results

**cURL Example:**
```bash
curl -X POST http://127.0.0.1:5000/detect \
  -F "file=@drawing.pdf"
```

**Response Format:**
```json
{
  "file": "drawing.pdf",
  "timestamp": "2025-12-04T10:50:22.123456",
  "total_symbols": {
    "weld_circle": 12,
    "bolt_hole": 8
  },
  "pages": [
    {
      "page": 1,
      "image_width": 2550,
      "image_height": 3300,
      "symbols": [
        {
          "name": "weld_circle",
          "count": 12,
          "detections": [
            {"bbox": [100, 150, 140, 190], "score": 0.93}
          ]
        }
      ]
    }
  ]
}
```

### 3. GET /health
**Description:** Health check and symbol count  
**Response:** JSON status

**cURL Example:**
```bash
curl http://127.0.0.1:5000/health
```

**Response:**
```json
{
  "status": "healthy",
  "symbols_count": 3
}
```

---

## Usage Examples

### Example 1: Web Browser Upload
1. Open http://127.0.0.1:5000
2. Drag PDF onto upload area
3. Click "Upload & Detect"
4. Wait for results
5. Download JSON if needed

### Example 2: cURL Upload
```bash
# Upload PDF
curl -X POST http://127.0.0.1:5000/detect \
  -F "file=@H.pdf" \
  > results.json

# View results
cat results.json | jq '.'
```

### Example 3: JavaScript/Fetch
```javascript
const formData = new FormData();
formData.append('file', pdfFile);

fetch('http://127.0.0.1:5000/detect', {
  method: 'POST',
  body: formData
})
.then(r => r.json())
.then(data => {
  console.log('Total symbols:', data.total_symbols);
  console.log('Page counts:', data.pages);
});
```

---

## Web Interface Features

### Upload Area
- Drag & drop support
- Click to browse
- File type validation
- Size limit indication

### Results Display
- **Summary Card** - Total counts per symbol
- **Per-Page Table** - Breakdown by page
- **Detection Details** - Confidence scores
- **Download Button** - Export as JSON

### Responsive Design
- Works on desktop, tablet, mobile
- Touch-friendly buttons
- Readable on all screen sizes
- Professional color scheme

---

## Requirements

### Software
- Python 3.8+
- Flask (auto-installs)
- Werkzeug (auto-installs)

### MongoDB
- Must have symbols stored in SYMBOL_TEMPLATES collection
- Connection via .env MONGO_URI

### Hardware
- Minimum 512MB RAM
- 100MB disk space for uploads

---

## Troubleshooting

### "No file provided" error
- Make sure you selected a PDF file
- Check file extension is .pdf

### "No symbol templates stored" error
- Upload symbols first using CLI:
  ```bash
  python symbol_detector.py upload "symbol_name" image.png
  ```

### "MongoDB connection failed"
- Check .env file has MONGO_URI
- Verify MongoDB is running
- Test: `python symbol_detector.py list`

### Results take too long
- Large PDFs (100+ pages) will take longer
- Higher DPI (600) is slower than 300
- Normal time is 5-10 seconds per page

### Browser won't connect
- Make sure server is running
- Check port 5000 is not in use
- Try: `netstat -an | grep 5000`

---

## Customization

### Change Port
Edit `web_upload_api.py`:
```python
app.run(host='127.0.0.1', port=8000, debug=False)  # Change 5000 to 8000
```

### Change Upload Size Limit
Edit `web_upload_api.py`:
```python
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB
```

### Change Detection Parameters
Edit `web_upload_api.py`:
```python
results = detector.detect_symbols_in_pdf(
    pdf_path, 
    templates_dict, 
    dpi=600,              # Higher quality
    match_thresh=0.80     # Stricter matching
)
```

---

## Comparison: Web vs CLI vs API

| Feature | Web | CLI | API |
|---------|-----|-----|-----|
| User Interface | ✅ Modern UI | ❌ Terminal | ⚠️ JSON |
| Browser-based | ✅ Yes | ❌ No | ⚠️ No |
| Results Display | ✅ Beautiful | ⚠️ Console | ⚠️ Raw JSON |
| JSON Export | ✅ Yes | ✅ Yes | ✅ Yes |
| Ease of Use | ✅ Very Easy | ⚠️ Medium | ⚠️ Developer |
| Automation | ⚠️ Manual | ✅ Easy | ✅ Easy |

---

## Performance Notes

### Time Breakdown
- Page upload: 1-2 seconds
- PDF processing: 3-8 seconds
- Symbol detection: 2-5 seconds
- Result display: <1 second
- **Total: 5-15 seconds**

### Optimization Tips
1. Use lower DPI (150-300) for faster processing
2. Break large PDFs into smaller files
3. Ensure symbols are clear and high-contrast
4. Tune match_thresh for your symbols

---

## Next Steps

### Basic Usage
1. ✅ Start server: `python web_upload_api.py`
2. ✅ Open browser: http://127.0.0.1:5000
3. ✅ Upload PDF and view results

### Advanced Usage
- Integrate with other applications
- Automate PDF uploads via cURL/API
- Build custom UI on top of /detect endpoint
- Store results in your own database

### Integration
- REST API ready for custom frontends
- JSON output for data processing
- Health check endpoint for monitoring

---

## Support

**Test the endpoints:**
```bash
# Check health
curl http://127.0.0.1:5000/health

# Test detection
curl -X POST http://127.0.0.1:5000/detect \
  -F "file=@test.pdf" | jq '.'
```

**View MongoDB results:**
```bash
python symbol_detector.py summary filename.pdf
```

---

## Files

- **web_upload_api.py** (420+ lines)
  - Flask server
  - HTML template embedded
  - Upload handler
  - Result formatter
  - Health check

---

## Start Using

```bash
python web_upload_api.py
```

Then open: **http://127.0.0.1:5000**

Upload a PDF and see results instantly! 🚀

---

**Status:** ✅ Ready to use immediately  
**One endpoint, beautiful UI, instant results!**
