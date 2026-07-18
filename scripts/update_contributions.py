#!/usr/bin/env python3

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

scripts = [
    HERE / "fetch_contributions.py",
    HERE / "render_heatmap_svg.py",
]

for script in scripts:
    print(f"Running {script.name}...")
    result = subprocess.run([sys.executable, str(script)])
    if result.returncode != 0:
        sys.exit(result.returncode)

print("Done!")