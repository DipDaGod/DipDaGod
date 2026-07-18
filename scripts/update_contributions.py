#!/usr/bin/env python3

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

scripts = [
    HERE / "yep" / "fetch_contributions.py",
    HERE / "yep" / "render_heatmap_svg.py",
]

for script in scripts:
    print(f"Running {script.relative_to(HERE)}...")
    result = subprocess.run([sys.executable, str(script)])
    if result.returncode != 0:
        sys.exit(result.returncode)

print("Done!")
