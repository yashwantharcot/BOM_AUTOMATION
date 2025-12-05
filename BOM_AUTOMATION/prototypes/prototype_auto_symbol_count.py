"""
Prototype: Auto-extract repeated shapes from PDF page and count candidate symbols.
- Rasterizes first page of `H.pdf` at 300 DPI
- Preprocess: grayscale, adaptive threshold
- Contour extraction via OpenCV
- Shape descriptor: log-abs Hu moments
- Simple clustering by threshold on descriptor distance
- Outputs JSON-like summary to stdout and saves debug image with colored bboxes

Usage:
    python prototypes/prototype_auto_symbol_count.py --pdf ../H.pdf --page 0

"""
import os
import argparse
import math
import json
from pathlib import Path

import fitz
import numpy as np
from PIL import Image

# Try to import OpenCV; if not available, we'll fallback to a pure-python extractor
try:
    import cv2
    HAVE_CV2 = True
except Exception:
    cv2 = None
    HAVE_CV2 = False


def rasterize_pdf_page(pdf_path, page_number=0, dpi=300):
    doc = fitz.open(pdf_path)
    if page_number < 0 or page_number >= doc.page_count:
        raise IndexError("Page index out of range")
    page = doc.load_page(page_number)
    mat = fitz.Matrix(dpi / 72.0, dpi / 72.0)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    mode = "RGB"
    img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
    doc.close()
    return img


def preprocess_image(pil_img):
    img = np.array(pil_img.convert('L'))
    if HAVE_CV2:
        # adaptive threshold
        th = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY_INV, 25, 10)
        # morphological opening to remove small noise
        kernel = np.ones((3,3), np.uint8)
        opened = cv2.morphologyEx(th, cv2.MORPH_OPEN, kernel)
        return opened
    else:
        # simple global threshold fallback
        th = (img < 200).astype(np.uint8) * 255
        return th


def extract_contours(bin_img, min_area=80):
    results = []
    h_img, w_img = bin_img.shape[:2]
    if HAVE_CV2:
        contours, _ = cv2.findContours(bin_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < min_area:
                continue
            x, y, w, h = cv2.boundingRect(cnt)
            bbox = [int(x), int(y), int(x+w), int(y+h)]
            # extract contour mask for Hu moments
            mask = np.zeros_like(bin_img)
            cv2.drawContours(mask, [cnt], -1, 255, -1)
            moments = cv2.moments(mask)
            hu = cv2.HuMoments(moments).flatten()
            # log scale transform for stability
            with np.errstate(all='ignore'):
                hu_log = -np.sign(hu) * np.log10(np.abs(hu) + 1e-30)
                hu_log = np.nan_to_num(hu_log)
            results.append({'bbox': bbox, 'area': float(area), 'hu': hu_log.tolist()})
        return results

    # Fallback: simple connected-component labeling (4-connectivity)
    data = (bin_img > 0).astype(np.uint8)
    visited = np.zeros_like(data, dtype=bool)
    def neighbors(y, x):
        for ny, nx in ((y-1,x),(y+1,x),(y,x-1),(y,x+1)):
            if 0 <= ny < h_img and 0 <= nx < w_img:
                yield ny, nx

    for y in range(h_img):
        for x in range(w_img):
            if data[y, x] and not visited[y, x]:
                # flood fill
                stack = [(y, x)]
                visited[y, x] = True
                minx = x; maxx = x; miny = y; maxy = y
                cnt_pixels = 0
                coords = []
                while stack:
                    cy, cx = stack.pop()
                    cnt_pixels += 1
                    coords.append((cy, cx))
                    if cx < minx: minx = cx
                    if cx > maxx: maxx = cx
                    if cy < miny: miny = cy
                    if cy > maxy: maxy = cy
                    for ny, nx in neighbors(cy, cx):
                        if data[ny, nx] and not visited[ny, nx]:
                            visited[ny, nx] = True
                            stack.append((ny, nx))
                area = cnt_pixels
                if area < min_area:
                    continue
                bbox = [int(minx), int(miny), int(maxx), int(maxy)]
                # create small mask for descriptor
                mask_h = max(1, bbox[3]-bbox[1]+1)
                mask_w = max(1, bbox[2]-bbox[0]+1)
                mask = np.zeros((mask_h, mask_w), dtype=np.uint8)
                for (py, px) in coords:
                    mask[py - bbox[1], px - bbox[0]] = 1
                # resize mask to 16x16 fingerprint
                try:
                    small = cv2.resize(mask.astype('uint8')*255, (16,16), interpolation=cv2.INTER_AREA) if HAVE_CV2 else np.array(Image.fromarray((mask*255).astype('uint8')).resize((16,16))).astype(np.uint8)
                except Exception:
                    small = np.array(Image.fromarray((mask*255).astype('uint8')).resize((16,16))).astype(np.uint8)
                vec = (small.flatten()/255.0).astype(float)
                # simple descriptor: [area_norm, wh_ratio, vec...]
                area_norm = float(area) / (w_img*h_img)
                wh_ratio = float(mask_w)/float(mask_h) if mask_h>0 else 1.0
                desc = np.concatenate(([area_norm, wh_ratio], vec))
                results.append({'bbox': bbox, 'area': float(area), 'hu': desc.tolist()})
    return results


def cluster_descriptors(items, dist_thresh=0.45):
    clusters = []  # list of {members: [idx], centroid: vector}
    for i, it in enumerate(items):
        v = np.array(it['hu'])
        if np.all(v == 0):
            # degenerate descriptor, skip
            continue
        assigned = False
        for c in clusters:
            cent = c['centroid']
            d = np.linalg.norm(v - cent)
            if d < dist_thresh:
                c['members'].append(i)
                # update centroid
                c['centroid'] = (cent * (len(c['members']) - 1) + v) / len(c['members'])
                assigned = True
                break
        if not assigned:
            clusters.append({'members': [i], 'centroid': v.copy()})
    return clusters


def draw_clusters(pil_img, items, clusters, out_path):
    img_rgb = pil_img.convert('RGB')
    colors = []
    rng = np.random.RandomState(1234)
    for _ in clusters:
        colors.append(tuple(int(x) for x in rng.randint(50, 230, size=3)))
    # map item index to cluster id
    idx_to_cid = {}
    for cid, c in enumerate(clusters):
        for m in c['members']:
            idx_to_cid[m] = cid

    out_dir = Path(out_path).parent
    out_dir.mkdir(parents=True, exist_ok=True)

    if HAVE_CV2:
        img = np.array(img_rgb)
        for i, it in enumerate(items):
            bbox = it['bbox']
            x0,y0,x1,y1 = bbox
            cid = idx_to_cid.get(i, None)
            if cid is None:
                color = (180,180,180)
            else:
                color = colors[cid]
            cv2.rectangle(img, (x0,y0), (x1,y1), color, 2)
        Image.fromarray(img).save(out_path)
    else:
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img_rgb)
        for i, it in enumerate(items):
            bbox = it['bbox']
            x0,y0,x1,y1 = bbox
            cid = idx_to_cid.get(i, None)
            if cid is None:
                color = (180,180,180)
            else:
                color = colors[cid]
            draw.rectangle([x0,y0,x1,y1], outline=color, width=2)
        img_rgb.save(out_path)


def summarize_clusters(items, clusters):
    summary = []
    for cid, c in enumerate(clusters):
        members = c['members']
        bboxes = [items[i]['bbox'] for i in members]
        sample_bbox = bboxes[0]
        summary.append({'cluster_id': cid, 'count': len(members), 'sample_bbox': sample_bbox})
    # sort by count desc
    summary = sorted(summary, key=lambda x: x['count'], reverse=True)
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pdf', required=True)
    parser.add_argument('--page', type=int, default=0)
    parser.add_argument('--dpi', type=int, default=300)
    parser.add_argument('--out', default='outputs/debug_page_1.png')
    args = parser.parse_args()

    pdf_path = args.pdf
    page = args.page
    dpi = args.dpi

    pil_img = rasterize_pdf_page(pdf_path, page, dpi=dpi)
    bin_img = preprocess_image(pil_img)
    items = extract_contours(bin_img, min_area=80)
    if not items:
        print(json.dumps({'error': 'no_contours_found'}))
        return
    clusters = cluster_descriptors(items, dist_thresh=0.45)
    draw_clusters(pil_img, items, clusters, args.out)
    summary = summarize_clusters(items, clusters)

    result = {
        'file': os.path.basename(pdf_path),
        'page': page,
        'dpi': dpi,
        'image_width': pil_img.width,
        'image_height': pil_img.height,
        'total_candidates': len(items),
        'clusters': summary
    }
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
