from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import List, Dict, Any
import uvicorn
import numpy as np
import cv2
import fitz  # PyMuPDF
from PIL import Image
import io
import tempfile

app = FastAPI(title="Symbol Count API")

# ---------- Utility functions ----------

def pil_to_cv2(pil_img: Image.Image) -> np.ndarray:
    """Convert PIL Image to OpenCV BGR (or grayscale if single channel)."""
    rgb = pil_img.convert("RGB")
    arr = np.asarray(rgb)
    # from RGB to BGR for OpenCV
    return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)

def load_imagefile_to_cv2(file: UploadFile) -> np.ndarray:
    """Read an uploaded file (image) and return OpenCV BGR ndarray."""
    data = file.file.read()
    file.file.seek(0)
    pil = Image.open(io.BytesIO(data))
    return pil_to_cv2(pil)

def render_pdf_pages_to_pil(pdf_bytes: bytes, zoom: float = 2.0) -> List[Image.Image]:
    """
    Render PDF pages to PIL images using PyMuPDF.
    zoom controls resolution: 2.0 = 2x (higher -> better matching but slower)
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = []
    mat = fitz.Matrix(zoom, zoom)
    for i in range(doc.page_count):
        page = doc.load_page(i)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        mode = "RGB"
        img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
        pages.append(img)
    return pages

def non_max_suppression(rects, scores, iou_threshold=0.3):
    """
    rects: list of [x1,y1,x2,y2]
    scores: corresponding list of scores
    returns list of indices kept
    """
    if len(rects) == 0:
        return []
    rects = np.array(rects, dtype=float)
    scores = np.array(scores, dtype=float)

    x1 = rects[:,0]
    y1 = rects[:,1]
    x2 = rects[:,2]
    y2 = rects[:,3]
    areas = (x2 - x1 + 1) * (y2 - y1 + 1)
    order = scores.argsort()[::-1]

    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(int(i))
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])

        w = np.maximum(0.0, xx2 - xx1 + 1)
        h = np.maximum(0.0, yy2 - yy1 + 1)
        inter = w * h
        iou = inter / (areas[i] + areas[order[1:]] - inter)
        inds = np.where(iou <= iou_threshold)[0]
        order = order[inds + 1]
    return keep

def match_template_multiscale(page_cv2, template_cv2, scales=(0.7, 1.0, 1.3), threshold=0.7, nms_iou=0.3):
    """
    Run multi-scale template matching and return bounding boxes and scores after NMS.
    page_cv2: page image in BGR or grayscale (ndarray)
    template_cv2: template image in BGR or grayscale (ndarray)
    scales: iterable of scaling factors to apply to template
    threshold: match threshold (for TM_CCOEFF_NORMED)
    """
    page_gray = page_cv2 if len(page_cv2.shape) == 2 else cv2.cvtColor(page_cv2, cv2.COLOR_BGR2GRAY)
    tpl_gray_orig = template_cv2 if len(template_cv2.shape) == 2 else cv2.cvtColor(template_cv2, cv2.COLOR_BGR2GRAY)

    rects = []
    scores = []

    ph, pw = page_gray.shape[:2]

    for s in scales:
        # resize template
        new_w = max(1, int(tpl_gray_orig.shape[1] * s))
        new_h = max(1, int(tpl_gray_orig.shape[0] * s))
        tpl = cv2.resize(tpl_gray_orig, (new_w, new_h), interpolation=cv2.INTER_AREA)

        if tpl.shape[0] >= page_gray.shape[0] or tpl.shape[1] >= page_gray.shape[1]:
            continue

        res = cv2.matchTemplate(page_gray, tpl, cv2.TM_CCOEFF_NORMED)
        loc = np.where(res >= threshold)
        for pt_y, pt_x in zip(*loc):
            score = float(res[pt_y, pt_x])
            x1, y1 = int(pt_x), int(pt_y)
            x2, y2 = int(pt_x + tpl.shape[1]), int(pt_y + tpl.shape[0])
            rects.append([x1, y1, x2, y2])
            scores.append(score)

    # apply NMS to merge overlapping detections
    keep_idx = non_max_suppression(rects, scores, iou_threshold=nms_iou)
    kept_rects = [rects[i] for i in keep_idx]
    kept_scores = [scores[i] for i in keep_idx]

    return kept_rects, kept_scores

# ---------- FastAPI endpoints ----------

@app.post("/api/detect_symbols")
async def detect_symbols(
    pdf_file: UploadFile = File(...),
    templates: List[UploadFile] = File(...),
    threshold: float = Form(0.75),
    scales: str = Form("0.8,1.0,1.2"),
    nms_iou: float = Form(0.3),
    zoom: float = Form(2.0)
):
    """
    Upload a PDF and one or more template images. Returns counts per template per page.
    - pdf_file: the PDF
    - templates: list of image files (png/jpg) that are templates to match
    - threshold: matching threshold (0.0 - 1.0)
    - scales: comma-separated scales to try for template matching (e.g. "0.7,1.0,1.3")
    - nms_iou: NMS IoU threshold
    - zoom: rendering scale for PDF (higher = higher resolution)
    """
    # basic validation
    if pdf_file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="pdf_file must be a PDF")

    try:
        scale_floats = [float(x.strip()) for x in scales.split(",") if x.strip()]
        assert len(scale_floats) > 0
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid scales parameter")

    # load templates into cv2 arrays and keep original names
    template_images = []
    for t in templates:
        try:
            t_cv2 = load_imagefile_to_cv2(t)
            template_images.append({"name": t.filename, "cv2": t_cv2})
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to read template {t.filename}: {e}")

    pdf_bytes = await pdf_file.read()
    # render pages to PIL images
    try:
        pages_pil = render_pdf_pages_to_pil(pdf_bytes, zoom=zoom)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to render PDF pages: {e}")

    # convert pages to cv2
    pages_cv2 = [pil_to_cv2(p) for p in pages_pil]

    results: Dict[str, Any] = {
        "file_name": pdf_file.filename,
        "num_pages": len(pages_cv2),
        "pages": []
    }

    # iterate pages and templates
    totals_by_template = {t["name"]: 0 for t in template_images}
    for page_index, page_cv2 in enumerate(pages_cv2):
        ph, pw = page_cv2.shape[:2]
        page_entry = {
            "page_index": page_index,
            "image_width": int(pw),
            "image_height": int(ph),
            "template_results": []
        }

        for tpl in template_images:
            rects, scores = match_template_multiscale(
                page_cv2,
                tpl["cv2"],
                scales=scale_floats,
                threshold=float(threshold),
                nms_iou=float(nms_iou)
            )
            count = len(rects)
            totals_by_template[tpl["name"]] += count
            page_entry["template_results"].append({
                "template_name": tpl["name"],
                "count": count,
                "detections": [
                    {"bbox": r, "score": s} for r, s in zip(rects, scores)
                ]
            })
        results["pages"].append(page_entry)

    results["totals"] = totals_by_template
    return JSONResponse(content=results)


# small health-check
@app.get("/api/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("fastapi_symbol_count_api:app", host="127.0.0.1", port=8000, reload=True)
