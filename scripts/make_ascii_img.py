"""
make_ascii_img.py
------------------
Pipeline 1 (Portrait) - single stage.

Auto-detects source_photo.<any extension> at the repo root (or an explicit
--input path), prepares it in memory, converts it to a character grid, and
writes ascii-img.svg with a row-by-row typing reveal (SMIL, plays once,
no loop, then freezes).

Background removal is assumed to already be done to the source photo (e.g.
exported as a transparent PNG, or already composited onto a plain
background) - this script does not attempt background segmentation. If the
image has an alpha channel, it's flattened onto white here; otherwise it's
used as-is.

Monochrome by design: a single fill color keeps the portrait readable.
Per-character coloring is what makes most ASCII art look noisy.
"""

from __future__ import annotations

import argparse
import glob
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

# ---------------------------------------------------------------------------
# Photo discovery / prep constants
# ---------------------------------------------------------------------------
DEFAULT_STEM = "source_photo"
SUPPORTED_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif")
DEFAULT_MAX_WIDTH = 800  # px, before ASCII sampling

# ---------------------------------------------------------------------------
# ASCII rendering constants
# ---------------------------------------------------------------------------
# Density ramp: bright pixels -> sparse/blank characters, dark pixels -> dense
# characters. The leading space is deliberate: it makes a white background
# disappear instead of printing as visual noise around the subject.
RAMP = " .`:-=+*cs#%@"

# Characters are taller than they are wide, so columns are under-sampled
# relative to rows to avoid a horizontally stretched result.
CHAR_ASPECT_CORRECTION = 0.55

FONT_FAMILY = "'Courier New', monospace"
FONT_SIZE = 8  # px
LINE_HEIGHT = FONT_SIZE * 1.05
CHAR_WIDTH = FONT_SIZE * 0.6  # approx monospace advance width

FILL_COLOR = "#9fef9f"  # single terminal-green tone
BACKGROUND_COLOR = "#0d1117"  # GitHub dark-mode background, so it blends in

ROW_REVEAL_DURATION = 0.45  # seconds for one row's wipe-in
ROW_STAGGER_STEP = 0.05  # seconds between each row starting


def escape_svg_text(text: str) -> str:
    """Escape characters that would break XML/SVG if placed inside a tag body."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def write_text_file(path: str | Path, content: str) -> None:
    """Write text to `path`, creating parent directories if needed."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def svg_document(
    width: int, height: int, body: str, *, extra_defs: str = "", background: str | None = None
) -> str:
    """Minimal <svg> wrapper: optional defs + optional flat background + body."""
    defs_block = f"<defs>{extra_defs}</defs>" if extra_defs else ""
    bg_rect = f'<rect width="{width}" height="{height}" fill="{background}"/>' if background else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}">{defs_block}{bg_rect}{body}</svg>'
    )


def stagger_delays(count: int, start: float = 0.0, step: float = 0.08) -> list[float]:
    """Return `count` sequential animation begin-times (in seconds), used so
    rows reveal one after another instead of all at once.
    """
    return [round(start + i * step, 3) for i in range(count)]


def find_source_photo(explicit_path: str | None) -> Path:
    """Resolve the source photo to use.

    If `explicit_path` is given, it's used as-is (and must exist). Otherwise,
    this looks for a file literally named "source_photo.<ext>" in the current
    folder, trying every extension in SUPPORTED_EXTENSIONS (both lower- and
    upper-case) - so you never need to remember or pass the exact extension.
    """
    if explicit_path:
        path = Path(explicit_path)
        if not path.exists():
            raise FileNotFoundError(f"Could not find {path}")
        return path

    candidates: list[str] = []
    for ext in SUPPORTED_EXTENSIONS:
        candidates.extend(glob.glob(f"{DEFAULT_STEM}{ext}"))
        candidates.extend(glob.glob(f"{DEFAULT_STEM}{ext.upper()}"))

    if not candidates:
        raise FileNotFoundError(
            f"No file named '{DEFAULT_STEM}.<ext>' found in the current folder "
            f"(tried: {', '.join(SUPPORTED_EXTENSIONS)}). "
            f"Pass --input to point at your photo explicitly."
        )
    return Path(sorted(candidates)[0])


def flatten_transparency_to_white(image: np.ndarray) -> np.ndarray:
    """If `image` has an alpha channel, composite it onto pure white and
    return a 3-channel BGR image. If it has no alpha channel, return it
    unchanged.

    Pure white matters: the ASCII ramp maps bright pixels to blank space, so
    a white background disappears instead of printing as noise around the
    subject.
    """
    if image.ndim < 3 or image.shape[2] != 4:
        return image  # no alpha channel - nothing to flatten

    bgr = image[:, :, :3].astype(np.float32)
    alpha = image[:, :, 3:4].astype(np.float32) / 255.0
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
    aspect ratio. Never upscales.
    """
    height, width = image.shape[:2]
    if width <= max_width:
        return image
    scale = max_width / width
    new_size = (max_width, int(height * scale))
    return cv2.resize(image, new_size, interpolation=cv2.INTER_AREA)


def prepare_grayscale_array(input_path: Path, max_width: int) -> np.ndarray:
    """Load `input_path` (any image type/extension OpenCV supports) and
    return a contrast-boosted, resized grayscale array ready for ASCII
    conversion.
    """
    # IMREAD_UNCHANGED preserves an alpha channel if present.
    image = cv2.imread(str(input_path), cv2.IMREAD_UNCHANGED)
    if image is None:
        raise FileNotFoundError(f"Could not read image at {input_path}")

    on_white = flatten_transparency_to_white(image)
    gray_input = on_white[:, :, :3] if on_white.ndim == 3 else on_white
    gray = cv2.cvtColor(gray_input, cv2.COLOR_BGR2GRAY) if gray_input.ndim == 3 else gray_input
    contrasted = boost_contrast(gray)
    return resize_max_width(contrasted, max_width)


def grayscale_array_to_ascii_rows(gray: np.ndarray, columns: int) -> list[str]:
    """Downsample a grayscale array to a `columns`-wide character grid and
    map brightness to characters from RAMP.
    """
    pil_img = Image.fromarray(gray)
    width, height = pil_img.size
    rows = max(1, round((height / width) * columns * CHAR_ASPECT_CORRECTION))
    small = pil_img.resize((columns, rows), Image.LANCZOS)
    pixels = np.array(small)

    ramp_indices = (pixels.astype(np.float32) / 255.0 * (len(RAMP) - 1)).astype(int)
    # Bright pixel -> high index -> we want the *sparse* end of the ramp,
    # so invert: dark pixel should pick dense glyphs.
    ramp_indices = (len(RAMP) - 1) - ramp_indices

    return ["".join(RAMP[i] for i in row) for row in ramp_indices]


def build_row_markup(text: str, row_index: int, begin_time: float) -> str:
    """Build one <g> element: a row of ASCII text revealed by an animated
    clipPath rect (wipes left to right) plus a small cursor block that rides
    the reveal edge and then disappears.
    """
    y = (row_index + 1) * LINE_HEIGHT
    full_width = len(text) * CHAR_WIDTH
    clip_id = f"clip-row-{row_index}"
    safe_text = escape_svg_text(text)

    clip_def = (
        f'<clipPath id="{clip_id}">'
        f'<rect x="0" y="{y - LINE_HEIGHT}" width="0" height="{LINE_HEIGHT}">'
        f'<animate attributeName="width" from="0" to="{full_width}" '
        f'dur="{ROW_REVEAL_DURATION}s" begin="{begin_time}s" '
        f'fill="freeze" calcMode="linear"/>'
        f"</rect>"
        f"</clipPath>"
    )

    text_el = (
        f'<g clip-path="url(#{clip_id})">'
        f'<text x="0" y="{y}" font-family="{FONT_FAMILY}" font-size="{FONT_SIZE}" '
        f'xml:space="preserve" fill="{FILL_COLOR}">{safe_text}</text>'
        f"</g>"
    )

    cursor_fade_start = begin_time + ROW_REVEAL_DURATION
    cursor = (
        f'<rect y="{y - FONT_SIZE + 1}" width="{CHAR_WIDTH * 0.8}" '
        f'height="{FONT_SIZE}" fill="{FILL_COLOR}">'
        f'<animate attributeName="x" from="0" to="{full_width}" '
        f'dur="{ROW_REVEAL_DURATION}s" begin="{begin_time}s" fill="freeze" calcMode="linear"/>'
        f'<animate attributeName="opacity" from="1" to="0" dur="0.2s" '
        f'begin="{cursor_fade_start}s" fill="freeze"/>'
        f"</rect>"
    )

    return clip_def + text_el + cursor


def build_ascii_svg(rows: list[str]) -> str:
    row_count = len(rows)
    col_count = max((len(r) for r in rows), default=0)

    width = round(col_count * CHAR_WIDTH) + 4
    height = round(row_count * LINE_HEIGHT) + 4

    begin_times = stagger_delays(row_count, start=0.15, step=ROW_STAGGER_STEP)

    body_parts = [
        build_row_markup(row_text, i, begin_time)
        for i, (row_text, begin_time) in enumerate(zip(rows, begin_times))
    ]

    body = "".join(body_parts)
    return svg_document(width, height, body, background=BACKGROUND_COLOR)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert a photo (background already removed) into an animated ASCII SVG."
    )
    parser.add_argument(
        "--input",
        default=None,
        help="Path to the source photo. Auto-detected (source_photo.<any ext>) if omitted.",
    )
    parser.add_argument("--output", default="ascii-img.svg", help="Path to write the ASCII SVG.")
    parser.add_argument("--columns", type=int, default=100, help="Number of ASCII character columns.")
    parser.add_argument(
        "--max-width", type=int, default=DEFAULT_MAX_WIDTH, help="Max width in px before ASCII sampling."
    )
    args = parser.parse_args()

    input_path = find_source_photo(args.input)
    print(f"Using source photo: {input_path}")

    gray = prepare_grayscale_array(input_path, args.max_width)
    rows = grayscale_array_to_ascii_rows(gray, args.columns)
    svg = build_ascii_svg(rows)
    write_text_file(args.output, svg)
    print(f"Wrote {len(rows)} rows -> {args.output}")


if __name__ == "__main__":
    main()