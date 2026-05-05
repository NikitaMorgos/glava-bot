#!/bin/bash
# v43 Stage 4: gate 2a → 2b → 2c (text-only PDF)
set -e
cd /opt/glava

TS=20260505_140502
BOOK=/opt/glava/exports/karakulina_book_FINAL_stage3_${TS}.json
PR=/opt/glava/exports/karakulina_proofreader_report_${TS}.json
FM=/opt/glava/exports/karakulina_fact_map_v42_input.json
LOG=/opt/glava/exports/run_stage4_v43.log

echo "=== v43 Stage 4: gate 2a ===" | tee "$LOG"
python3 scripts/test_stage4_karakulina.py \
  --proofreader-report "$PR" \
  --fact-map "$FM" \
  --acceptance-gate 2a \
  --approve-gate \
  --text-only \
  --allow-mismatch \
  --allow-legacy-input \
  >> "$LOG" 2>&1

LAYOUT_2A=/opt/glava/exports/karakulina_stage4_layout_iter1_20260505_141302.json

echo "=== v43 Stage 4: gate 2b ===" | tee -a "$LOG"
python3 scripts/test_stage4_karakulina.py \
  --proofreader-report "$PR" \
  --fact-map "$FM" \
  --acceptance-gate 2b \
  --approve-gate \
  --text-only \
  --allow-mismatch \
  --allow-legacy-input \
  --existing-layout "$LAYOUT_2A" \
  >> "$LOG" 2>&1

# Find the layout output from gate 2b (iter2)
LAYOUT_2B=$(ls /opt/glava/exports/karakulina_stage4_layout_iter2_*.json 2>/dev/null | sort -r | head -1)
echo "Layout 2b: $LAYOUT_2B" | tee -a "$LOG"

echo "=== v43 Stage 4: gate 2c ===" | tee -a "$LOG"
python3 scripts/test_stage4_karakulina.py \
  --proofreader-report "$PR" \
  --fact-map "$FM" \
  --acceptance-gate 2c \
  --text-only \
  --allow-mismatch \
  --allow-legacy-input \
  --existing-layout "$LAYOUT_2B" \
  >> "$LOG" 2>&1

echo "=== DONE ===" | tee -a "$LOG"
