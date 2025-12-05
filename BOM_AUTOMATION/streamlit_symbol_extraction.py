#!/usr/bin/env python3
"""
Streamlit UI for Symbol Extraction & Counting
Beautiful web interface to upload PDF, extract symbols, and view counts with images
"""

import streamlit as st
import sys
from pathlib import Path
import json
import base64
from datetime import datetime
import tempfile
import hashlib

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from core.vector_symbol_extractor import VectorSymbolExtractor
except ImportError:
    st.error("Failed to import VectorSymbolExtractor. Make sure core modules are available.")
    st.stop()

# Page config
st.set_page_config(
    page_title="Symbol Extraction & Counting",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .symbol-card {
        border: 2px solid #e0e0e0;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        background: white;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .count-badge {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 5px 15px;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'extraction_results' not in st.session_state:
    st.session_state.extraction_results = None
if 'pdf_filename' not in st.session_state:
    st.session_state.pdf_filename = None

def extract_symbols_from_pdf(pdf_path: str, min_count: int = 1, save_templates: bool = True):
    """Extract symbols from PDF"""
    try:
        extractor = VectorSymbolExtractor(pdf_path)
        results = extractor.extract_all_pages()
        
        # Save templates (use min_count=1 to save all symbols, not just repeated ones)
        template_files = []
        if save_templates:
            # Save all symbols regardless of count for display purposes
            template_files = extractor.save_symbol_templates(
                output_dir="outputs/vector_symbols",
                min_count=1  # Save all symbols so we can display them
            )
        
        extractor.close()
        
        # Group symbols by signature
        all_symbols_by_sig = {}
        for page_result in results['pages']:
            for sym in page_result['symbols']:
                sig = sym['signature']
                if sig not in all_symbols_by_sig:
                    all_symbols_by_sig[sig] = {
                        'signature': sig,
                        'instances': [],
                        'bbox': sym['bbox'],
                        'width': sym['width'],
                        'height': sym['height'],
                        'area': sym['area'],
                        'aspect_ratio': sym['aspect_ratio'],
                        'template_path': None
                    }
                all_symbols_by_sig[sig]['instances'].append({
                    'page': page_result['page'],
                    'bbox': sym['bbox']
                })
        
        # Match templates to signatures using MD5 hash
        template_map = {}
        
        # Create signature to MD5 hash mapping
        sig_to_hash = {}
        for sig in all_symbols_by_sig.keys():
            sig_to_hash[sig] = hashlib.md5(sig.encode()).hexdigest()[:8]
        
        # Match templates by MD5 hash in filename
        for template_file in template_files:
            template_path = Path(template_file)
            template_stem = template_path.stem
            
            # Extract hash from filename (format: symbol_{hash}_count{num})
            # Try to find matching signature
            for sig, sig_hash in sig_to_hash.items():
                if sig_hash in template_stem:
                    template_map[sig] = template_path
                    break
        
        # Debug: Show matching info
        st.sidebar.write(f"📊 Debug: {len(template_files)} templates saved, {len(template_map)} matched")
        
        # Build symbols list
        symbols_list = []
        for sig, sym_data in all_symbols_by_sig.items():
            count = len(sym_data['instances'])
            if count < min_count:
                continue
            
            symbol_item = {
                'signature': sig,
                'count': count,
                'width': sym_data['width'],
                'height': sym_data['height'],
                'area': sym_data['area'],
                'aspect_ratio': sym_data['aspect_ratio'],
                'instances': sym_data['instances'],
                'template_path': template_map.get(sig)
            }
            symbols_list.append(symbol_item)
        
        # Sort by count
        symbols_list.sort(key=lambda x: x['count'], reverse=True)
        
        # Format pages for display
        formatted_pages = []
        for page_result in results['pages']:
            formatted_pages.append({
                'page': page_result['page'],
                'symbol_count': page_result.get('total_symbols', 0),
                'unique_patterns': page_result.get('unique_patterns', 0)
            })
        
        return {
            'symbols': symbols_list,
            'summary': {
                'total_symbols': sum(s['count'] for s in symbols_list),
                'unique_symbols': len(symbols_list),
                'total_pages': results['summary']['total_pages']
            },
            'pages': formatted_pages
        }
    
    except Exception as e:
        st.error(f"Extraction failed: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return None

# Main UI
st.markdown('<div class="main-header">🔍 Symbol Extraction & Counting</div>', unsafe_allow_html=True)
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    
    min_count = st.slider(
        "Minimum Count",
        min_value=1,
        max_value=20,
        value=1,
        help="Only show symbols that appear at least this many times"
    )
    
    save_templates = st.checkbox(
        "Save Templates",
        value=True,
        help="Save symbol templates to outputs/vector_symbols/"
    )
    
    st.markdown("---")
    st.header("📊 Filters")
    
    filter_by_count = st.checkbox("Filter by count range")
    if filter_by_count:
        count_range = st.slider(
            "Count Range",
            min_value=1,
            max_value=100,
            value=(1, 100),
            help="Filter symbols by count range"
        )
    else:
        count_range = (1, 1000)
    
    filter_by_size = st.checkbox("Filter by size")
    if filter_by_size:
        size_range = st.slider(
            "Size Range (area)",
            min_value=0,
            max_value=50000,
            value=(0, 50000),
            help="Filter symbols by area"
        )
    else:
        size_range = (0, 1000000)

# File upload
st.header("📄 Upload PDF")
col1, col2 = st.columns([3, 1])

with col1:
    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=['pdf'],
        help="Upload a PDF file to extract symbols from"
    )

with col2:
    use_local = st.button("Use H.pdf", help="Use H.pdf from root directory")

# Process PDF
if uploaded_file is not None or use_local:
    pdf_path = None
    
    try:
        if uploaded_file is not None:
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(uploaded_file.read())
                pdf_path = tmp_file.name
                pdf_name = uploaded_file.name
        else:
            # Use local file
            pdf_path = "H.pdf"
            pdf_name = "H.pdf"
            if not Path(pdf_path).exists():
                st.error(f"File not found: {pdf_path}")
                st.stop()
        
        # Extract symbols
        with st.spinner(f"Extracting symbols from {pdf_name}... This may take a moment."):
            results = extract_symbols_from_pdf(
                pdf_path,
                min_count=min_count,
                save_templates=save_templates
            )
        
        if results:
            st.session_state.extraction_results = results
            st.session_state.pdf_filename = pdf_name
            
            # Clean up temp file
            if uploaded_file is not None and Path(pdf_path).exists():
                Path(pdf_path).unlink()
    
    except Exception as e:
        st.error(f"Error processing PDF: {str(e)}")
        import traceback
        st.code(traceback.format_exc())

# Display results
if st.session_state.extraction_results:
    results = st.session_state.extraction_results
    
    # Apply filters
    filtered_symbols = results['symbols']
    if filter_by_count:
        filtered_symbols = [s for s in filtered_symbols if count_range[0] <= s['count'] <= count_range[1]]
    if filter_by_size:
        filtered_symbols = [s for s in filtered_symbols if size_range[0] <= s['area'] <= size_range[1]]
    
    # Summary metrics
    st.markdown("---")
    st.header("📊 Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Symbols", results['summary']['total_symbols'])
    with col2:
        st.metric("Unique Symbols", results['summary']['unique_symbols'])
    with col3:
        st.metric("Total Pages", results['summary']['total_pages'])
    with col4:
        st.metric("Filtered Results", len(filtered_symbols))
    
    # Charts
    if filtered_symbols:
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            # Count distribution
            if HAS_PANDAS:
                counts = [s['count'] for s in filtered_symbols]
                df_counts = pd.DataFrame({'Count': counts})
                st.bar_chart(df_counts, height=300)
                st.caption("Symbol Count Distribution")
            else:
                st.info("Install pandas for charts: pip install pandas")
        
        with chart_col2:
            # Size distribution
            if HAS_PANDAS:
                areas = [s['area'] for s in filtered_symbols]
                df_areas = pd.DataFrame({'Area': areas})
                st.line_chart(df_areas, height=300)
                st.caption("Symbol Size (Area) Distribution")
            else:
                st.info("Install pandas for charts: pip install pandas")
    
    # Per-page breakdown
    with st.expander("📄 Per-Page Breakdown"):
        for page in results['pages']:
            symbol_count = page.get('symbol_count', page.get('total_symbols', 0))
            unique_patterns = page.get('unique_patterns', 0)
            st.write(f"**Page {page['page']}**: {symbol_count} symbols, {unique_patterns} unique patterns")
    
    # Symbols grid
    st.markdown("---")
    st.header(f"🎯 Symbols ({len(filtered_symbols)} shown)")
    
    # Search/filter
    search_term = st.text_input("🔍 Search by signature", placeholder="Enter signature to filter...")
    if search_term:
        filtered_symbols = [s for s in filtered_symbols if search_term.lower() in s['signature'].lower()]
    
    # Display symbols in grid
    if filtered_symbols:
        # Sort options
        sort_option = st.selectbox(
            "Sort by",
            ["Count (High to Low)", "Count (Low to High)", "Size (Large to Small)", "Size (Small to Large)", "Signature"]
        )
        
        if sort_option == "Count (High to Low)":
            filtered_symbols = sorted(filtered_symbols, key=lambda x: x['count'], reverse=True)
        elif sort_option == "Count (Low to High)":
            filtered_symbols = sorted(filtered_symbols, key=lambda x: x['count'])
        elif sort_option == "Size (Large to Small)":
            filtered_symbols = sorted(filtered_symbols, key=lambda x: x['area'], reverse=True)
        elif sort_option == "Size (Small to Large)":
            filtered_symbols = sorted(filtered_symbols, key=lambda x: x['area'])
        elif sort_option == "Signature":
            filtered_symbols = sorted(filtered_symbols, key=lambda x: x['signature'])
        
        # Grid layout selector
        cols_per_row = st.selectbox("Columns per row", [2, 3, 4], index=1)
        
        # Calculate grid columns
        num_rows = (len(filtered_symbols) + cols_per_row - 1) // cols_per_row
        
        for row in range(num_rows):
            cols = st.columns(cols_per_row)
            for col_idx in range(cols_per_row):
                symbol_idx = row * cols_per_row + col_idx
                if symbol_idx < len(filtered_symbols):
                    symbol = filtered_symbols[symbol_idx]
                    
                    with cols[col_idx]:
                        # Symbol card with count badge
                        st.markdown(f"""
                            <div style="border: 2px solid #e0e0e0; border-radius: 10px; padding: 15px; margin-bottom: 20px; background: white; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 8px 15px; border-radius: 20px; font-weight: bold; text-align: center; margin-bottom: 10px;">
                                    Count: {symbol['count']}
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        # Display image if available
                        if symbol.get('template_path'):
                            template_path = Path(symbol['template_path'])
                            if template_path.exists():
                                try:
                                    st.image(
                                        str(template_path), 
                                        use_container_width=True,
                                        caption=f"Symbol {symbol_idx + 1} | Count: {symbol['count']}"
                                    )
                                except Exception as e:
                                    st.error(f"Error loading image: {e}")
                                    st.write(f"Path: {template_path}")
                            else:
                                st.warning(f"⚠️ Image not found: {template_path}")
                        else:
                            st.info("ℹ️ No template image available for this symbol")
                        
                        # Symbol details in expander
                        with st.expander("📋 Details", expanded=False):
                            st.write(f"**Count:** {symbol['count']} occurrences")
                            st.write(f"**Size:** {symbol['width']:.1f} × {symbol['height']:.1f} px")
                            st.write(f"**Area:** {symbol['area']:.0f} px²")
                            st.write(f"**Aspect Ratio:** {symbol['aspect_ratio']:.2f}")
                            
                            # Show pages where symbol appears
                            pages = sorted(set(inst['page'] for inst in symbol['instances']))
                            st.write(f"**Pages:** {', '.join(map(str, pages))}")
                            
                            # Signature (truncated)
                            st.write(f"**Signature:**")
                            st.code(symbol['signature'][:80] + "..." if len(symbol['signature']) > 80 else symbol['signature'])
                            
                            # Template file path
                            if symbol['template_path']:
                                st.write(f"**Template:** `{Path(symbol['template_path']).name}`")
    else:
        st.warning("No symbols found matching the current filters.")
    
    # Download results
    st.markdown("---")
    st.header("💾 Download Results")
    
    # Prepare JSON for download
    download_data = {
        'pdf_filename': st.session_state.pdf_filename,
        'timestamp': datetime.now().isoformat(),
        'summary': results['summary'],
        'symbols': [
            {
                'signature': s['signature'],
                'count': s['count'],
                'width': s['width'],
                'height': s['height'],
                'area': s['area'],
                'template_filename': Path(s['template_path']).name if s['template_path'] else None
            }
            for s in filtered_symbols
        ]
    }
    
    json_str = json.dumps(download_data, indent=2)
    st.download_button(
        label="📥 Download Results (JSON)",
        data=json_str,
        file_name=f"symbol_extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json"
    )

else:
    # Welcome message
    st.info("👆 Upload a PDF file above to extract symbols, or click 'Use H.pdf' to use the default file.")
    
    # Show example
    with st.expander("📖 How to use"):
        st.markdown("""
        1. **Upload PDF**: Click "Browse files" to upload a PDF, or use the "Use H.pdf" button
        2. **Adjust Settings**: Use the sidebar to set minimum count and filters
        3. **View Results**: Symbols will be displayed with images and counts
        4. **Filter & Search**: Use the search box to find specific symbols
        5. **Download**: Export results as JSON
        
        **Features:**
        - Automatic symbol extraction from vector primitives
        - Visual representation of each symbol
        - Per-page breakdown
        - Filtering and search capabilities
        - Export results
        """)

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666;'>Symbol Extraction & Counting System | Built with Streamlit</div>",
    unsafe_allow_html=True
)

