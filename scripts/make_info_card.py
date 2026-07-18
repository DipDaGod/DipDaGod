"""
make_info_card.py
------------------
Pipeline 2 (Info Card).

CONFIG (below) -> info-card.svg

A neofetch-style terminal panel: a host line, identity key/value rows, then
titled sections (key/value rows or bullet highlights) - NOT GitHub stats,
since the contribution heatmap already covers those. Everything shown comes
from CONFIG; add or remove a section there and the layout adjusts itself.

Each row fades in and rises slightly on a short stagger (SMIL animate +
animateTransform, both fill="freeze", no repeatCount) so the panel feels
like it's printing - then holds still.

Set STATIC=1 as an environment variable to emit the fully-revealed frame
with no animation, handy for a quick local preview.
"""

from __future__ import annotations

import os

from utils import escape_svg_text, write_text_file

# ---------------------------------------------------------------------------
# CONFIG - the only section you should need to edit.
# ---------------------------------------------------------------------------
CONFIG: dict = {
    "username": "DipDaGod",
    "host": "github",
    "command": "neofetch",

    # Displayed below the header
    "identity": [
        ("Name", "Dhairya Khetan"),
        ("Role", "Student Coder"),
        ("Education", "Class 11 • Computer Science"),
    ],

    "sections": [
        {
            "title": "Languages",
            "kv": {
                "HTML": "Advanced",
                "Python": "Intermediate",
                "CSS": "Beginner",
                "JavaScript": "Beginner",
            },
        },
        {
            "title": "Interests",
            "bullets": [
                "Web Development",
                "Football",
                "Fun Side Projects",
            ],
        },
        {
            "title": "Links",
            "kv": {
                "Showcase": "dipdagod.github.io/projects-showcase",
            },
        },
    ],
}

STATIC = bool(os.environ.get("STATIC"))

# ---------------------------------------------------------------------------
# Visual constants
# ---------------------------------------------------------------------------
FONT_STACK = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
MIN_WIDTH = 480
PADDING = 20
TITLE_BAR_HEIGHT = 30
KEY_X = PADDING
LINE_HEIGHT = 20.5

# Approximate glyph advance width (px) for bold 12.5px monospace text - used
# to compute how far right the value column needs to start so long keys
# (e.g. "Education", or a custom link label) never run into their values.
KEY_CHAR_WIDTH_ESTIMATE = 7.6
VALUE_CHAR_WIDTH_ESTIMATE = 7.2  # approx glyph width for regular (non-bold) 12.5px text
VALUE_COLUMN_GAP = 16

BG_TOP = "#111722"
BG_BOTTOM = "#0d1117"
FRAME_COLOR = "#30363d"
MUTED_COLOR = "#7d8590"
INK_COLOR = "#c9d1d9"
KEY_COLOR = "#ffa657"       # orange - identity/section keys
SECTION_COLOR = "#58a6ff"   # blue - section titles
GREEN_COLOR = "#3fb950"     # host name + bullet dots
ACCENT_COLOR = "#22d3ee"    # host machine name
DOT_COLORS = ["#ff5f56", "#ffbd2e", "#27c93f"]  # window-chrome buttons


def rise(inner: str, row_index: int) -> str:
    """Wrap `inner` so it fades in and rises slightly, staggered by
    `row_index`. Freezes once done - never loops. STATIC mode skips the
    animation entirely and just shows the settled state.
    """
    if STATIC:
        return f"<g>{inner}</g>"
    delay = 0.15 + row_index * 0.06
    return (
        f'<g opacity="0" transform="translate(0,5)">{inner}'
        f'<animate attributeName="opacity" from="0" to="1" begin="{delay:.2f}s" '
        f'dur="0.4s" fill="freeze"/>'
        f'<animateTransform attributeName="transform" type="translate" from="0 5" to="0 0" '
        f'begin="{delay:.2f}s" dur="0.4s" fill="freeze" calcMode="spline" '
        f'keySplines="0.2 0.8 0.2 1"/></g>'
    )


def compute_value_column_x(config: dict) -> float:
    """Find the x-position where value text can safely start, based on the
    longest key across identity rows and every section's kv rows.

    Using one fixed offset breaks as soon as a key is longer than expected
    (e.g. "Education" vs "Now", or a custom link label) - the value text
    would start underneath the key instead of after it. Computing this from
    the actual config content means it adapts automatically no matter what
    keys you put in CONFIG.
    """
    labels: list[str] = [key for key, _ in config.get("identity", [])]
    for section in config.get("sections", []):
        labels.extend(section.get("kv", {}).keys())

    longest_label_length = max((len(label) for label in labels), default=0)
    return KEY_X + longest_label_length * KEY_CHAR_WIDTH_ESTIMATE + VALUE_COLUMN_GAP


def compute_card_width(config: dict, value_x: float) -> float:
    """Find a card width wide enough that no value or bullet line runs past
    the right edge. Starts from MIN_WIDTH and grows only if the actual
    content (long values, long bullet text, a long title-bar command line)
    needs more room.
    """
    candidate_widths = [MIN_WIDTH]

    values = [value for _, value in config.get("identity", [])]
    for section in config.get("sections", []):
        values.extend(section.get("kv", {}).values())
    for value in values:
        candidate_widths.append(value_x + len(value) * VALUE_CHAR_WIDTH_ESTIMATE + PADDING) # type: ignore

    for section in config.get("sections", []):
        for bullet_text in section.get("bullets", []):
            candidate_widths.append(
                KEY_X + 14 + len(bullet_text) * VALUE_CHAR_WIDTH_ESTIMATE + PADDING # type: ignore
            )

    title_line = f'{config["username"]}@{config["host"]}: ~$ {config.get("command", "neofetch")}'
    candidate_widths.append(len(title_line) * 7.0 + PADDING * 4)  # type: ignore # centered, needs margin both sides

    return max(candidate_widths)


def build_rows_markup(config: dict, value_x: float, width: float) -> tuple[str, float]:
    """Turn CONFIG into the sequence of animated row groups. Returns the
    joined markup and the final y-coordinate (used to size the card).
    """
    parts: list[str] = []
    row_index = 0
    y = TITLE_BAR_HEIGHT + 30

    # Host line: "<username>@<host>" plus a rule.
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

    # Identity rows (key/value, no section header).
    for key, value in config.get("identity", []):
        safe_key, safe_value = escape_svg_text(key), escape_svg_text(value)
        inner = (
            f'<text x="{KEY_X}" y="{y:.1f}" fill="{KEY_COLOR}" font-size="12.5" '
            f'font-weight="700">{safe_key}</text>'
            f'<text x="{value_x}" y="{y:.1f}" fill="{INK_COLOR}" font-size="12.5">{safe_value}</text>'
        )
        parts.append(rise(inner, row_index))
        row_index += 1
        y += LINE_HEIGHT

    # Sections: a title rule, then either kv rows or bullet rows.
    for section in config.get("sections", []):
        y += LINE_HEIGHT * 0.5  # gap before each section
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
            safe_key, safe_value = escape_svg_text(key), escape_svg_text(value)
            inner = (
                f'<text x="{KEY_X}" y="{y:.1f}" fill="{KEY_COLOR}" font-size="12.5" '
                f'font-weight="700">{safe_key}</text>'
                f'<text x="{value_x}" y="{y:.1f}" fill="{INK_COLOR}" font-size="12.5">{safe_value}</text>'
            )
            parts.append(rise(inner, row_index))
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

    dots = "".join(
        f'<circle cx="{PADDING + i * 16}" cy="{TITLE_BAR_HEIGHT / 2}" r="5" fill="{color}"/>'
        for i, color in enumerate(DOT_COLORS)
    )

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="{FONT_STACK}">',
        "<defs>"
        '<linearGradient id="cardBg" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{BG_TOP}"/>'
        f'<stop offset="1" stop-color="{BG_BOTTOM}"/>'
        "</linearGradient>"
        "</defs>",
        f'<rect width="{width}" height="{height}" rx="12" fill="url(#cardBg)"/>',
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="12" '
        f'fill="none" stroke="{FRAME_COLOR}"/>',
        f'<line x1="0" y1="{TITLE_BAR_HEIGHT}" x2="{width}" y2="{TITLE_BAR_HEIGHT}" '
        f'stroke="{FRAME_COLOR}"/>',
        dots,
        f'<text x="{width / 2}" y="{TITLE_BAR_HEIGHT / 2 + 4}" fill="{MUTED_COLOR}" '
        f'font-size="12" text-anchor="middle">{username}@{host}: ~$ {command}</text>',
        rows_markup,
        "</svg>",
    ]
    return "".join(parts)


def main() -> None:
    svg = build_info_card_svg(CONFIG)
    write_text_file("info-card.svg", svg)
    print(f"Wrote info-card.svg ({len(svg)} bytes)")


if __name__ == "__main__":
    main()