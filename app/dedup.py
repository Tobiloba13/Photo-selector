from PIL import Image
import imagehash
from pathlib import Path

# Hamming-distance threshold: 0 = identical, ≤10 is a typical "near-duplicate"
HASH_THRESHOLD = 8


def deduplicate(
    images: dict[str, Image.Image],
    threshold: int = HASH_THRESHOLD,
) -> tuple[dict[str, Image.Image], dict[str, str]]:
    """
    Remove near-duplicate images using perceptual hashing (pHash).

    Parameters
    ----------
    images:
        Mapping of ``filename -> PIL.Image``.
    threshold:
        Maximum Hamming distance to consider two images duplicates.
        Lower = stricter. ``0`` means pixel-perfect identical hashes only.

    Returns
    -------
    unique:
        Filtered dict with duplicates removed (keeps first seen).
    duplicate_map:
        ``{duplicate_filename: original_filename}`` for every removed image.
    """
    hashes: dict[str, imagehash.ImageHash] = {}
    unique: dict[str, Image.Image] = {}
    duplicate_map: dict[str, str] = {}

    for filename, img in images.items():
        h = imagehash.phash(img)
        matched_original: str | None = None

        for seen_name, seen_hash in hashes.items():
            if abs(h - seen_hash) <= threshold:
                matched_original = seen_name
                break

        if matched_original:
            duplicate_map[filename] = matched_original
        else:
            hashes[filename] = h
            unique[filename] = img

    return unique, duplicate_map
