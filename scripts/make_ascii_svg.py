from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image

from utils import escape_svg_text, stagger_delays, svg_document, write_text_file

# Density ramp: bright pixels -> sparse/blank characters, dark pixels -> dense
# characters. The leading space is deliberate: it makes the (white) background
# disappear instead of printing as visual noise around the subject.
RAMP = " .`:-=+*cs#%@"

# Characters are taller than they are wide, so we under-sample columns
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


def image_to_ascii_rows(image_path: Path, columns: int) -> list[str]:
    """Downsample the prepped grayscale image to a `columns`-wide character
    grid and map brightness to characters from RAMP.
    """
    img = Image.open(image_path).convert("L")
    width, height = img.size

    rows = max(1, round((height / width) * columns * CHAR_ASPECT_CORRECTION))
    small = img.resize((columns, rows), Image.LANCZOS)
    pixels = np.array(small)

    ramp_indices = (pixels.astype(np.float32) / 255.0 * (len(RAMP) - 1)).astype(int)
    # Bright pixel -> high index -> we want the *sparse* end of the ramp,
    # so invert: dark pixel should pick dense glyphs.
    ramp_indices = (len(RAMP) - 1) - ramp_indices

    lines = []
    for row in ramp_indices:
        lines.append("".join(RAMP[i] for i in row))
    return lines


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

    # Cursor: a small block that tracks the same width animate, then fades
    # out once this row's reveal is done (fill="freeze" holds opacity at 0).
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

    body_parts = []
    for i, (row_text, begin_time) in enumerate(zip(rows, begin_times)):
        body_parts.append(build_row_markup(row_text, i, begin_time))

    body = "".join(body_parts)
    return svg_document(width, height, body, background=BACKGROUND_COLOR)


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert a prepped photo into an animated ASCII SVG.")
    parser.add_argument(
        "--input", default="data/portrait-prepped.png", help="Path to the prepped grayscale image."
    )
    parser.add_argument("--output", default="avi-ascii.svg", help="Path to write the ASCII SVG.")
    parser.add_argument(
        "--columns", type=int, default=100, help="Number of ASCII character columns."
    )
    args = parser.parse_args()

    rows = image_to_ascii_rows(Path(args.input), args.columns)
    svg = build_ascii_svg(rows)
    write_text_file(args.output, svg)
    print(f"Wrote {len(rows)} rows -> {args.output}")


if __name__ == "__main__":
    main()