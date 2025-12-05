"""
Run template matching for all PNG templates placed in `inputs/templates/` against a PDF.
Saves JSON results (counts per template per page) and debug overlays in `outputs/template_counts/`.

Requires OpenCV (`cv2`) for reliable template matching. If `cv2` is not available, the script will exit with an instruction.

Usage:
  python prototypes/run_template_count.py --pdf ../H.pdf --dpi 300 --thresh 0.75

"""
import os
import json
import math
import argparse
from pathlib import Path
from datetime import datetime
from PIL import Image

try:
    import cv2
    import numpy as np
except Exception:
    cv2 = None
    import numpy as np

    # Provide a warning that OpenCV is not available; we'll use a pure-numpy fallback for template matching
    print('Warning: OpenCV not available, using pure-numpy fallback matcher (slower)')

import fitz

OUT_DIR = Path('outputs/template_counts')
OUT_DIR.mkdir(parents=True, exist_ok=True)


def rasterize_page(pdf_path, page_num=0, dpi=300):
    doc = fitz.open(pdf_path)
    page = doc.load_page(page_num)
    mat = fitz.Matrix(dpi / 72.0, dpi / 72.0)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)
    doc.close()
    return img


def match_template_cv2(page_img_np, template_np, thresh=0.75, scales=(1.0,)):
    # If cv2 is available, use it
    if cv2 is not None:
        detections = []
        img_gray = cv2.cvtColor(page_img_np, cv2.COLOR_BGR2GRAY) if page_img_np.ndim == 3 else page_img_np
        tpl_h0, tpl_w0 = template_np.shape[:2]
        for s in scales:
            tpl_w = max(1, int(tpl_w0 * s))
            tpl_h = max(1, int(tpl_h0 * s))
            tpl_resized = cv2.resize(template_np, (tpl_w, tpl_h), interpolation=cv2.INTER_AREA)
            tpl_gray = cv2.cvtColor(tpl_resized, cv2.COLOR_BGR2GRAY) if tpl_resized.ndim == 3 else tpl_resized
            try:
                res = cv2.matchTemplate(img_gray, tpl_gray, cv2.TM_CCOEFF_NORMED)
            except Exception:
                continue
            loc = np.where(res >= thresh)
            for y, x in zip(*loc):
                score = float(res[y, x])
                detections.append({'bbox': [int(x), int(y), int(x + tpl_w), int(y + tpl_h)], 'score': score})
        return detections

    # Fallback pure-numpy normalized cross-correlation (slower)
    detections = []
    img = page_img_np
    if img.ndim == 3:
        # convert RGB to grayscale
        img = np.dot(img[...,:3], [0.2989, 0.5870, 0.1140])
    tpl = template_np
    if tpl.ndim == 3:
        tpl = np.dot(tpl[...,:3], [0.2989, 0.5870, 0.1140])
    ih, iw = img.shape
    th0, tw0 = tpl.shape
    for s in scales:
        th = max(1, int(th0 * s))
        tw = max(1, int(tw0 * s))
        # resize template using numpy (simple nearest-neighbor)
        tpl_rs = np.array(Image.fromarray(tpl).resize((tw, th))).astype(np.float32)
        tpl_mean = tpl_rs.mean()
        tpl_std = tpl_rs.std() + 1e-8
        # sliding window (naive) - compute NCC with step to speed up
        step_y = max(1, th // 4)
        step_x = max(1, tw // 4)
        for y in range(0, ih - th + 1, step_y):
            for x in range(0, iw - tw + 1, step_x):
                window = img[y:y+th, x:x+tw].astype(np.float32)
                w_mean = window.mean()
                w_std = window.std() + 1e-8
                ncc = ((window - w_mean) * (tpl_rs - tpl_mean)).sum() / (w_std * tpl_std * (tw*th))
                if ncc >= thresh:
                    detections.append({'bbox': [int(x), int(y), int(x+tw), int(y+th)], 'score': float(ncc)})
    return detections


def non_max_suppression(dets, iou_thresh=0.25):
    if not dets:
        return []
    boxes = np.array([d['bbox'] for d in dets])
    scores = np.array([d['score'] for d in dets])
    x1 = boxes[:,0]; y1 = boxes[:,1]; x2 = boxes[:,2]; y2 = boxes[:,3]
    areas = (x2 - x1 + 1) * (y2 - y1 + 1)
    order = scores.argsort()[::-1]
    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(i)
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        w = np.maximum(0.0, xx2 - xx1 + 1)
        h = np.maximum(0.0, yy2 - yy1 + 1)
        inter = w * h
        iou = inter / (areas[i] + areas[order[1:]] - inter)
        inds = np.where(iou <= iou_thresh)[0]
        order = order[inds + 1]
    return [dets[i] for i in keep]


def draw_overlay(pil_img, detections_by_template, out_path):
    img = pil_img.convert('RGB')
    draw = Image.new('RGBA', img.size)
    from PIL import ImageDraw
    d = ImageDraw.Draw(img)
    import random
    rng = random.Random(1234)
    for tname, dets in detections_by_template.items():
        color = tuple(rng.randint(50,230) for _ in range(3))
        for det in dets:
            x0,y0,x1,y1 = det['bbox']
            d.rectangle([x0,y0,x1,y1], outline=color, width=2)
            d.text((x0+2,y0+2), f"{tname}:{det['score']:.2f}", fill=color)
    img.save(out_path)


def run(pdf_path, dpi=300, thresh=0.75, scales=(0.9,1.0,1.1)):
    templates_dir = Path('inputs/templates')
    if not templates_dir.exists():
        print('No templates found in inputs/templates. Please place PNG templates and retry.')
        return 1
    template_files = list(templates_dir.glob('*.png')) + list(templates_dir.glob('*.jpg'))
    if not template_files:
        print('No PNG/JPG templates found in inputs/templates.')
        return 1

    # load templates (support PIL/numpy when cv2 is unavailable)
    templates = {}
    for tf in template_files:
        try:
            if cv2 is not None:
                tpl = cv2.imread(str(tf))
                if tpl is None:
                    print('Warning: failed to read template via cv2, trying PIL', tf)
                    tpl = np.array(Image.open(tf).convert('RGB'))
            else:
                tpl = np.array(Image.open(tf).convert('RGB'))
        except Exception as e:
            print('Warning: failed to read template', tf, e)
            continue
        templates[tf.stem] = tpl

    # open PDF to get page count
    doc = fitz.open(pdf_path)
    page_count = doc.page_count
    doc.close()

    results = {
        'file': os.path.basename(pdf_path),
        'timestamp': datetime.utcnow().isoformat(),
        'pages': []
    }

    for p in range(page_count):
        print(f'Processing page {p+1}/{page_count}')
        pil_img = rasterize_page(pdf_path, p, dpi=dpi)
        if cv2 is not None:
            page_np = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        else:
            page_np = np.array(pil_img)
        page_entry = {'page': p, 'width': pil_img.width, 'height': pil_img.height, 'templates': {}}
        detections_by_template = {}
        for tname, tpl in templates.items():
            dets = match_template_cv2(page_np, tpl, thresh=thresh, scales=scales)
            # apply NMS
            dets_nms = non_max_suppression(dets, iou_thresh=0.25)
            detections_by_template[tname] = dets_nms
            page_entry['templates'][tname] = {'count': len(dets_nms), 'detections': dets_nms}
        # draw overlay
        out_overlay = OUT_DIR / f'page_{p}_overlay.png'
        draw_overlay(pil_img, detections_by_template, out_overlay)
        results['pages'].append(page_entry)

    out_json = OUT_DIR / 'template_counts.json'
    with open(out_json, 'w') as f:
        json.dump(results, f, indent=2)
    print('Done. Results saved to', out_json)
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--pdf', required=True)
    parser.add_argument('--dpi', type=int, default=300)
    parser.add_argument('--thresh', type=float, default=0.75)
    parser.add_argument('--scales', type=str, default='0.9,1.0,1.1')
    args = parser.parse_args()
    scales = tuple(float(x) for x in args.scales.split(','))
    exit(run(args.pdf, dpi=args.dpi, thresh=args.thresh, scales=scales))
