"""
OCR engine stub. Wraps Tesseract OCR calls with a simple API and returns text blocks with bounding boxes.
Function: `ocr_image_pil(pil_image)` -> List[ {"text": str, "bbox": [x0,y0,x1,y1], "conf": float} ]

This stub falls back to returning an empty list if pytesseract is not installed.
"""

from typing import List, Dict

try:
    from PIL import Image
    import pytesseract
except Exception:
    Image = None
    pytesseract = None


def ocr_image_pil(pil_image) -> List[Dict]:
    """Perform OCR on a PIL image and return text blocks.

    pil_image: PIL.Image
    returns: list of dicts {text, bbox, conf}
    """
    results = []
    if pytesseract is None or Image is None:
        return results

    # Use pytesseract to get data with bounding boxes
    try:
        data = pytesseract.image_to_data(pil_image, output_type=pytesseract.Output.DICT)
        n = len(data.get('text', []))
        for i in range(n):
            txt = (data['text'][i] or '').strip()
            if not txt:
                continue
            bbox = [data['left'][i], data['top'][i], data['left'][i] + data['width'][i], data['top'][i] + data['height'][i]]
            conf = float(data['conf'][i]) if data['conf'][i] not in (None, '') else 0.0
            results.append({"text": txt, "bbox": bbox, "conf": conf})
    except Exception:
        return []

    return results
