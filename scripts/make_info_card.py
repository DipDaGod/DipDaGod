from __future__ import annotations

import os
from pathlib import Path

import config
from lib.svg_common import MONO_FONT_STACK, escape_svg_text, terminal_card_frame, terminal_titlebar, write_text_file

CONFIG: dict = config.INFO_CARD  # edit scripts/config.py, not this file

STATIC = bool(os.environ.get("STATIC"))

MIN_WIDTH = 480
PADDING = 20
TITLE_BAR_HEIGHT = 30
KEY_X = PADDING
LINE_HEIGHT = 20.5

# Approximate glyph advance widths (px) for 12.5px monospace text, used to
# compute where the value column starts and how wide the card needs to be
# so long keys/values/bullets never run into each other or off the edge.
KEY_CHAR_WIDTH_ESTIMATE = 7.6
VALUE_CHAR_WIDTH_ESTIMATE = 7.2
VALUE_COLUMN_GAP = 16

BG_TOP = "#111722"
BG_BOTTOM = "#0d1117"
FRAME_COLOR = "#30363d"
MUTED_COLOR = "#7d8590"
INK_COLOR = "#c9d1d9"
KEY_COLOR = "#ffa657"       # identity/section keys
SECTION_COLOR = "#58a6ff"   # section titles
GREEN_COLOR = "#3fb950"     # host name + bullet dots
ACCENT_COLOR = "#22d3ee"    # host machine name


def rise(inner: str, row_index: int) -> str:
    """Fade-in + rise-in animation staggered by row_index, freezing once
    done. STATIC=1 env var skips the animation and shows the settled state.
    """
    if STATIC:
        return f"<g>{inner}</g>"
    delay = 0.15 + row_index * 0.06
    return (
        f'<g opacity="0" transform="translate(0,5)">{inner}'
        f'<animate attributeName="opacity" from="0" to="1" begin="{delay:.2f}s" dur="0.4s" fill="freeze"/>'
        f'<animateTransform attributeName="transform" type="translate" from="0 5" to="0 0" '
        f'begin="{delay:.2f}s" dur="0.4s" fill="freeze" calcMode="spline" keySplines="0.2 0.8 0.2 1"/></g>'
    )


def compute_value_column_x(config: dict) -> float:
    """Value column x-position, based on the longest key in use, so a long
    key (or custom link label) never runs into its value.
    """
    labels = [key for key, _ in config.get("identity", [])]
    for section in config.get("sections", []):
        labels.extend(section.get("kv", {}).keys())
    longest = max((len(label) for label in labels), default=0)
    return KEY_X + longest * KEY_CHAR_WIDTH_ESTIMATE + VALUE_COLUMN_GAP


def compute_card_width(config: dict, value_x: float) -> float:
    """Widest of MIN_WIDTH and whatever the actual content needs, so no
    value/bullet/title line runs past the right edge.
    """
    widths = [MIN_WIDTH]
    values = [v for _, v in config.get("identity", [])]
    for section in config.get("sections", []):
        values.extend(section.get("kv", {}).values())
    widths += [value_x + len(v) * VALUE_CHAR_WIDTH_ESTIMATE + PADDING for v in values]

    for section in config.get("sections", []):
        widths += [
            KEY_X + 14 + len(b) * VALUE_CHAR_WIDTH_ESTIMATE + PADDING
            for b in section.get("bullets", [])
        ]

    title_line = f'{config["username"]}@{config["host"]}: ~$ {config.get("command", "neofetch")}'
    widths.append(len(title_line) * 7.0 + PADDING * 4)  # centered, needs margin both sides
    return max(widths)


def build_rows_markup(config: dict, value_x: float, width: float) -> tuple[str, float]:
    """CONFIG -> animated row groups. Returns (markup, final y) so the
    card can be sized to fit.
    """
    parts: list[str] = []
    row_index = 0
    y = TITLE_BAR_HEIGHT + 30

    username = escape_svg_text(config["username"])
    host = escape_svg_text(config["host"])
    host_inner = (
        f'<text x="{KEY_X}" y="{y:.1f}" font-size="14" font-weight="700">'
        f'<tspan fill="{GREEN_COLOR}">{username}</tspan>'
        f'<tspan fill="{MUTED_COLOR}">@</tspan>'
        f'<tspan fill="{ACCENT_COLOR}">{host}</tspan></text>'
        f'<line x1="{KEY_X + 96}" y1="{y - 4:.1f}" x2="{width - PADDING}" y2="{y - 4:.1f}" '
        f'stroke="{FRAME_COLOR}" stroke-opacity="0.8"/>'
    )
    parts.append(rise(host_inner, row_index))
    row_index += 1
    y += LINE_HEIGHT

    def kv_row(key: str, value: str, idx: int, y: float) -> str:
        safe_key, safe_value = escape_svg_text(key), escape_svg_text(value)
        return rise(
            f'<text x="{KEY_X}" y="{y:.1f}" fill="{KEY_COLOR}" font-size="12.5" font-weight="700">{safe_key}</text>'
            f'<text x="{value_x}" y="{y:.1f}" fill="{INK_COLOR}" font-size="12.5">{safe_value}</text>',
            idx,
        )

    for key, value in config.get("identity", []):
        parts.append(kv_row(key, value, row_index, y))
        row_index += 1
        y += LINE_HEIGHT

    for section in config.get("sections", []):
        y += LINE_HEIGHT * 0.5
        title = escape_svg_text(section["title"])
        title_inner = (
            f'<text x="{KEY_X}" y="{y:.1f}" fill="{SECTION_COLOR}" font-size="12.5" '
            f'font-weight="700">&#8212; {title}</text>'
            f'<line x1="{KEY_X + 12 + len(section["title"]) * 8}" y1="{y - 4:.1f}" '
            f'x2="{width - PADDING}" y2="{y - 4:.1f}" stroke="{FRAME_COLOR}" stroke-opacity="0.8"/>'
        )
        parts.append(rise(title_inner, row_index))
        row_index += 1
        y += LINE_HEIGHT

        for key, value in section.get("kv", {}).items():
            parts.append(kv_row(key, value, row_index, y))
            row_index += 1
            y += LINE_HEIGHT

        for bullet_text in section.get("bullets", []):
            safe_text = escape_svg_text(bullet_text)
            inner = (
                f'<circle cx="{KEY_X + 3}" cy="{y - 4:.1f}" r="2.5" fill="{GREEN_COLOR}"/>'
                f'<text x="{KEY_X + 14}" y="{y:.1f}" fill="{INK_COLOR}" font-size="12.5">{safe_text}</text>'
            )
            parts.append(rise(inner, row_index))
            row_index += 1
            y += LINE_HEIGHT

    return "".join(parts), y


def build_info_card_svg(config: dict) -> str:
    value_x = compute_value_column_x(config)
    width = compute_card_width(config, value_x)
    rows_markup, content_bottom = build_rows_markup(config, value_x, width)
    height = round(content_bottom + PADDING)

    command = escape_svg_text(config.get("command", "neofetch"))
    username = escape_svg_text(config["username"])
    host = escape_svg_text(config["host"])
    title = f"{username}@{host}: ~$ {command}"

    chrome = terminal_card_frame(width, height, bg_top=BG_TOP, bg_bottom=BG_BOTTOM, frame_color=FRAME_COLOR)
    chrome += terminal_titlebar(width, TITLE_BAR_HEIGHT, PADDING, title,
                                 muted_color=MUTED_COLOR, frame_color=FRAME_COLOR)

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="{MONO_FONT_STACK}">'
        f"{chrome}{rows_markup}</svg>"
    )


def main() -> None:
    svg = build_info_card_svg(CONFIG)
    write_text_file(Path(__file__).resolve().parent.parent / "info-card.svg", svg)
    print(f"Wrote info-card.svg ({len(svg)} bytes)")


if __name__ == "__main__":
    main()
