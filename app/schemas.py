from pydantic import BaseModel, Field
from typing import Literal, Optional


class ImageScores(BaseModel):
    sharpness: float = Field(..., ge=0.0, le=1.0, description="Laplacian variance, normalised 0–1")
    brightness: float = Field(..., ge=0.0, le=1.0, description="Proximity to ideal mid-range brightness")
    contrast: float = Field(..., ge=0.0, le=1.0, description="Grayscale std-dev, normalised 0–1")
    resolution: float = Field(..., ge=0.0, le=1.0, description="Pixel count normalised against ceiling")
    relevance: Optional[float] = Field(None, ge=0.0, le=1.0, description="CLIP cosine similarity (optional)")


class ImageResult(BaseModel):
    filename: str
    orientation: Literal["portrait", "landscape", "square"]
    width: int
    height: int
    final_score: float = Field(..., ge=0.0, le=1.0)
    scores: ImageScores
    tags: list[str] = Field(default_factory=list, description="Human-readable quality tags")
    duplicate_of: Optional[str] = Field(None, description="Filename this image was flagged as duplicate of")


class RankResponse(BaseModel):
    total_uploaded: int
    duplicates_removed: int
    ranked: list[ImageResult]
    prompt_used: Optional[str] = None
