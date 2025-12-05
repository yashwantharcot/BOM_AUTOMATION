"""
Template matcher using OpenCV's matchTemplate with multi-scale and multi-rotation support.
Layer 1: Template Matching (5.2)
- Multi-scale template matching
- Multi-rotation (0°, 90°, 180°, 270°)
- Sliding window match
- Threshold ≥ symbol.threshold
"""

from typing import List, Dict, Optional

try:
    import cv2
    import numpy as np
except Exception:
    cv2 = None
    np = None


def match_template(image, template, scales=None, rotations=None, thresh=0.8) -> List[Dict]:
    """
    Template matching with multi-scale and multi-rotation support
    
    Args:
        image: Input image (grayscale or BGR)
        template: Template image to match
        scales: List of scale factors (default: [1.0])
        rotations: List of rotation angles in degrees (default: [0, 90, 180, 270])
        thresh: Confidence threshold (default: 0.8)
        
    Returns:
        List of detections {bbox: [x1,y1,x2,y2], score: float}
    """
    if cv2 is None or np is None:
        return []
    
    if scales is None:
        scales = [1.0]
    if rotations is None:
        rotations = [0, 90, 180, 270]  # Multi-rotation as per spec 5.2

    detections = []
    img_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY) if len(template.shape) == 3 else template
    
    h_template, w_template = template_gray.shape[:2]
    h_img, w_img = img_gray.shape[:2]
    
    for rotation in rotations:
        # Rotate template
        if rotation == 0:
            rotated_template = template_gray
        elif rotation == 90:
            rotated_template = cv2.rotate(template_gray, cv2.ROTATE_90_CLOCKWISE)
        elif rotation == 180:
            rotated_template = cv2.rotate(template_gray, cv2.ROTATE_180)
        elif rotation == 270:
            rotated_template = cv2.rotate(template_gray, cv2.ROTATE_90_COUNTERCLOCKWISE)
        else:
            # Arbitrary rotation
            center = (w_template // 2, h_template // 2)
            M = cv2.getRotationMatrix2D(center, rotation, 1.0)
            rotated_template = cv2.warpAffine(template_gray, M, (w_template, h_template))
        
        h_rot, w_rot = rotated_template.shape[:2]
        
        for scale in scales:
            try:
                # Scale template
                if scale != 1.0:
                    new_w = int(w_rot * scale)
                    new_h = int(h_rot * scale)
                    
                    # Skip if scaled template is larger than image
                    if new_w > w_img or new_h > h_img:
                        continue
                    
                    resized = cv2.resize(rotated_template, (new_w, new_h), interpolation=cv2.INTER_AREA)
                else:
                    resized = rotated_template
                    new_w, new_h = w_rot, h_rot
                
                # Template matching
                res = cv2.matchTemplate(img_gray, resized, cv2.TM_CCOEFF_NORMED)
                loc = np.where(res >= thresh)
                
                for pt in zip(*loc[::-1]):
                    score = float(res[pt[1], pt[0]])
                    x1, y1 = pt[0], pt[1]
                    x2, y2 = x1 + new_w, y1 + new_h
                    
                    detections.append({
                        "bbox": [x1, y1, x2, y2],
                        "score": score,
                        "rotation": rotation,
                        "scale": scale
                    })
            except Exception as e:
                continue
    
    return detections


def match_template_single_scale(image, template, thresh=0.8) -> List[Dict]:
    """Simplified version for backward compatibility"""
    return match_template(image, template, scales=[1.0], rotations=[0], thresh=thresh)
