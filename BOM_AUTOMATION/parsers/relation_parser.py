"""
Relation parser stub: takes lists of symbols and texts with bboxes and returns candidate relations.
Function: `link_symbols_to_texts(symbols, texts)` -> list of relations {symbol_index, text_index, score}
"""

from typing import List, Dict

def bbox_center(bbox):
    x0, y0, x1, y1 = bbox
    return ((x0 + x1) / 2.0, (y0 + y1) / 2.0)


def distance(a, b):
    return ((a[0]-b[0])**2 + (a[1]-b[1])**2) ** 0.5


def link_symbols_to_texts(symbols: List[Dict], texts: List[Dict], max_dist=500) -> List[Dict]:
    relations = []
    for i, sym in enumerate(symbols):
        sc = bbox_center(sym['bbox'])
        best = None
        best_score = 0.0
        for j, txt in enumerate(texts):
            tc = bbox_center(txt['bbox'])
            d = distance(sc, tc)
            score = max(0.0, 1.0 - (d / max_dist))
            if score > best_score:
                best_score = score
                best = j
        if best is not None and best_score > 0.1:
            relations.append({"symbol_index": i, "text_index": best, "score": best_score})
    return relations
