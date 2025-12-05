#!/usr/bin/env python3
"""
Database Schema Module (PostgreSQL)
Defines database schema as per Section 11 specification
"""

from typing import Optional, Dict, List
from datetime import datetime

# SQLAlchemy models would go here, but for now we'll define schema as SQL strings
# This can be converted to SQLAlchemy ORM models later

SCHEMA_SQL = """
-- Symbols Table (Section 5.1)
CREATE TABLE IF NOT EXISTS symbols (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    template_image_path TEXT,
    rotations_allowed BOOLEAN DEFAULT FALSE,
    scaling_allowed BOOLEAN DEFAULT FALSE,
    threshold REAL DEFAULT 0.75,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_symbols_name ON symbols(name);

-- Uploads Table (Section 11)
CREATE TABLE IF NOT EXISTS uploads (
    id SERIAL PRIMARY KEY,
    filename TEXT NOT NULL,
    file_path TEXT,
    file_size BIGINT,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'pending',  -- pending, processing, completed, failed
    pages_count INTEGER,
    processing_time REAL,
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_uploads_status ON uploads(status);
CREATE INDEX IF NOT EXISTS idx_uploads_uploaded_at ON uploads(uploaded_at);

-- Symbol Detections Table (Section 11)
CREATE TABLE IF NOT EXISTS symbol_detections (
    id SERIAL PRIMARY KEY,
    upload_id INTEGER REFERENCES uploads(id) ON DELETE CASCADE,
    page INTEGER NOT NULL,
    symbol_id INTEGER REFERENCES symbols(id) ON DELETE CASCADE,
    bbox JSONB NOT NULL,  -- [x1, y1, x2, y2]
    score REAL NOT NULL,
    detection_method TEXT,  -- template, feature, ml
    rotation REAL,
    scale REAL,
    confidence REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_symbol_detections_upload_id ON symbol_detections(upload_id);
CREATE INDEX IF NOT EXISTS idx_symbol_detections_symbol_id ON symbol_detections(symbol_id);
CREATE INDEX IF NOT EXISTS idx_symbol_detections_page ON symbol_detections(page);

-- Extracted Text Table (Section 11)
CREATE TABLE IF NOT EXISTS text_entries (
    id SERIAL PRIMARY KEY,
    upload_id INTEGER REFERENCES uploads(id) ON DELETE CASCADE,
    page INTEGER NOT NULL,
    text TEXT NOT NULL,
    bbox JSONB NOT NULL,  -- [x0, y0, x1, y1]
    confidence REAL,
    source TEXT,  -- vector, ocr
    font TEXT,
    font_size REAL,
    color INTEGER,
    layer_info JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_text_entries_upload_id ON text_entries(upload_id);
CREATE INDEX IF NOT EXISTS idx_text_entries_page ON text_entries(page);
CREATE INDEX IF NOT EXISTS idx_text_entries_source ON text_entries(source);

-- Extracted Tables Table (Section 11)
CREATE TABLE IF NOT EXISTS table_cells (
    id SERIAL PRIMARY KEY,
    upload_id INTEGER REFERENCES uploads(id) ON DELETE CASCADE,
    page INTEGER NOT NULL,
    table_index INTEGER,
    row INTEGER NOT NULL,
    col INTEGER NOT NULL,
    text TEXT,
    bbox JSONB NOT NULL,
    confidence REAL,
    header BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_table_cells_upload_id ON table_cells(upload_id);
CREATE INDEX IF NOT EXISTS idx_table_cells_page ON table_cells(page);
CREATE INDEX IF NOT EXISTS idx_table_cells_table_index ON table_cells(table_index);

-- Parsed Values Table (for extracted quantities, dimensions, materials)
CREATE TABLE IF NOT EXISTS parsed_values (
    id SERIAL PRIMARY KEY,
    upload_id INTEGER REFERENCES uploads(id) ON DELETE CASCADE,
    page INTEGER,
    text_entry_id INTEGER REFERENCES text_entries(id) ON DELETE SET NULL,
    value_type TEXT NOT NULL,  -- quantity, dimension, material, standard, date
    value_text TEXT,
    value_numeric REAL,
    unit TEXT,
    normalized_value TEXT,
    confidence REAL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_parsed_values_upload_id ON parsed_values(upload_id);
CREATE INDEX IF NOT EXISTS idx_parsed_values_type ON parsed_values(value_type);

-- Symbol-Text Associations (from Rule Engine)
CREATE TABLE IF NOT EXISTS symbol_text_associations (
    id SERIAL PRIMARY KEY,
    upload_id INTEGER REFERENCES uploads(id) ON DELETE CASCADE,
    page INTEGER NOT NULL,
    symbol_detection_id INTEGER REFERENCES symbol_detections(id) ON DELETE CASCADE,
    text_entry_id INTEGER REFERENCES text_entries(id) ON DELETE CASCADE,
    distance REAL,
    association_score REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_symbol_text_associations_upload_id ON symbol_text_associations(upload_id);
CREATE INDEX IF NOT EXISTS idx_symbol_text_associations_symbol ON symbol_text_associations(symbol_detection_id);
CREATE INDEX IF NOT EXISTS idx_symbol_text_associations_text ON symbol_text_associations(text_entry_id);
"""


class DatabaseSchema:
    """Database schema manager"""
    
    def __init__(self, connection=None):
        """
        Initialize schema manager
        
        Args:
            connection: Database connection (psycopg2 or SQLAlchemy)
        """
        self.connection = connection
    
    def create_schema(self):
        """Create all tables"""
        if self.connection:
            cursor = self.connection.cursor()
            cursor.execute(SCHEMA_SQL)
            self.connection.commit()
            cursor.close()
            return True
        return False
    
    def get_symbol_count_query(self, upload_id: int, symbol_id: Optional[int] = None) -> str:
        """
        Get SQL query for symbol counts
        
        Args:
            upload_id: Upload ID
            symbol_id: Optional symbol ID filter
            
        Returns:
            SQL query string
        """
        if symbol_id:
            return f"""
                SELECT symbol_id, COUNT(*) as count
                FROM symbol_detections
                WHERE upload_id = {upload_id} AND symbol_id = {symbol_id}
                GROUP BY symbol_id
            """
        else:
            return f"""
                SELECT symbol_id, COUNT(*) as count
                FROM symbol_detections
                WHERE upload_id = {upload_id}
                GROUP BY symbol_id
            """
    
    def get_text_entries_query(self, upload_id: int, page: Optional[int] = None) -> str:
        """Get SQL query for text entries"""
        base_query = f"SELECT * FROM text_entries WHERE upload_id = {upload_id}"
        if page is not None:
            base_query += f" AND page = {page}"
        return base_query + " ORDER BY page, id"
    
    def get_table_cells_query(self, upload_id: int, page: Optional[int] = None) -> str:
        """Get SQL query for table cells"""
        base_query = f"SELECT * FROM table_cells WHERE upload_id = {upload_id}"
        if page is not None:
            base_query += f" AND page = {page}"
        return base_query + " ORDER BY page, table_index, row, col"


# MongoDB schema (for compatibility with existing code)
MONGO_SCHEMA = {
    'symbols': {
        'symbol_name': str,
        'image_data': bytes,
        'image_filename': str,
        'metadata': dict,
        'created_at': datetime,
        'updated_at': datetime
    },
    'symbol_detections': {
        'filename': str,
        'page': int,
        'symbols': list,  # List of {symbol_name, count, detections}
        'timestamp': datetime,
        'dpi': int
    },
    'text_entries': {
        'upload_id': str,
        'page': int,
        'text': str,
        'bbox': list,
        'source': str,
        'confidence': float
    },
    'table_cells': {
        'upload_id': str,
        'page': int,
        'table_index': int,
        'row': int,
        'col': int,
        'text': str,
        'bbox': list
    }
}


if __name__ == "__main__":
    print("Database Schema Module")
    print("=" * 50)
    print("\nPostgreSQL Schema:")
    print(SCHEMA_SQL[:500] + "...")
    print("\nMongoDB Schema:")
    for collection, schema in MONGO_SCHEMA.items():
        print(f"\n{collection}:")
        for field, field_type in schema.items():
            print(f"  {field}: {field_type.__name__ if hasattr(field_type, '__name__') else str(field_type)}")





