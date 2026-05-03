#!/bin/bash
PDF="/opt/glava/exports/karakulina_stage4_gate_2c_20260501_080607.pdf"
OUT="/opt/glava/exports/v40_png"
mkdir -p "$OUT"
# Pages 3-18 to see chapter_start pages and subheadings
pdftocairo -r 150 -png -f 3 -l 18 "$PDF" "$OUT/page"
echo "Exit: $?"
ls -la "$OUT/"
