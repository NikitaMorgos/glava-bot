#!/usr/bin/env python3
"""
Task 025: Рендер страниц PDF в PNG для визуальной верификации subheading стиля.
"""
import subprocess
import os
import sys

PDF_PATH = "/opt/glava/exports/karakulina_v40_gate2c_20260501.pdf"
OUT_DIR = "/opt/glava/exports/v40_png"
os.makedirs(OUT_DIR, exist_ok=True)

# Рендерим страницы 11-14 (0-indexed: 10-13)
# где должны быть subheadings (ch_03, ch_04)
# pdftocairo -r 150 -png -f 11 -l 14 <pdf> <prefix>
result = subprocess.run(
    ["pdftocairo", "-r", "150", "-png", "-f", "11", "-l", "14", PDF_PATH, f"{OUT_DIR}/page"],
    capture_output=True, text=True
)
if result.returncode != 0:
    print("pdftocairo error:", result.stderr)
    # Try convert (ImageMagick)
    for page_num in range(11, 15):
        out_file = f"{OUT_DIR}/page_{page_num:02d}.png"
        r2 = subprocess.run(
            ["convert", "-density", "150", f"{PDF_PATH}[{page_num-1}]", out_file],
            capture_output=True, text=True
        )
        if r2.returncode == 0:
            print(f"Rendered page {page_num} -> {out_file}")
        else:
            print(f"convert page {page_num} error:", r2.stderr[:200])
else:
    print("pdftocairo OK")
    files = sorted(os.listdir(OUT_DIR))
    for f in files:
        fpath = os.path.join(OUT_DIR, f)
        print(f"  {f}: {os.path.getsize(fpath):,} bytes")
