"""
photo-selector — FastAPI backend
Cloud-safe: per-file size cap, batch chunking, memory-conscious image loading.
"""

from __future__ import annotations

import gc
import io
import os
from typing import Annotated, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, UnidentifiedImageError

from app.dedup import deduplicate
from app.ranker import rank_images
from app.schemas import RankResponse
from app.utils import score_relevance

app = FastAPI(
    title="Photo Selector API",
    description="Upload a batch of images; get back ranked, deduplicated top picks.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_TYPES  = {"image/jpeg", "image/png", "image/webp", "image/tiff"}
MAX_FILE_BYTES = int(os.getenv("MAX_FILE_MB", "20")) * 1024 * 1024
MAX_FILES      = int(os.getenv("MAX_FILES", "100"))
MAX_DIMENSION  = int(os.getenv("MAX_DIMENSION", "3000"))
CHUNK_SIZE     = int(os.getenv("CHUNK_SIZE", "10"))


def _shrink_if_needed(img: Image.Image) -> Image.Image:
    w, h = img.size
    long_edge = max(w, h)
    if long_edge > MAX_DIMENSION:
        scale = MAX_DIMENSION / long_edge
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    return img


def _load_images(files: list[UploadFile]) -> dict[str, Image.Image]:
    loaded: dict[str, Image.Image] = {}
    for f in files:
        if f.content_type not in ALLOWED_TYPES:
            continue
        data = f.file.read()
        if len(data) > MAX_FILE_BYTES:
            del data
            continue
        try:
            img = Image.open(io.BytesIO(data))
            img.load()
            img = img.convert("RGB")
            img = _shrink_if_needed(img)
            loaded[f.filename or f"file_{len(loaded)}"] = img
        except (UnidentifiedImageError, Exception):
            pass
        del data
    return loaded


def _process_in_chunks(images, prompt, dedup_threshold, top_n):
    unique, duplicate_map = deduplicate(images, threshold=dedup_threshold)
    items = list(unique.items())
    all_results = []
    for i in range(0, len(items), CHUNK_SIZE):
        chunk = dict(items[i : i + CHUNK_SIZE])
        rel_scores = score_relevance(chunk, prompt) if prompt else {}
        chunk_results = rank_images(images=chunk, duplicate_map={}, top_n=-1, relevance_scores=rel_scores)
        all_results.extend(chunk_results)
        gc.collect()
    all_results.sort(key=lambda r: r.final_score, reverse=True)
    if top_n > 0:
        all_results = all_results[:top_n]
    return unique, duplicate_map, all_results


@app.get("/health")
def health():
    return {"status": "ok", "max_file_mb": MAX_FILE_BYTES // (1024 * 1024), "max_files": MAX_FILES}


@app.post("/rank", response_model=RankResponse)
async def rank(
    files: Annotated[list[UploadFile], File(description="Batch of image files")],
    top_n: Annotated[int, Form()] = 20,
    prompt: Annotated[Optional[str], Form()] = None,
    dedup_threshold: Annotated[int, Form()] = 8,
):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")
    if len(files) > MAX_FILES:
        raise HTTPException(status_code=413, detail=f"Max {MAX_FILES} files per request.")

    images = _load_images(files)
    if not images:
        raise HTTPException(status_code=422, detail="No valid images could be decoded.")

    total_uploaded = len(images)
    _, duplicate_map, ranked = _process_in_chunks(images, prompt, dedup_threshold, top_n)

    for img in images.values():
        img.close()
    del images
    gc.collect()

    return RankResponse(
        total_uploaded=total_uploaded,
        duplicates_removed=len(duplicate_map),
        ranked=ranked,
        prompt_used=prompt,
    )
