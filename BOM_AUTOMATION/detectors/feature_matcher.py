"""
Feature matcher stub using ORB + BFMatcher.
Provides `feature_match(image, template, min_matches=8)` returning homography-based bbox if found.
"""

from typing import Optional, Dict

try:
    import cv2
    import numpy as np
except Exception:
    cv2 = None
    np = None


def feature_match(image, template, min_matches=8) -> Optional[Dict]:
    if cv2 is None or np is None:
        return None

    try:
        orb = cv2.ORB_create(1000)
        kp1, des1 = orb.detectAndCompute(template, None)
        kp2, des2 = orb.detectAndCompute(image, None)
        if des1 is None or des2 is None:
            return None
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = bf.match(des1, des2)
        matches = sorted(matches, key=lambda x: x.distance)
        if len(matches) < min_matches:
            return None
        src_pts = np.float32([kp1[m.queryIdx].pt for m in matches]).reshape(-1,1,2)
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in matches]).reshape(-1,1,2)
        M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
        h, w = template.shape[:2]
        pts = np.float32([[0,0],[0,h-1],[w-1,h-1],[w-1,0]]).reshape(-1,1,2)
        dst = cv2.perspectiveTransform(pts, M)
        bbox = [float(dst[0][0][0]), float(dst[0][0][1]), float(dst[2][0][0]), float(dst[2][0][1])]
        return {"bbox": bbox, "score": 1.0}
    except Exception:
        return None
