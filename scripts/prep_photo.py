"""
prep_photo.py
--------------
Pipeline 1 (Portrait) - Step A.

source_photo.png (background already removed, may have transparency)
                  -> contrast boosted -> grayscale
                  -> resized -> data/portrait-prepped.png

This intermediate PNG is consumed by make_ascii_svg.py. It is regenerated
by hand whenever you change your source photo (not part of the daily
GitHub Actions run).

Background removal itself is assumed to already be done to the source
photo (e.g. exported as a transparent PNG). If the image carries an alpha
channel, it is flattened onto pure white here; otherwise it's used as-is.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np


def flatten_transparency_to_white(image: np.ndarray) -> np.ndarray:
    """If `image` has an alpha channel (already background-removed), composite
    it onto pure white and return a 3-channel BGR image. If it has no alpha
    channel, return it unchanged.

    Pure white matters: the ASCII ramp used later maps bright pixels to
    blank space, so a white background disappears instead of printing as
    noise around the subject.
    """
    if image.ndim < 3 or image.shape[2] != 4:
        return image  # no alpha channel - nothing to flatten

    bgr = image[:, :, :3].astype(np.float32)
    alpha = (image[:, :, 3:4].astype(np.float32)) / 255.0
    white_bg = np.full_like(bgr, 255.0)
    composited = bgr * alpha + white_bg * (1.0 - alpha)
    return composited.astype(np.uint8)


def boost_contrast(gray: np.ndarray) -> np.ndarray:
    """Apply CLAHE (Contrast-Limited Adaptive Histogram Equalization) so a
    flatly-lit face gets real local highlights/shadows instead of mapping to
    one or two ASCII density levels.
    """
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    return clahe.apply(gray)


def resize_max_width(image: np.ndarray, max_width: int) -> np.ndarray:
    """Downscale `image` so its width is at most `max_width`, preserving
    aspect ratio. Upscaling is never done here (that happens implicitly
    when make_ascii_svg.py samples a coarser character grid).
    """
    height, width = image.shape[:2]
    if width <= max_width:
        return image
    scale = max_width / width
    new_size = (max_width, int(height * scale))
    return cv2.resize(image, new_size, interpolation=cv2.INTER_AREA)


def prep_photo(input_path: Path, output_path: Path, max_width: int) -> None:
    # IMREAD_UNCHANGED preserves an alpha channel if the photo already has
    # its background removed (e.g. exported as a transparent PNG).
    image = cv2.imread(str(input_path), cv2.IMREAD_UNCHANGED)
    if image is None:
        raise FileNotFoundError(f"Could not read image at {input_path}")

    on_white = flatten_transparency_to_white(image)
    gray_input = on_white[:, :, :3] if on_white.ndim == 3 else on_white
    gray = cv2.cvtColor(gray_input, cv2.COLOR_BGR2GRAY) if gray_input.ndim == 3 else gray_input
    contrasted = boost_contrast(gray)
    resized = resize_max_width(contrasted, max_width)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), resized)
    print(f"Wrote prepped portrait -> {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare a photo for ASCII conversion.")
    parser.add_argument("--input", default="source_photo.png", help="Path to the source photo.")
    parser.add_argument(
        "--output",
        default="data/portrait-prepped.png",
        help="Path to write the prepped grayscale image.",
    )
    parser.add_argument(
        "--max-width", type=int, default=800, help="Maximum width in pixels after resizing."
    )
    args = parser.parse_args()

    prep_photo(Path(args.input), Path(args.output), args.max_width)


if __name__ == "__main__":
    main()