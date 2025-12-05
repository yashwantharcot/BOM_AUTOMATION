# 📊 TABLE CELL MAPPING GUIDE

## Overview

Your PDF table cells are now correctly mapped as **key-value pairs** and stored in MongoDB collection `TABLE_MAPPINGS`.

---

## ✅ What Was Extracted from H.pdf

### Tables Found
- **3 tables** extracted from page 1
- **Total rows**: 12 (7 + 3 + 2)
- **Total columns**: 6 (main table is 6 columns)

### Data Extracted

#### Table 0 (Main Table - 7x6)
```
Page: 1
Rows: 7
Columns: 6

Header Data (Key-Value):
  date: 2008-01-13
```

#### Table 1 (Sub-table - 3x1)
```
Page: 1
Rows: 3
Columns: 1
```

#### Table 2 (Info Table - 2x1)
```
Page: 1
Rows: 2
Columns: 1

Header Data (Key-Value):
  date: 2008-01-13
```

---

## 🗄️ MongoDB Storage

### Collection: `TABLE_MAPPINGS`

Each table stored as document:
```json
{
  "filename": "H.pdf",
  "page": 1,
  "table_index": 0,
  "raw_rows": 7,
  "raw_columns": 6,
  "key_value_pairs": {
    "item_number": "001",
    "drawing_number": "762849",
    "mass_kg": "195",
    "date": "2008-01-13",
    "...": "..."
  },
  "header_data": {
    "date": "2008-01-13"
  },
  "import_date": "2025-12-04T10:44:33.417000"
}
```

---

## 🔍 Query Table Mappings

### View Statistics
```bash
python query_table_mappings.py stats
```
Output:
```
Table Mappings Statistics:
  Total Stored: 3
  Files: 1
    H.pdf: 3 mappings
  Pages: [1]
```

### Show All Tables
```bash
python query_table_mappings.py all
```

### Show Tables from File
```bash
python query_table_mappings.py file H.pdf
```

### Show Tables from Page
```bash
python query_table_mappings.py page 1
```

### Find by Key Name
```bash
python query_table_mappings.py key "date"
python query_table_mappings.py key "item_number"
```

### Find by Value
```bash
python query_table_mappings.py value "2008-01-13"
python query_table_mappings.py value "A3"
```

### Export to JSON
```bash
python query_table_mappings.py export
# Creates: table_mappings_export.json
```

### Export Specific File
```bash
python query_table_mappings.py export-file H.pdf
# Creates: H_table_export.json
```

---

## 📋 Cell Mapping Examples

### From H.pdf

**Key-Value Pairs Extracted:**
```
item_number: 001
drawing_number: 762849
mass_kg: 195
certificate: EN 10204:2004-3.1
format: A3
status: KAJAY
date: 2008-01-13
material: EN 10025:2004 -S 355J2+N + Option 5
scale: 1:10
description: REAR FOUNDATION, TOP PLATE
```

---

## 🛠️ Scripts Available

### 1. **`table_cell_mapper.py`** - Extract & Map
```bash
# Extract tables and map cells
python table_cell_mapper.py H.pdf

# Extract and store in MongoDB
python table_cell_mapper.py H.pdf --store-mongo
```

Output:
- `H_table_mappings.json` - Local export
- MongoDB storage in `TABLE_MAPPINGS` collection

### 2. **`query_table_mappings.py`** - Query & Export
```bash
# Interactive mode
python query_table_mappings.py

# Command mode
python query_table_mappings.py stats
python query_table_mappings.py file H.pdf
python query_table_mappings.py export
```

---

## 📊 Mapping Strategy

### How Cells Are Mapped to Key-Value Pairs

**Strategy 1: First Column as Key**
```
| Key        | Value              |
|------------|-------------------|
| Item No.   | 001               |
| Mass (kg)  | 195               |
| Material   | EN 10025:2004...  |
```
Becomes:
```json
{
  "item_number": "001",
  "mass_kg": "195",
  "material": "EN 10025:2004..."
}
```

**Strategy 2: Header Extraction**
```
Key-Value pairs extracted from headers:
- item_number
- drawing_number
- mass_kg
- certificate
- format
- date
- material
- scale
- description
```

**Strategy 3: Text Pattern Recognition**
```
Regex patterns detect:
- Dates: YYYY-MM-DD or DD/MM/YYYY
- Numbers: Quantities, weights, scales
- Materials: EN standards, specifications
- Descriptions: Item descriptions, titles
```

---

## 💾 Export Formats

### JSON Export
```bash
python query_table_mappings.py export
# Creates: table_mappings_export.json
```

Content:
```json
{
  "table_0": {
    "filename": "H.pdf",
    "page": 1,
    "table_index": 0,
    "raw_rows": 7,
    "raw_columns": 6,
    "key_value_pairs": {...},
    "header_data": {...}
  },
  "table_1": {...},
  "table_2": {...}
}
```

### File-Specific Export
```bash
python query_table_mappings.py export-file H.pdf
# Creates: H_table_export.json
```

---

## 🔄 Integration with MongoDB

### Documents in TABLE_MAPPINGS Collection

**3 documents (one per table)**

Document 1: Main Table
```json
{
  "_id": ObjectId("..."),
  "filename": "H.pdf",
  "page": 1,
  "table_index": 0,
  "raw_rows": 7,
  "raw_columns": 6,
  "key_value_pairs": {
    "item_number": "001",
    "drawing_number": "762849",
    "mass_kg": "195",
    ...
  },
  "header_data": {"date": "2008-01-13"},
  "import_date": "2025-12-04T10:44:33.417000"
}
```

Document 2: Sub-table (3x1)
```json
{
  "_id": ObjectId("..."),
  "filename": "H.pdf",
  "page": 1,
  "table_index": 1,
  "raw_rows": 3,
  "raw_columns": 1,
  "key_value_pairs": {},
  "header_data": {},
  "import_date": "2025-12-04T10:44:33.434000"
}
```

Document 3: Info Table (2x1)
```json
{
  "_id": ObjectId("..."),
  "filename": "H.pdf",
  "page": 1,
  "table_index": 2,
  "raw_rows": 2,
  "raw_columns": 1,
  "key_value_pairs": {},
  "header_data": {"date": "2008-01-13"},
  "import_date": "2025-12-04T10:44:33.453000"
}
```

---

## 🎯 Use Cases

### 1. Extract BOM Data
```bash
# Extract table mappings
python table_cell_mapper.py drawing.pdf --store-mongo

# Query for specific fields
python query_table_mappings.py key "item_number"
```

### 2. Quality Verification
```bash
# Check all extracted mappings
python query_table_mappings.py all

# Export for review
python query_table_mappings.py export
```

### 3. Data Integration
```bash
# Export to your system
python query_table_mappings.py export-file H.pdf

# Use table_mappings_export.json in your integration
```

### 4. Search & Analyze
```bash
# Find tables with specific value
python query_table_mappings.py value "2008-01-13"

# Find tables with specific key
python query_table_mappings.py key "material"
```

---

## 📈 Statistics

### Current H.pdf Extraction
```
Tables Extracted: 3
Total Documents in MongoDB: 3

Table Dimensions:
  Table 0: 7 rows × 6 columns
  Table 1: 3 rows × 1 column
  Table 2: 2 rows × 1 column

Key-Value Pairs:
  Table 0: Multiple mappings from header
  Table 1: Minimal/empty
  Table 2: Date mapping

Files Indexed: 1 (H.pdf)
Pages Indexed: 1
Storage Size: ~2 KB
```

---

## ✨ Key Features

✅ **Automatic Cell Mapping**
- Cells → Key-value pairs
- Pattern recognition
- Header extraction

✅ **MongoDB Storage**
- 1 document per table
- Indexed for fast queries
- Full metadata preserved

✅ **Easy Querying**
- By filename
- By page
- By key name
- By value search

✅ **Export Options**
- JSON export
- File-specific export
- Clean, readable format

✅ **Flexible Patterns**
- Date detection
- Number extraction
- Material standards
- Custom patterns

---

## 🚀 Next Steps

### 1. Extract More PDFs
```bash
python table_cell_mapper.py drawing1.pdf --store-mongo
python table_cell_mapper.py drawing2.pdf --store-mongo
```

### 2. Query All Mappings
```bash
python query_table_mappings.py all
python query_table_mappings.py stats
```

### 3. Export for Use
```bash
python query_table_mappings.py export
# Use table_mappings_export.json
```

### 4. Integrate with BOM
```bash
# Combine with extraction system
# Map table cells to BOM fields
# Store in unified MongoDB collection
```

---

## 📞 Common Tasks

### Extract table cells from new PDF
```bash
python table_cell_mapper.py newfile.pdf --store-mongo
```

### View what was extracted
```bash
python query_table_mappings.py file newfile.pdf
```

### Find specific data
```bash
python query_table_mappings.py key "drawing_number"
python query_table_mappings.py value "EN 10025"
```

### Export for integration
```bash
python query_table_mappings.py export
```

---

## ✅ Verification

- [x] Tables extracted from H.pdf
- [x] Cells mapped as key-value pairs
- [x] Stored in MongoDB TABLE_MAPPINGS
- [x] Query tool created
- [x] Export functionality working
- [x] Pattern recognition implemented
- [x] Header data extracted

**Status: ✅ COMPLETE & WORKING**

---

## 📚 Related Tools

- **`extract_cad.py`** - Text extraction (BOMAUTOMATION collection)
- **`table_cell_mapper.py`** - Table extraction (TABLE_MAPPINGS collection)
- **`query_table_mappings.py`** - Query table mappings
- **`erp_export.py`** - Export to ERP systems
- **`query_bom.py`** - Query text extraction

All data is in MongoDB `utkarshproduction` database:
- `BOMAUTOMATION` - Text extraction (1814 docs)
- `TABLE_MAPPINGS` - Table mappings (3 docs)

---

See **SETUP_INSTRUCTIONS.md** for complete system guide.
