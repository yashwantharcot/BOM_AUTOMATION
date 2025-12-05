# Module Stubs

This folder contains initial stubs for core modules used in the BOM automation project.

Files:
- `extractors/vector_text_extractor.py` - vector text extraction using PyMuPDF
- `extractors/ocr_engine.py` - Tesseract OCR wrapper
- `detectors/template_matcher.py` - OpenCV template matching helper
- `detectors/feature_matcher.py` - ORB feature-based matching helper
- `parsers/relation_parser.py` - simple spatial relation heuristics
- `db_interface.py` - minimal DB wrapper (Mongo or in-memory fallback)
- `tests/` - basic unit tests for the stubs

Run quick syntax check:

```bash
python -m py_compile extractors/vector_text_extractor.py \
    extractors/ocr_engine.py detectors/template_matcher.py \
    detectors/feature_matcher.py parsers/relation_parser.py db_interface.py
```

Run tests (install pytest first):

```bash
pip install -r requirements.txt
pytest -q
```
