from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image

import config
from lib.svg_common import escape_svg_text, svg_document, write_text_file

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent

# Density ramp: bright pixels -> sparse/blank characters, dark pixels -> dense
# characters. The leading space is deliberate: it makes the (white) background
# disappear instead of printing as visual noise around the subject.
RAMP = " .`:-=+*cs#%@"
CHAR_ASPECT_CORRECTION = 0.55  # chars are taller than wide; undersample columns to compensate

FONT_FAMILY = "'Courier New', monospace"
FONT_SIZE = 8  # px
LINE_HEIGHT = FONT_SIZE * 1.05
CHAR_WIDTH = FONT_SIZE * 0.6  # approx monospace advance width

FILL_COLOR = "#9fef9f"
BACKGROUND_COLOR = "#0d1117"  # GitHub dark-mode background, so it blends in

ROW_REVEAL_DURATION = 0.45  # seconds for one row's wipe-in
ROW_STAGGER_STEP = 0.05  # seconds between each row starting


def find_source_photo(directory: Path) -> Path:
    """Find a 'source_photo.*' file (any extension/case) in `directory`."""
    for entry in sorted(directory.iterdir()):
        if entry.is_file() and entry.stem.lower() == "source_photo":
            return entry
    raise FileNotFoundError(
        f"No 'source_photo.*' file found in {directory}. Put your "
        "background-stripped photo there and name it 'source_photo' "
        "(any extension, e.g. source_photo.png), then re-run this script."
    )


def load_grayscale(image_path: Path) -> Image.Image:
    """Flatten the source photo to grayscale. Transparent pixels (from a
    background-stripped PNG) are composited onto white first so they land
    on the blank end of RAMP instead of rendering as solid black.
    """
    img = Image.open(image_path)
    if img.mode in ("RGBA", "LA") or "transparency" in img.info:
        img = img.convert("RGBA")
        canvas = Image.new("RGBA", img.size, (255, 255, 255, 255))
        img = Image.alpha_composite(canvas, img)
    return img.convert("L")


def image_to_ascii_rows(image_path: Path, columns: int) -> list[str]:
    """Downsample the source image to a `columns`-wide grid and map
    brightness to characters from RAMP.
    """
    img = load_grayscale(image_path)
    width, height = img.size
    rows = max(1, round((height / width) * columns * CHAR_ASPECT_CORRECTION))
    pixels = np.array(img.resize((columns, rows), Image.LANCZOS))

    # Bright pixel -> high index -> we want the sparse end of RAMP, so invert.
    ramp_indices = (len(RAMP) - 1) - (pixels.astype(np.float32) / 255.0 * (len(RAMP) - 1)).astype(int)
    return ["".join(RAMP[i] for i in row) for row in ramp_indices]


def build_row_markup(text: str, row_index: int, begin_time: float) -> str:
    """One <g>: ASCII row revealed left-to-right by an animated clipPath,
    plus a cursor block riding the reveal edge that fades once it's done.
    """
    y = (row_index + 1) * LINE_HEIGHT
    full_width = len(text) * CHAR_WIDTH
    clip_id = f"clip-row-{row_index}"
    safe_text = escape_svg_text(text)

    clip_def = (
        f'<clipPath id="{clip_id}"><rect x="0" y="{y - LINE_HEIGHT}" width="0" height="{LINE_HEIGHT}">'
        f'<animate attributeName="width" from="0" to="{full_width}" dur="{ROW_REVEAL_DURATION}s" '
        f'begin="{begin_time}s" fill="freeze" calcMode="linear"/></rect></clipPath>'
    )
    text_el = (
        f'<g clip-path="url(#{clip_id})"><text x="0" y="{y}" font-family="{FONT_FAMILY}" '
        f'font-size="{FONT_SIZE}" xml:space="preserve" fill="{FILL_COLOR}">{safe_text}</text></g>'
    )
    cursor_fade_start = begin_time + ROW_REVEAL_DURATION
    cursor = (
        f'<rect y="{y - FONT_SIZE + 1}" width="{CHAR_WIDTH * 0.8}" height="{FONT_SIZE}" fill="{FILL_COLOR}">'
        f'<animate attributeName="x" from="0" to="{full_width}" dur="{ROW_REVEAL_DURATION}s" '
        f'begin="{begin_time}s" fill="freeze" calcMode="linear"/>'
        f'<animate attributeName="opacity" from="1" to="0" dur="0.2s" '
        f'begin="{cursor_fade_start}s" fill="freeze"/></rect>'
    )
    return clip_def + text_el + cursor


def build_ascii_svg(rows: list[str]) -> str:
    row_count = len(rows)
    col_count = max((len(r) for r in rows), default=0)
    width = round(col_count * CHAR_WIDTH) + 4
    height = round(row_count * LINE_HEIGHT) + 4

    body = "".join(
        build_row_markup(text, i, round(0.15 + i * ROW_STAGGER_STEP, 3))
        for i, text in enumerate(rows)
    )
    return svg_document(width, height, body, background=BACKGROUND_COLOR)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert a background-stripped photo (named 'source_photo.*' "
        "in the repo root) directly into an animated ASCII SVG."
    )
    parser.add_argument("--columns", type=int, default=config.ASCII_COLUMNS,
                         help="Number of ASCII character columns (default set in config.py).")
    parser.add_argument("--output", default=str(REPO_ROOT / config.ASCII_OUTPUT),
                         help="Output path (default set in config.py, written to repo root).")
    args = parser.parse_args()

    source = find_source_photo(REPO_ROOT)
    rows = image_to_ascii_rows(source, args.columns)
    write_text_file(args.output, build_ascii_svg(rows))
    print(f"Found {source.name} -> wrote {len(rows)} rows -> {args.output}")


if __name__ == "__main__":
    main()
