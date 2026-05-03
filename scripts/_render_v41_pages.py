#!/usr/bin/env python3
"""Render specific pages of v41 gate2c PDF to PNG for visual verification."""
import subprocess
import os

PDF = "/opt/glava/exports/karakulina_stage4_gate_2c_20260503_194138.pdf"
OUT_DIR = "/opt/glava/exports/v41_pages"
os.makedirs(OUT_DIR, exist_ok=True)

pages_to_render = [3, 4, 5, 10, 11, 12, 13, 14, 15, 17, 18, 19, 20]

for pg in pages_to_render:
    prefix = f"{OUT_DIR}/page"
    result = subprocess.run([
        "pdftocairo", "-png", "-f", str(pg), "-l", str(pg), "-r", "120",
        PDF, prefix
    ], capture_output=True, text=True)
    # pdftocairo names files: prefix-NN.png (zero-padded)
    import glob
    files = glob.glob(f"{prefix}-*.png")
    # Find the one with our page number
    expected = f"{prefix}-{pg:02d}.png"
    if os.path.exists(expected):
        sz = os.path.getsize(expected)
        dest = f"{OUT_DIR}/page-{pg:02d}.png"
        os.rename(expected, dest)
        print(f"[OK] page {pg}: {dest} ({sz} bytes)")
    else:
        print(f"[ERR] page {pg}: returncode={result.returncode} stderr={result.stderr[:100]}")
        # Try to find any new file
        for f in files:
            print(f"  found: {f}")

print("Done.")
