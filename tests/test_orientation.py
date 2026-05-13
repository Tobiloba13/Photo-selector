"""Tests for orientation detection."""

import io
import pytest
from PIL import Image

from app.orientation import get_orientation


def _make_img(w: int, h: int) -> Image.Image:
    return Image.new("RGB", (w, h), color=(128, 128, 128))


def test_landscape():
    assert get_orientation(_make_img(1920, 1080)) == "landscape"


def test_portrait():
    assert get_orientation(_make_img(1080, 1920)) == "portrait"


def test_square():
    assert get_orientation(_make_img(500, 500)) == "square"
