# CAD Drawing BOM Automation System

A comprehensive Python system for extracting, processing, and managing Bill of Materials (BOM) data from CAD drawings in PDF format.

## 📁 Project Structure

This project is organized into logical modules for better maintainability and understanding:

```
BOM_AUTOMATION/
├── core/                    # Core extraction and processing modules
│   ├── extract_cad.py      # Main CAD extraction engine (Vector + OCR)
│   ├── cad_extractor.py    # CAD drawing extractor & MongoDB mapper
│   ├── advanced_extractor.py # Advanced extraction with full features
│   ├── extract_and_store.py # All-in-one extraction and storage pipeline
│   ├── symbol_counter.py   # PDF symbol analysis tool
│   ├── symbol_detector.py  # Symbol detection and counting system
│   ├── table_extractor.py  # Table detection & extraction
│   └── table_cell_mapper.py # Table cell mapping utilities
│
├── api/                     # API servers and endpoints
│   ├── api_server.py       # Flask REST API for symbol detection
│   ├── fastapi_upload_api.py # FastAPI upload endpoint
│   └── web_upload_api.py   # Web upload API
│
├── database/                # Database interface modules
│   ├── mongo_manager.py    # MongoDB management interface
│   ├── db_interface.py     # Database interface abstraction
│   ├── cad_mongo_mapper.py # CAD to MongoDB mapping utilities
│   └── import_to_mongo.py # MongoDB import utilities
│
├── export/                  # Export modules
│   └── erp_export.py       # ERP system export (SAP, Odoo, NetSuite)
│
├── scripts/                 # Utility scripts
│   ├── quickstart.py       # One-command setup and processing
│   ├── example_workflow.py # Example workflow demonstrations
│   ├── query_bom.py        # BOM query utilities
│   └── query_table_mappings.py # Table mapping query utilities
│
├── extractors/             # Text extraction engines
│   ├── ocr_engine.py       # OCR-based text extraction
│   └── vector_text_extractor.py # Vector text extraction
│
├── detectors/               # Detection modules
│   ├── feature_matcher.py  # Feature matching for symbols
│   └── template_matcher.py # Template matching for symbols
│
├── parsers/                 # Parsing utilities
│   └── relation_parser.py  # Symbol-text relation parser
│
├── prototypes/              # Prototype and experimental code
│   ├── extract_cluster_samples.py
│   ├── prototype_auto_symbol_count.py
│   └── run_template_count.py
│
├── tests/                   # Unit tests
│   ├── test_ocr_engine.py
│   └── test_vector_text_extractor.py
│
├── docs/                    # Documentation
│   ├── START_HERE.md       # Quick start guide
│   ├── README.md           # Full technical documentation
│   ├── SYSTEM_SUMMARY.md   # System architecture overview
│   └── ... (other guides)
│
├── config/                  # Configuration files
│   ├── requirements.txt    # Python dependencies
│   └── vc_redist.x64.exe   # Visual C++ redistributable
│
├── files/                   # Output data files
│   ├── bom_export.json
│   ├── bom_structured.json
│   └── ... (other exports)
│
├── inputs/                  # Input templates and files
│   └── templates/
│
├── outputs/                 # Processing outputs
│   ├── samples/
│   └── template_counts/
│
├── uploads/                 # Uploaded PDF files
│
└── README.md               # This file
```

## 🚀 Quick Start

### Installation

1. **Install Python dependencies:**
   ```bash
   pip install -r config/requirements.txt
   ```

2. **Run quickstart:**
   ```bash
   python scripts/quickstart.py H.pdf
   ```

### Basic Usage

#### Extract CAD Data
```bash
python core/extract_cad.py H.pdf --output result.json
```

#### Import to MongoDB
```bash
python database/mongo_manager.py --import files/H_extracted.json
```

#### Query Database
```bash
python database/mongo_manager.py
```

#### Export to ERP Systems
```bash
python export/erp_export.py --format sap
python export/erp_export.py --format odoo
python export/erp_export.py --format netsuite
```

## 📚 Module Descriptions

### Core Modules (`core/`)

- **extract_cad.py**: Main extraction engine combining vector text extraction and OCR fallback
- **symbol_counter.py**: Analyzes PDF content for symbols, characters, and patterns
- **symbol_detector.py**: Detects and counts symbols using template matching
- **table_extractor.py**: Extracts tables from PDF pages
- **table_cell_mapper.py**: Maps table cells to structured key-value pairs

### API Modules (`api/`)

- **api_server.py**: Flask REST API for symbol detection operations
- **fastapi_upload_api.py**: FastAPI-based upload endpoint
- **web_upload_api.py**: Web interface for file uploads

### Database Modules (`database/`)

- **mongo_manager.py**: Interactive MongoDB management tool
- **cad_mongo_mapper.py**: Maps CAD extracted data to MongoDB schema
- **import_to_mongo.py**: Batch import utilities

### Export Modules (`export/`)

- **erp_export.py**: Exports BOM data to various ERP formats (SAP, Odoo, NetSuite)

### Scripts (`scripts/`)

- **quickstart.py**: One-command automation for full pipeline
- **example_workflow.py**: Demonstrates complete workflows
- **query_bom.py**: Query utilities for BOM data
- **query_table_mappings.py**: Query utilities for table mappings

## 🔧 Development

### Running Tests
```bash
pytest tests/
```

### Adding New Extractors
Add new extraction modules to `extractors/` and import them in `core/__init__.py`

### Adding New Detectors
Add new detection modules to `detectors/` following the existing pattern

### Adding New Parsers
Add parsing utilities to `parsers/` for processing extracted data

## 📖 Documentation

See the `docs/` folder for comprehensive documentation:
- **START_HERE.md**: Quick start guide
- **README.md**: Full technical reference
- **SYSTEM_SUMMARY.md**: Architecture overview
- **API guides**: API usage documentation

## 🎯 Key Features

- ✅ Vector text extraction (high accuracy)
- ✅ OCR fallback for scanned documents
- ✅ Symbol detection and counting
- ✅ Table extraction and mapping
- ✅ MongoDB integration
- ✅ ERP system export (SAP, Odoo, NetSuite)
- ✅ REST API endpoints
- ✅ Batch processing support

## 📝 Requirements

See `config/requirements.txt` for full list. Key dependencies:
- pymupdf (PyMuPDF)
- pytesseract
- pymongo
- fastapi
- flask
- opencv-python
- numpy
- pillow

## 🤝 Contributing

When adding new features:
1. Place modules in appropriate folders
2. Update `__init__.py` files for package imports
3. Add tests in `tests/`
4. Update documentation in `docs/`

## 📄 License

[Add your license information here]

## 🔗 Links

- [MongoDB Setup Guide](docs/MONGODB_GUIDE.md)
- [API Documentation](docs/FASTAPI_GUIDE.md)
- [Symbol Detection Guide](docs/SYMBOL_DETECTION_GUIDE.md)





