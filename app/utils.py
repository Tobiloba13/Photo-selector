"""
Optional CLIP-based relevance scorer.

Install extras to enable:
    pip install transformers torch open-clip-torch

If dependencies are missing the function returns None for every image,
and the ranker redistributes the 10 % relevance weight automatically.
"""

from __future__ import annotations

from typing import Optional

from PIL import Image

try:
    import open_clip
    import torch

    _CLIP_AVAILABLE = True
except ImportError:
    _CLIP_AVAILABLE = False


_model = None
_preprocess = None
_tokenizer = None


def _load_model():
    global _model, _preprocess, _tokenizer
    if _model is None:
        _model, _, _preprocess = open_clip.create_model_and_transforms(
            "ViT-B-32", pretrained="openai"
        )
        _model.eval()
        _tokenizer = open_clip.get_tokenizer("ViT-B-32")


def score_relevance(
    images: dict[str, Image.Image],
    prompt: str,
) -> dict[str, float]:
    """
    Compute cosine similarity between each image and the text ``prompt``.

    Returns
    -------
    dict[str, float]
        ``{filename: score}`` where score ∈ [0, 1].
        Returns an empty dict if CLIP is not installed.
    """
    if not _CLIP_AVAILABLE or not prompt.strip():
        return {}

    import torch

    _load_model()
    assert _model is not None and _preprocess is not None and _tokenizer is not None

    text_tokens = _tokenizer([prompt])
    with torch.no_grad():
        text_features = _model.encode_text(text_tokens)
        text_features /= text_features.norm(dim=-1, keepdim=True)

    scores: dict[str, float] = {}
    for filename, img in images.items():
        tensor = _preprocess(img.convert("RGB")).unsqueeze(0)
        with torch.no_grad():
            img_features = _model.encode_image(tensor)
            img_features /= img_features.norm(dim=-1, keepdim=True)
            similarity = (img_features @ text_features.T).item()
        # Cosine similarity is in [-1, 1]; map to [0, 1]
        scores[filename] = float((similarity + 1) / 2)

    return scores
