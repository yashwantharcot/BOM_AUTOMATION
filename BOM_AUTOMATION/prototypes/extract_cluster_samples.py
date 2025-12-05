"""
Extract sample crop images for clusters found by the prototype.
Reads `outputs/prototype_result_page_0.json`, rasterizes the page from the original PDF,
crops the `sample_bbox` for top clusters and writes PNGs to `outputs/samples/`.

Usage:
    python prototypes/extract_cluster_samples.py --json outputs/prototype_result_page_0.json --pdf H.pdf --top 20 --page 0

"""
import argparse
import json
from pathlib import Path
from PIL import Image
import fitz


def rasterize_pdf_page(pdf_path, page_number=0, dpi=300):
    doc = fitz.open(pdf_path)
    page = doc.load_page(page_number)
    mat = fitz.Matrix(dpi / 72.0, dpi / 72.0)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    doc.close()
    return img


def crop_and_save(img, bbox, out_path, pad=8):
    x0,y0,x1,y1 = bbox
    w,h = img.size
    x0 = max(0, int(x0 - pad))
    y0 = max(0, int(y0 - pad))
    x1 = min(w, int(x1 + pad))
    y1 = min(h, int(y1 + pad))
    crop = img.crop((x0, y0, x1, y1))
    outp = Path(out_path)
    outp.parent.mkdir(parents=True, exist_ok=True)
    crop.save(outp)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--json', required=True)
    parser.add_argument('--pdf', required=True)
    parser.add_argument('--page', type=int, default=0)
    parser.add_argument('--dpi', type=int, default=300)
    parser.add_argument('--top', type=int, default=20)
    args = parser.parse_args()

    jpath = Path(args.json)
    pdf = args.pdf
    page = args.page

    with open(jpath, 'r') as f:
        data = json.load(f)
    clusters = data.get('clusters', [])
    # filter clusters with count>=3
    clusters = [c for c in clusters if c.get('count',0) >= 3]
    clusters = sorted(clusters, key=lambda x: -x['count'])[:args.top]

    img = rasterize_pdf_page(pdf, page, dpi=args.dpi)
    out_index = []
    for c in clusters:
        cid = c['cluster_id']
        cnt = c['count']
        bbox = c['sample_bbox']
        out_file = f"outputs/samples/cluster_{cid}_count_{cnt}.png"
        crop_and_save(img, bbox, out_file)
        out_index.append({'cluster_id': cid, 'count': cnt, 'sample': out_file, 'bbox': bbox})

    idx_path = Path('outputs/samples/index.json')
    idx_path.parent.mkdir(parents=True, exist_ok=True)
    with open(idx_path, 'w') as f:
        json.dump({'file': data.get('file'), 'page': data.get('page'), 'samples': out_index}, f, indent=2)

    print(f"Wrote {len(out_index)} samples to outputs/samples/")

if __name__ == '__main__':
    main()
