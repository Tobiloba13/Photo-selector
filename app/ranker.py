"""
Ranking layer — assembles ImageResult objects and returns top N.
"""

from __future__ import annotations

from typing import Optional

from PIL import Image

from app.orientation import get_orientation
from app.schemas import ImageResult, ImageScores
from app.scorer import compute_final_score, generate_tags, score_image


def rank_images(
    images: dict[str, Image.Image],
    duplicate_map: dict[str, str],
    top_n: int = 20,
    relevance_scores: Optional[dict[str, float]] = None,
) -> list[ImageResult]:
    """
    Score, sort, and return the top N images as ``ImageResult`` objects.

    Parameters
    ----------
    images:
        ``{filename: PIL.Image}`` after deduplication.
    duplicate_map:
        ``{duplicate_filename: original_filename}`` from the dedup step.
    top_n:
        Maximum number of results to return. Pass ``-1`` for all.
    relevance_scores:
        Optional pre-computed CLIP scores keyed by filename.

    Returns
    -------
    list[ImageResult]
        Sorted descending by ``final_score``, length ≤ ``top_n``.
    """
    results: list[ImageResult] = []
    relevance_scores = relevance_scores or {}

    for filename, img in images.items():
        rel = relevance_scores.get(filename)
        scores: ImageScores = score_image(img, relevance=rel)
        final = compute_final_score(scores)
        tags = generate_tags(scores, final)
        orientation = get_orientation(img)

        results.append(
            ImageResult(
                filename=filename,
                orientation=orientation,
                width=img.width,
                height=img.height,
                final_score=final,
                scores=scores,
                tags=tags,
                duplicate_of=None,
            )
        )

    # Add stub entries for duplicates (score 0, tagged)
    for dup_name, original in duplicate_map.items():
        results.append(
            ImageResult(
                filename=dup_name,
                orientation="landscape",
                width=0,
                height=0,
                final_score=0.0,
                scores=ImageScores(sharpness=0, brightness=0, contrast=0, resolution=0),
                tags=["duplicate"],
                duplicate_of=original,
            )
        )

    results.sort(key=lambda r: r.final_score, reverse=True)

    # Filter out duplicates from the ranked list; keep for reference only
    ranked = [r for r in results if r.duplicate_of is None]
    if top_n > 0:
        ranked = ranked[:top_n]

    return ranked
