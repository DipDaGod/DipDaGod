"""
utils.py
--------
Shared helpers used by every pipeline (portrait, info card, contributions).

Nothing pipeline-specific lives here (no ASCII ramps, no color palettes,
no GitHub scraping logic) — only generic SVG/file/animation plumbing that
would otherwise be duplicated across scripts.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Text safety
# ---------------------------------------------------------------------------

def escape_svg_text(text: str) -> str:
    """Escape characters that would break XML/SVG if placed inside a tag body
    or attribute (e.g. names, stats, ASCII glyphs like '&', '<', '>')."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


# ---------------------------------------------------------------------------
# SVG document assembly
# ---------------------------------------------------------------------------

def svg_document(
    width: int,
    height: int,
    body: str,
    *,
    extra_defs: str = "",
    background: str | None = None,
) -> str:
    """Wrap inner SVG markup in a complete, standalone <svg> document.

    Args:
        width: viewBox / canvas width in px.
        height: viewBox / canvas height in px.
        body: inner SVG markup (shapes, text, animations).
        extra_defs: optional <defs>...</defs> content (gradients, clip paths).
        background: optional fill color for a full-canvas background rect.
                    Left as None when the caller wants a transparent SVG.
    """
    defs_block = f"<defs>{extra_defs}</defs>" if extra_defs else ""
    bg_rect = (
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="{background}"/>'
        if background
        else ""
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" width="{width}" height="{height}">'
        f"{defs_block}{bg_rect}{body}"
        f"</svg>"
    )


# ---------------------------------------------------------------------------
# Animation timing
# ---------------------------------------------------------------------------

def stagger_delays(count: int, start: float = 0.0, step: float = 0.08) -> list[float]:
    """Return `count` sequential animation begin-times (in seconds).

    Used to make rows/lines/squares reveal one after another instead of all
    at once, e.g. for the ASCII typing effect, info-card line fade-ins, and
    the heatmap's diagonal reveal.
    """
    return [round(start + i * step, 3) for i in range(count)]


# ---------------------------------------------------------------------------
# File I/O (cross-platform via pathlib)
# ---------------------------------------------------------------------------

def write_text_file(path: str | Path, content: str) -> None:
    """Write text to `path`, creating parent directories if needed."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def write_json(path: str | Path, data: Any) -> None:
    """Write `data` as pretty-printed JSON to `path`, creating dirs as needed."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def read_json(path: str | Path) -> Any:
    """Read and parse a JSON file."""
    return json.loads(Path(path).read_text(encoding="utf-8"))