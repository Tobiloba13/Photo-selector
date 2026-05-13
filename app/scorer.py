"""
Image quality scorer — v1 algorithm.

Weights
-------
sharpness   35 %  – Laplacian variance (high = sharp edges)
brightness  20 %  – proximity to ideal mid-range (0.4–0.6 of 255)
contrast    15 %  – grayscale standard deviation
resolution  20 %  – normalised pixel count
relevance   10 %  – optional CLIP cosine similarity
"""

from __future__ import annotations

import math
from typing import Optional

import cv2
import numpy as np
from PIL import Image

from app.schemas import ImageScores

# ----- tuning constants -----
RESOLUTION_CEILING = 4000 * 3000          # 12 MP — scores above this cap at 1.0
BRIGHTNESS_IDEAL_LOW = 80                  # out of 255
BRIGHTNESS_IDEAL_HIGH = 180
SHARPNESS_CEILING = 2000.0                 # Laplacian variance cap

WEIGHTS = {
    "sharpness": 0.35,
    "brightness": 0.20,
    "contrast": 0.15,
    "resolution": 0.20,
    "relevance": 0.10,
}


# ---------------------------------------------------------------------------
# Individual signal scorers
# ---------------------------------------------------------------------------

def _score_sharpness(gray: np.ndarray) -> float:
    variance = cv2.Laplacian(gray, cv2.CV_64F).var()
    return float(min(variance / SHARPNESS_CEILING, 1.0))


def _score_brightness(gray: np.ndarray) -> float:
    mean = float(gray.mean())
    if BRIGHTNESS_IDEAL_LOW <= mean <= BRIGHTNESS_IDEAL_HIGH:
        return 1.0
    if mean < BRIGHTNESS_IDEAL_LOW:
        return mean / BRIGHTNESS_IDEAL_LOW
    # mean > BRIGHTNESS_IDEAL_HIGH
    excess = mean - BRIGHTNESS_IDEAL_HIGH
    return max(0.0, 1.0 - excess / (255 - BRIGHTNESS_IDEAL_HIGH))


def _score_contrast(gray: np.ndarray) -> float:
    std = float(gray.std())
    # std dev of ~60 is typical for a well-exposed, varied scene
    return float(min(std / 80.0, 1.0))


def _score_resolution(img: Image.Image) -> float:
    pixels = img.width * img.height
    return float(min(pixels / RESOLUTION_CEILING, 1.0))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def score_image(
    img: Image.Image,
    relevance: Optional[float] = None,
) -> ImageScores:
    """Compute all signal scores for a single PIL image."""
    gray = np.array(img.convert("L"))

    return ImageScores(
        sharpness=_score_sharpness(gray),
        brightness=_score_brightness(gray),
        contrast=_score_contrast(gray),
        resolution=_score_resolution(img),
        relevance=relevance,
    )


def compute_final_score(scores: ImageScores) -> float:
    """
    Weighted average of available signals.
    If ``relevance`` is None the 10 % weight is redistributed proportionally.
    """
    active_weights = {k: v for k, v in WEIGHTS.items() if k != "relevance" or scores.relevance is not None}
    total_weight = sum(active_weights.values())

    total = 0.0
    for key, w in active_weights.items():
        value = getattr(scores, key) or 0.0
        total += (w / total_weight) * value

    return round(float(total), 4)


def generate_tags(scores: ImageScores, final_score: float) -> list[str]:
    """Return human-readable quality tags based on individual signal thresholds."""
    tags: list[str] = []

    if scores.sharpness >= 0.65:
        tags.append("sharp")
    elif scores.sharpness < 0.25:
        tags.append("blurry")

    if scores.brightness >= 0.75:
        tags.append("well-lit")
    elif scores.brightness < 0.35:
        tags.append("poorly-lit")

    if scores.contrast >= 0.65:
        tags.append("high-contrast")

    if scores.resolution >= 0.75:
        tags.append("high-res")
    elif scores.resolution < 0.25:
        tags.append("low-res")

    if scores.relevance is not None and scores.relevance >= 0.6:
        tags.append("relevant")

    if final_score >= 0.75:
        tags.append("top-pick")

    return tags
