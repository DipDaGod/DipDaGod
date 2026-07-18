"""Shared SVG helpers for the three generator scripts (make_info_card.py,
make_ascii_svg.py, update_contributions.py). Anything copy-pasted across
more than one of them lives here instead.
"""

from __future__ import annotations

from pathlib import Path

MONO_FONT_STACK = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
DOT_COLORS = ["#ff5f56", "#ffbd2e", "#27c93f"]  # macOS-style traffic-light buttons


def escape_svg_text(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def write_text_file(path: str | Path, content: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def svg_document(width: int, height: int, body: str, *, extra_defs: str = "",
                  background: str | None = None) -> str:
    """Minimal <svg> wrapper: optional defs + optional flat background + body."""
    defs_block = f"<defs>{extra_defs}</defs>" if extra_defs else ""
    bg_rect = f'<rect width="{width}" height="{height}" fill="{background}"/>' if background else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}">{defs_block}{bg_rect}{body}</svg>'
    )


def terminal_card_frame(width: float, height: float, *, bg_top: str, bg_bottom: str,
                         frame_color: str, gradient_id: str = "cardBg",
                         frame_opacity: float = 1.0) -> str:
    """Rounded gradient background + border shared by every 'terminal card' SVG."""
    opacity_attr = f' stroke-opacity="{frame_opacity}"' if frame_opacity != 1.0 else ""
    return (
        f'<defs><linearGradient id="{gradient_id}" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{bg_top}"/><stop offset="1" stop-color="{bg_bottom}"/>'
        f"</linearGradient></defs>"
        f'<rect width="{width}" height="{height}" rx="12" fill="url(#{gradient_id})"/>'
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="12" '
        f'fill="none" stroke="{frame_color}"{opacity_attr}/>'
    )


def terminal_titlebar(width: float, titlebar_h: float, padding: float, title_text: str, *,
                       muted_color: str, frame_color: str, dot_colors=DOT_COLORS,
                       line_opacity: float = 1.0) -> str:
    """Separator line + traffic-light dots + centered title, used by every
    'terminal card' SVG's header bar.
    """
    opacity_attr = f' stroke-opacity="{line_opacity}"' if line_opacity != 1.0 else ""
    line = f'<line x1="0" y1="{titlebar_h}" x2="{width}" y2="{titlebar_h}" stroke="{frame_color}"{opacity_attr}/>'
    dots = "".join(
        f'<circle cx="{padding + i * 16}" cy="{titlebar_h / 2}" r="5" fill="{c}"/>'
        for i, c in enumerate(dot_colors)
    )
    label = (
        f'<text x="{width / 2}" y="{titlebar_h / 2 + 4}" fill="{muted_color}" '
        f'font-size="12" text-anchor="middle">{title_text}</text>'
    )
    return line + dots + label
