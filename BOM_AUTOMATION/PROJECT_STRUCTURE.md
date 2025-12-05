# Project Structure Guide

This document explains the organization of the BOM Automation project.

## 📂 Folder Organization

### `/core` - Core Extraction Modules
Contains the main extraction and processing engines:
- **extract_and_store.py**: Complete pipeline for extraction and MongoDB storage
- **cad_extractor.py**: CAD drawing extractor with MongoDB mapping
- **advanced_extractor.py**: Advanced extraction with full features
- **symbol_counter.py**: PDF symbol and character analysis
- **symbol_detector.py**: Symbol detection using template matching
- **table_extractor.py**: Table detection and extraction from PDFs
- **table_cell_mapper.py**: Maps table cells to structured data

**Usage:**
```python
from core.symbol_detector import SymbolDetector
from core.symbol_counter import SymbolCounter
```

### `/api` - API Servers
REST API endpoints for the system:
- **api_server.py**: Flask-based symbol detection API
- **fastapi_upload_api.py**: FastAPI upload endpoint
- **web_upload_api.py**: Web interface for uploads

**Usage:**
```bash
python api/api_server.py
```

### `/database` - Database Modules
MongoDB integration and management:
- **mongo_manager.py**: Interactive MongoDB management tool
- **db_interface.py**: Database interface abstraction layer
- **cad_mongo_mapper.py**: Maps CAD data to MongoDB schema
- **import_to_mongo.py**: Batch import utilities

**Usage:**
```bash
python database/mongo_manager.py --import data.json
```

### `/export` - Export Modules
ERP system integration:
- **erp_export.py**: Exports to SAP, Odoo, NetSuite formats

**Usage:**
```bash
python export/erp_export.py --format sap
```

### `/scripts` - Utility Scripts
Helper scripts for common tasks:
- **quickstart.py**: One-command automation
- **example_workflow.py**: Example workflows
- **query_bom.py**: BOM query utilities
- **query_table_mappings.py**: Table mapping queries

**Usage:**
```bash
python scripts/quickstart.py H.pdf
```

### `/extractors` - Text Extraction Engines
Low-level extraction modules:
- **ocr_engine.py**: OCR-based text extraction
- **vector_text_extractor.py**: Vector text extraction from PDFs

### `/detectors` - Detection Modules
Symbol and feature detection:
- **feature_matcher.py**: Feature matching algorithms
- **template_matcher.py**: Template matching for symbols

### `/parsers` - Parsing Utilities
Data parsing and relation extraction:
- **relation_parser.py**: Links symbols to text based on proximity

### `/prototypes` - Experimental Code
Prototype and experimental implementations:
- **extract_cluster_samples.py**
- **prototype_auto_symbol_count.py**
- **run_template_count.py**

### `/tests` - Unit Tests
Test files for modules:
- **test_ocr_engine.py**
- **test_vector_text_extractor.py**

### `/docs` - Documentation
All project documentation:
- **START_HERE.md**: Quick start guide
- **README.md**: Full documentation
- **SYSTEM_SUMMARY.md**: Architecture overview
- Various API and feature guides

### `/config` - Configuration
Configuration files:
- **requirements.txt**: Python dependencies
- **vc_redist.x64.exe**: Visual C++ redistributable

### `/files` - Output Data
Generated data files:
- JSON exports
- CSV exports
- Structured BOM data

### `/inputs` - Input Files
Input templates and sample files

### `/outputs` - Processing Outputs
Processing results and debug outputs

### `/uploads` - Uploaded Files
User-uploaded PDF files

## 🔄 Import Patterns

### Importing from core modules:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.symbol_detector import SymbolDetector
```

### Importing from same-level modules:
```python
from .symbol_detector import SymbolDetector
```

### Running scripts:
```bash
# From project root
python scripts/quickstart.py H.pdf

# Or with full path
python core/extract_cad.py H.pdf --output result.json
```

## 📝 Adding New Modules

1. **Core functionality** → `/core`
2. **API endpoints** → `/api`
3. **Database operations** → `/database`
4. **Export formats** → `/export`
5. **Utility scripts** → `/scripts`
6. **New extractors** → `/extractors`
7. **New detectors** → `/detectors`
8. **New parsers** → `/parsers`

Remember to:
- Add `__init__.py` if creating new package folders
- Update imports in dependent files
- Add tests in `/tests`
- Update documentation in `/docs`





