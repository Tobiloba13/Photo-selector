"""Tests for the image quality scorer."""

import numpy as np
import pytest
from PIL import Image

from app.scorer import compute_final_score, generate_tags, score_image
from app.schemas import ImageScores


def _solid_image(w: int, h: int, brightness: int) -> Image.Image:
    arr = np.full((h, w, 3), brightness, dtype=np.uint8)
    return Image.fromarray(arr, "RGB")


def _noisy_image(w: int, h: int) -> Image.Image:
    rng = np.random.default_rng(42)
    arr = rng.integers(0, 256, (h, w, 3), dtype=np.uint8)
    return Image.fromarray(arr, "RGB")


class TestScoreImage:
    def test_returns_image_scores_instance(self):
        img = _solid_image(800, 600, 128)
        scores = score_image(img)
        assert isinstance(scores, ImageScores)

    def test_all_scores_in_range(self):
        img = _noisy_image(1024, 768)
        scores = score_image(img)
        for field in ("sharpness", "brightness", "contrast", "resolution"):
            val = getattr(scores, field)
            assert 0.0 <= val <= 1.0, f"{field} out of range: {val}"

    def test_bright_image_low_brightness_score(self):
        img = _solid_image(800, 600, 250)  # near-white
        scores = score_image(img)
        assert scores.brightness < 0.5

    def test_ideal_brightness_image(self):
        img = _solid_image(800, 600, 128)  # mid-grey
        scores = score_image(img)
        assert scores.brightness >= 0.9

    def test_dark_image_low_brightness_score(self):
        img = _solid_image(800, 600, 10)  # near-black
        scores = score_image(img)
        assert scores.brightness < 0.2

    def test_relevance_passed_through(self):
        img = _solid_image(400, 300, 128)
        scores = score_image(img, relevance=0.75)
        assert scores.relevance == pytest.approx(0.75)

    def test_no_relevance_by_default(self):
        img = _solid_image(400, 300, 128)
        scores = score_image(img)
        assert scores.relevance is None


class TestComputeFinalScore:
    def test_score_in_range(self):
        scores = ImageScores(sharpness=0.8, brightness=0.9, contrast=0.7, resolution=0.6)
        final = compute_final_score(scores)
        assert 0.0 <= final <= 1.0

    def test_perfect_scores_give_one(self):
        scores = ImageScores(sharpness=1.0, brightness=1.0, contrast=1.0, resolution=1.0, relevance=1.0)
        assert compute_final_score(scores) == pytest.approx(1.0, abs=1e-4)

    def test_zero_scores_give_zero(self):
        scores = ImageScores(sharpness=0.0, brightness=0.0, contrast=0.0, resolution=0.0, relevance=0.0)
        assert compute_final_score(scores) == pytest.approx(0.0, abs=1e-4)

    def test_missing_relevance_redistributes_weight(self):
        s_with = ImageScores(sharpness=1.0, brightness=1.0, contrast=1.0, resolution=1.0, relevance=1.0)
        s_without = ImageScores(sharpness=1.0, brightness=1.0, contrast=1.0, resolution=1.0)
        # Both perfect signals → both should be 1.0
        assert compute_final_score(s_with) == pytest.approx(1.0, abs=1e-4)
        assert compute_final_score(s_without) == pytest.approx(1.0, abs=1e-4)


class TestGenerateTags:
    def test_sharp_tag(self):
        scores = ImageScores(sharpness=0.8, brightness=0.5, contrast=0.5, resolution=0.5)
        tags = generate_tags(scores, 0.8)
        assert "sharp" in tags

    def test_blurry_tag(self):
        scores = ImageScores(sharpness=0.1, brightness=0.5, contrast=0.5, resolution=0.5)
        tags = generate_tags(scores, 0.3)
        assert "blurry" in tags

    def test_top_pick_tag(self):
        scores = ImageScores(sharpness=0.9, brightness=0.9, contrast=0.9, resolution=0.9)
        tags = generate_tags(scores, 0.9)
        assert "top-pick" in tags

    def test_no_duplicate_tags(self):
        scores = ImageScores(sharpness=0.9, brightness=0.9, contrast=0.9, resolution=0.9)
        tags = generate_tags(scores, 0.9)
        assert len(tags) == len(set(tags))
