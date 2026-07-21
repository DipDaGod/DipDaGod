#!/usr/bin/env python3

from __future__ import annotations

import datetime
import os
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent

USERNAME = os.environ.get("GH_PROFILE_USER", "DipDaGod")
URL = f"https://github.com/users/{USERNAME}/contributions"

SVG_OUT_PATH = REPO_ROOT / "contributions.svg"

# ---------------------------------------------------------------------------
# Step 1: fetch the contribution calendar
# ---------------------------------------------------------------------------


def fetch_days() -> list[dict]:
    resp = requests.get(URL, headers={"User-Agent": "profile-readme-bot/1.0"}, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    cells = soup.select("td.ContributionCalendar-day")
    if not cells:
        print("no calendar cells found -- github markup may have changed", file=sys.stderr)
        sys.exit(1)

    days = []
    for td in cells:
        date = td.get("data-date")
        if not date:
            continue
        tooltip_el = soup.find("tool-tip", attrs={"for": td.get("id")}) if td.get("id") else None
        text = tooltip_el.get_text(strip=True) if tooltip_el else ""
        if re.search(r"no contributions", text, re.I):
            count = 0
        else:
            m = re.match(r"(\d+)", text)
            count = int(m.group(1)) if m else 0
        days.append({"date": date, "count": count})

    days.sort(key=lambda d: d["date"])
    return days


def compute_current_streak(days: list[dict]):
    idx = len(days) - 1
    if days[idx]["count"] == 0:
        idx -= 1  # today isn't over yet -- don't break the streak on it
    streak = 0
    end_idx = idx
    while idx >= 0 and days[idx]["count"] > 0:
        streak += 1
        idx -= 1
    if streak == 0:
        return 0, None, None
    return streak, days[idx + 1]["date"], days[end_idx]["date"]


def compute_longest_streak(days: list[dict]):
    longest = run = 0
    longest_start = longest_end = None
    run_start_idx = None
    for i, d in enumerate(days):
        if d["count"] > 0:
            if run == 0:
                run_start_idx = i
            run += 1
            if run > longest:
                longest = run
                longest_start = days[run_start_idx]["date"]
                longest_end = days[i]["date"]
        else:
            run = 0
    return longest, longest_start, longest_end


def build_data(days: list[dict]) -> dict:
    total = sum(d["count"] for d in days)
    active_days = sum(1 for d in days if d["count"] > 0)
    best = max(days, key=lambda d: d["count"])
    cur_len, cur_start, cur_end = compute_current_streak(days)
    long_len, long_start, long_end = compute_longest_streak(days)

    monthly = {}
    for d in days:
        monthly[d["date"][:7]] = monthly.get(d["date"][:7], 0) + d["count"]

    return {
        "username": USERNAME,
        "generated_at": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "range": {"start": days[0]["date"], "end": days[-1]["date"]},
        "total_contributions": total,
        "active_days": active_days,
        "avg_per_active_day": round(total / active_days, 1) if active_days else 0,
        "current_streak": {"length": cur_len, "start": cur_start, "end": cur_end},
        "longest_streak": {"length": long_len, "start": long_start, "end": long_end},
        "best_day": {"date": best["date"], "count": best["count"]},
        "monthly": [{"month": k, "total": v} for k, v in sorted(monthly.items())],
        "days": days,
    }


# ---------------------------------------------------------------------------
# Step 2: render the heatmap SVG
# ---------------------------------------------------------------------------

MONO_FONT_STACK = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
DOT_COLORS = ["#ff5f56", "#ffbd2e", "#27c93f"]  # macOS-style traffic-light buttons


def escape_svg_text(text: str) -> str:
    """Escape characters that would break XML/SVG if placed inside a tag body."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
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


PALETTE = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353", "#69f0a0"]  # empty -> brightest

CELL = 12
GAP = 3
STEP = CELL + GAP
PAD = 22
LEFT_LABEL_W = 30
TOP_LABEL_H = 20
TITLEBAR_H = 30

BG_TOP = "#0d1420"
BG_BOTTOM = "#0a0e14"
FRAME_COLOR = "#1f6feb"
MUTED_COLOR = "#7d8590"
ACCENT_COLOR = "#22d3ee"
GREEN_COLOR = "#39d353"
GOLD_COLOR = "#f2cc60"

COL_T = 0.018   # per-column delay (left -> right sweep)
ROW_T = 0.045   # per-row delay (top -> bottom cascade)
CELL_DUR = 0.42


def level_for(count: int) -> int:
    for cap, lvl in ((0, 0), (5, 1), (15, 2), (30, 3), (50, 4)):
        if count <= cap:
            return lvl
    return 5


def build_grid(days: list[dict]):
    first = datetime.date.fromisoformat(days[0]["date"])
    grid, col = [], [None] * ((first.weekday() + 1) % 7)  # sunday=0
    for d in days:
        weekday = (datetime.date.fromisoformat(d["date"]).weekday() + 1) % 7
        col += [None] * (weekday - len(col))
        col.append((d["date"], d["count"], level_for(d["count"])))
        if len(col) == 7:
            grid.append(col)
            col = []
    if col:
        grid.append(col + [None] * (7 - len(col)))
    return grid


def render(data: dict) -> str:
    days = data["days"]
    grid = build_grid(days)
    art_w, art_h = len(grid) * STEP, 7 * STEP

    month_labels, seen_months = [], set()
    for ci, column in enumerate(grid):
        for cell in column:
            if cell is None:
                continue
            date = datetime.date.fromisoformat(cell[0])
            key = (date.year, date.month)
            if key not in seen_months and date.day <= 7:
                seen_months.add(key)
                month_labels.append((ci, date.strftime("%b")))
            break

    canvas_w = PAD + LEFT_LABEL_W + art_w + PAD
    stats_h = 40  # just one line of text now, instead of legend + two stat rows
    canvas_h = TITLEBAR_H + TOP_LABEL_H + art_h + stats_h + PAD
    grid_top = TITLEBAR_H + TOP_LABEL_H
    grid_left = PAD + LEFT_LABEL_W

    css = (
        f"@keyframes cell{{0%{{opacity:0;transform:translateY(-6px)}}"
        f"100%{{opacity:1;transform:translateY(0)}}}}"
        f".c{{opacity:0;animation:cell {CELL_DUR:.2f}s cubic-bezier(.2,.8,.2,1) both}}"
    )

    chrome = terminal_card_frame(canvas_w, canvas_h, bg_top=BG_TOP, bg_bottom=BG_BOTTOM,
                                  frame_color=FRAME_COLOR, gradient_id="hbg", frame_opacity=0.55)
    title = escape_svg_text(f"{USERNAME}@github: ~/contributions --graph")
    chrome += terminal_titlebar(canvas_w, TITLEBAR_H, PAD, title, muted_color=MUTED_COLOR,
                                 frame_color=FRAME_COLOR, line_opacity=0.35)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_w}" height="{canvas_h}" '
        f'viewBox="0 0 {canvas_w} {canvas_h}" font-family="{MONO_FONT_STACK}">',
        f"<style>{css}</style>",
        chrome,
    ]

    for ci, label in month_labels:
        parts.append(f'<text x="{grid_left + ci * STEP}" y="{TITLEBAR_H + 14}" '
                      f'fill="{MUTED_COLOR}" font-size="10">{label}</text>')
    for wi, wname in [(1, "Mon"), (3, "Wed"), (5, "Fri")]:
        parts.append(f'<text x="{PAD}" y="{grid_top + wi * STEP + CELL * 0.78:.1f}" '
                      f'fill="{MUTED_COLOR}" font-size="9">{wname}</text>')

    for ci, column in enumerate(grid):
        gx = grid_left + ci * STEP
        for ri, cell in enumerate(column):
            if cell is None:
                continue
            date_s, count, lvl = cell
            delay = ci * COL_T + ri * ROW_T
            plural = "s" if count != 1 else ""
            parts.append(
                f'<rect class="c" x="{gx}" y="{grid_top + ri * STEP}" width="{CELL}" height="{CELL}" rx="2.5" '
                f'fill="{PALETTE[lvl]}" style="animation-delay:{delay:.3f}s">'
                f'<title>{date_s}: {count} contribution{plural}</title></rect>'
            )

    # Just the total, directly under the grid - no legend, no streaks, no
    # best day, no date range.
    total = data["total_contributions"]
    ly = grid_top + art_h + 30
    parts.append(f'<text x="{PAD}" y="{ly}" font-size="13" fill="{GREEN_COLOR}">'
                 f'<tspan font-weight="700">{total:,}</tspan>'
                 f'<tspan fill="{MUTED_COLOR}"> contributions in the last year</tspan></text>')

    parts.append("</svg>")
    return "".join(parts)


# ---------------------------------------------------------------------------
# Entrypoint: fetch -> save json -> render -> save svg, all in one run
# ---------------------------------------------------------------------------


def main() -> None:
    print(f"Fetching contribution calendar for {USERNAME}...")
    data = build_data(fetch_days())
    print(f"{data['total_contributions']} contributions, "
          f"current streak {data['current_streak']['length']}, "
          f"longest streak {data['longest_streak']['length']}")

    svg = render(data)
    SVG_OUT_PATH.write_text(svg)
    print(f"wrote {SVG_OUT_PATH} ({len(svg)} bytes)")
    print("Done!")


if __name__ == "__main__":
    main()