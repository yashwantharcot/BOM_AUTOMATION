"""
Vector text extractor stub.
Tries to extract vector text from a PDF page using PyMuPDF (fitz) or pdfminer as fallback.
Provides a unified function `extract_vector_text(pdf_path, pages=None)` returning a list of pages,
each page is a list of dicts: {"text": str, "bbox": [x0,y0,x1,y1], "font_size": float}
"""

from typing import List, Dict, Optional

try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None


def extract_vector_text(pdf_path: str, pages: Optional[List[int]] = None) -> List[List[Dict]]:
    """Extracts vector text from PDF if available.

    Args:
        pdf_path: path to PDF file
        pages: optional list of 0-based page indices to extract

    Returns:
        List per page of text items with bbox and font_size.
    """
    results = []
    if fitz is None:
        # PyMuPDF not installed; return empty structured output
        return results

    doc = fitz.open(pdf_path)
    total_pages = doc.page_count
    page_indices = pages if pages is not None else list(range(total_pages))

    for p in page_indices:
        if p < 0 or p >= total_pages:
            results.append([])
            continue
        page = doc.load_page(p)
        blocks = page.get_text("dict").get("blocks", [])
        items = []
        for b in blocks:
            for line in b.get("lines", []):
                for span in line.get("spans", []):
                    item = {
                        "text": span.get("text", "").strip(),
                        "bbox": [span.get("bbox")[0], span.get("bbox")[1], span.get("bbox")[2], span.get("bbox")[3]] if span.get("bbox") else None,
                        "font_size": span.get("size")
                    }
                    if item["text"]:
                        items.append(item)
        results.append(items)
    doc.close()
    return results
