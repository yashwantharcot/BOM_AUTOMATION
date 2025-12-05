## Symbol Detection System - Installation & Setup

**Status:** ✅ Ready to use  
**Tested:** December 4, 2025  
**Python Version:** 3.8+

---

## Prerequisites

- ✅ Python 3.8 or higher
- ✅ MongoDB database (utkarshproduction)
- ✅ `.env` file with `MONGO_URI`

---

## Installation Steps

### 1. Verify Python Installation

```bash
python --version
```

Expected output: `Python 3.x.x` (3.8 or higher)

### 2. Verify MongoDB Connection

Check that your `.env` file contains:
```
MONGO_URI=mongodb://[user:password@]host:port/database
```

Example:
```
MONGO_URI=mongodb://72.60.219.113:29048/utkarshproduction
```

### 3. Test MongoDB Connection

```bash
python symbol_detector.py list
```

Expected output:
```
[OK] Connected to MongoDB
======================================================================
STORED SYMBOLS
======================================================================
No symbols stored
```

If you see this, MongoDB is working! ✅

### 4. Install Required Dependencies (Automatic)

The system automatically installs dependencies when first run:

```bash
python symbol_detector.py list
```

This will install:
- ✅ pymupdf (PDF processing)
- ✅ pymongo (MongoDB driver)
- ✅ pillow (Image processing)
- ✅ numpy (Arrays)
- ✅ flask (Web server)

**Note:** OpenCV (cv2) is optional. If unavailable, the system uses Pillow instead.

### 5. Verify Installation

```bash
ls -la *.py
```

You should see:
- ✅ `symbol_detector.py` (565+ lines)
- ✅ `api_server.py` (410+ lines)
- ✅ `example_workflow.py` (250+ lines)

---

## Quick Test

### Test 1: MongoDB Connection
```bash
python symbol_detector.py list
```

### Test 2: Create Sample Symbols
```bash
python example_workflow.py
```

This will:
1. ✅ Create 3 sample symbols
2. ✅ Upload to MongoDB
3. ✅ Test detection on H.pdf
4. ✅ Store results in MongoDB

### Test 3: API Server
```bash
python api_server.py
```

Output:
```
======================================================================
SYMBOL DETECTION REST API
======================================================================

Endpoints:
  GET  /api/v1/health
  GET  /api/v1/symbols
  ...

Server running on http://127.0.0.1:5000
======================================================================
```

Press `Ctrl+C` to stop.

---

## Troubleshooting Installation

### Issue: "ModuleNotFoundError: No module named 'pymongo'"

**Solution:** The system will auto-install it. If not:
```bash
pip install pymongo pymupdf pillow numpy
```

### Issue: ".env file not found"

**Solution:** Create `.env` in `d:\BOM_AUTOMATION\`:
```
MONGO_URI=mongodb://72.60.219.113:29048/utkarshproduction
```

### Issue: "MongoDB connection failed"

**Solution:** Verify MongoDB URI:
```bash
# Test connection (replace with your actual URI)
python -c "from pymongo import MongoClient; MongoClient('mongodb://72.60.219.113:29048/utkarshproduction').admin.command('ping')"
```

### Issue: "OpenCV not available"

**This is OK!** The system works with or without OpenCV. If you want OpenCV:
```bash
pip install opencv-python
```

Note: OpenCV on Windows may require Visual C++ runtime libraries.

### Issue: "Flask ImportError"

**Solution:** Install Flask:
```bash
pip install flask
```

---

## Dependency Details

### Automatically Installed

| Package | Purpose | Version | Required |
|---------|---------|---------|----------|
| pymupdf | PDF rasterization | 1.23+ | ✅ Yes |
| pymongo | MongoDB driver | 4.0+ | ✅ Yes |
| pillow | Image processing | 9.0+ | ✅ Yes |
| numpy | Array operations | 1.20+ | ✅ Yes |
| python-dotenv | .env file support | 1.0+ | ✅ Yes |
| flask | REST API | 2.0+ | ⚠️ For API server |
| werkzeug | Flask utilities | 2.0+ | ⚠️ For API server |

### Optional

| Package | Purpose | When needed |
|---------|---------|------------|
| opencv-python | Image matching | If available (better performance) |
| scikit-image | Image processing | Future enhancements |

---

## File Organization

```
d:\BOM_AUTOMATION\
├── symbol_detector.py          # Main CLI tool (565 lines)
├── api_server.py               # REST API server (410 lines)
├── example_workflow.py         # Example usage (250 lines)
├── SYMBOL_DETECTION_GUIDE.md   # Full documentation (500+ lines)
├── SYMBOL_DETECTION_READY.md   # Quick start guide (300+ lines)
├── SETUP_INSTALLATION.md       # This file
├── .env                        # MongoDB connection
├── H.pdf                       # Test drawing
├── uploads/                    # PDF storage directory
├── sample_symbols/             # Example symbols (created by example_workflow.py)
└── README.md                   # Project overview
```

---

## Environment Variables

Create `.env` file in `d:\BOM_AUTOMATION\`:

```bash
# Required
MONGO_URI=mongodb://72.60.219.113:29048/utkarshproduction

# Optional
FLASK_ENV=production
DEBUG=0
MAX_CONTENT_LENGTH=104857600  # 100MB max upload
```

---

## System Requirements

### Minimum
- **Python:** 3.8+
- **Memory:** 512 MB RAM
- **Disk:** 100 MB free space
- **Network:** Connection to MongoDB

### Recommended
- **Python:** 3.10+
- **Memory:** 2 GB RAM
- **Disk:** 500 MB free space
- **Storage:** MongoDB with 1 GB space

### For Full Features (with OpenCV)
- **Memory:** 4 GB RAM
- **CPU:** 2+ cores recommended
- **GPU:** NVIDIA GPU (optional, for future ML models)

---

## Verification Checklist

- [ ] Python 3.8+ installed
- [ ] `.env` file with `MONGO_URI` created
- [ ] `python symbol_detector.py list` returns successfully
- [ ] MongoDB connection verified
- [ ] Example scripts created
- [ ] All Python files compile without errors

✅ If all checked, you're ready to use the system!

---

## First Commands

### 1. List existing symbols
```bash
python symbol_detector.py list
```

### 2. Upload a symbol
```bash
python symbol_detector.py upload "weld_circle" your_symbol.png
```

### 3. Detect in PDF
```bash
python symbol_detector.py detect your_drawing.pdf --store
```

### 4. Query results
```bash
python symbol_detector.py summary your_drawing.pdf
```

### 5. Start API server
```bash
python api_server.py
```

---

## Getting Help

**If something doesn't work:**

1. **Check MongoDB:** `python symbol_detector.py list`
2. **Review logs:** Check console output for error messages
3. **Test individually:** Run each component separately
4. **Check .env:** Verify `MONGO_URI` is correct
5. **Review documentation:** See `SYMBOL_DETECTION_GUIDE.md`

---

## Next Steps

- [ ] Upload symbol templates
- [ ] Test detection on sample PDFs
- [ ] Start REST API server
- [ ] Integrate with your application

**See `SYMBOL_DETECTION_READY.md` for quick start guide**

---

**Status:** ✅ Installation guide complete. You're ready to go!
