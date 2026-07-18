#!/usr/bin/env python3
"""
launch.py -- one-shot setup + generate-everything script.

Run once after (or even before) filling in config.py:

    python scripts/launch.py

It will:
  1. Check scripts/config.py for placeholder values you haven't filled in
     yet, and prompt you before continuing if it finds any.
  2. Run, in order: make_info_card.py -> make_ascii_svg.py ->
     update_contributions.py, printing a status box for each step so you
     can see what happened without digging through raw terminal output.

Each step is independent -- if one fails (e.g. no source_photo yet, or no
network for the GitHub fetch) the rest still run, and you get a summary
box at the end showing what succeeded.
"""

from __future__ import annotations

import os
import re
import shutil
import sys
import textwrap
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import config  # noqa: E402

# Enable ANSI escape handling on legacy Windows terminals.
if os.name == "nt":
    os.system("")

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
BLUE = "\033[34m"

WIDTH = max(min(shutil.get_terminal_size((78, 20)).columns, 78), 50)
ANSI_RE = re.compile(r"\033\[[0-9;]*m")
PLACEHOLDER_RE = re.compile(r"<[A-Z0-9_]+>")


def _visible_len(s: str) -> int:
    return len(ANSI_RE.sub("", s))


def box(lines: list[str], *, title: str = "", color: str = CYAN) -> None:
    """Print a bordered box. `lines` may already contain ANSI color codes;
    width is computed against their visible (un-colored) length.
    """
    inner_w = WIDTH - 4
    wrapped: list[str] = []
    for line in lines:
        if _visible_len(line) <= inner_w or ANSI_RE.search(line):
            wrapped.append(line)
        else:
            wrapped.extend(textwrap.wrap(line, inner_w) or [""])

    print(f"{color}┌{'─' * (WIDTH - 2)}┐{RESET}")
    if title:
        pad = max(inner_w - len(title) + 1, 0)
        print(f"{color}│ {RESET}{BOLD}{title}{RESET}{' ' * pad}{color}│{RESET}")
        print(f"{color}├{'─' * (WIDTH - 2)}┤{RESET}")
    for line in wrapped:
        pad = max(inner_w - _visible_len(line), 0)
        print(f"{color}│{RESET} {line}{' ' * pad} {color}│{RESET}")
    print(f"{color}└{'─' * (WIDTH - 2)}┘{RESET}")


def check_config_placeholders() -> list[str]:
    """Scan config.py's own source for any leftover <PLACEHOLDER> tokens."""
    source = (HERE / "config.py").read_text(encoding="utf-8")
    return sorted(set(PLACEHOLDER_RE.findall(source)))


def prompt_continue(placeholders: list[str]) -> bool:
    lines = [f"{YELLOW}\u26a0{RESET}  config.py still has unfilled placeholders:", ""]
    lines += [f"   {YELLOW}\u2022{RESET} {p}" for p in placeholders]
    lines += ["", "Open scripts/config.py and fill these in for accurate cards."]
    box(lines, title="CONFIG CHECK", color=YELLOW)
    try:
        answer = input(f"\n{BOLD}Continue anyway with placeholder text? [y/N]: {RESET}").strip().lower()
    except EOFError:
        answer = "n"
    return answer in ("y", "yes")


def run_step(step_num: int, total: int, label: str, func) -> bool:
    box([f"{CYAN}\u25b8{RESET} {label}"], title=f"STEP {step_num}/{total}", color=BLUE)
    try:
        func()
        box([f"{GREEN}\u2714 done{RESET}"], color=GREEN)
        return True
    except FileNotFoundError as e:
        box([f"{YELLOW}\u26a0 skipped{RESET} -- {e}"], color=YELLOW)
        return False
    except Exception as e:  # noqa: BLE001 - deliberately broad, this is a CLI runner
        box([f"{RED}\u2716 failed{RESET} -- {e}"], color=RED)
        print(f"{DIM}", end="")
        traceback.print_exc()
        print(f"{RESET}", end="")
        return False


def main() -> None:
    box(
        ["One-time setup check, then generates every profile-readme asset."],
        title=f"{config.GITHUB_USERNAME}'S PROFILE README -- LAUNCH",
        color=CYAN,
    )

    placeholders = check_config_placeholders()
    if placeholders:
        if not prompt_continue(placeholders):
            box(
                ["Stopped. Edit scripts/config.py, then re-run:", "  python scripts/launch.py"],
                color=YELLOW,
            )
            sys.exit(0)
    else:
        box([f"{GREEN}\u2714{RESET} config.py looks fully filled in, nothing to flag."], color=GREEN)

    print()

    # Imported here (after the config check) so the check runs even if one
    # of these modules has an import-time issue.
    import make_info_card
    import make_ascii_svg
    import update_contributions

    steps = [
        ("Build info card -> info-card.svg", make_info_card.main),
        ("Convert source_photo -> ascii-img.svg", make_ascii_svg.main),
        ("Fetch + render contributions -> contributions.svg", update_contributions.main),
    ]

    results = []
    for i, (label, func) in enumerate(steps, start=1):
        print()
        results.append((label, run_step(i, len(steps), label, func)))

    print()
    summary = [
        (f"{GREEN}\u2714{RESET} " if ok else f"{YELLOW}\u2013{RESET} ") + label
        for label, ok in results
    ]
    box(summary, title="SUMMARY", color=CYAN)


if __name__ == "__main__":
    main()
