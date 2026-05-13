from PIL import Image
from typing import Literal


def get_orientation(img: Image.Image) -> Literal["portrait", "landscape", "square"]:
    """
    Determine orientation after applying EXIF rotation so the reported
    orientation always reflects how a human would view the image.
    """
    img = _apply_exif_rotation(img)
    w, h = img.size
    if w > h:
        return "landscape"
    elif h > w:
        return "portrait"
    return "square"


def _apply_exif_rotation(img: Image.Image) -> Image.Image:
    """Rotate image according to EXIF orientation tag."""
    try:
        exif = img._getexif()  # type: ignore[attr-defined]
        if exif is None:
            return img
        orientation_tag = 274  # EXIF tag for Orientation
        orientation = exif.get(orientation_tag)
        rotation_map = {3: 180, 6: 270, 8: 90}
        if orientation in rotation_map:
            img = img.rotate(rotation_map[orientation], expand=True)
    except (AttributeError, Exception):
        pass
    return img
