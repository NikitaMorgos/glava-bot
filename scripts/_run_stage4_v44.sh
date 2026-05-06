#!/bin/bash
# v44 Stage 4: gate 2a -> 2b -> 2c
# LD v3.21, book v36, prefix karakulina_v44
set -e
cd /opt/glava

PR=/opt/glava/exports/stage3_v36/karakulina_proofreader_report_20260428_154932.json
FM=/opt/glava/exports/v36a/karakulina_fact_map_full_20260428_060949_v2.json
PORTRAIT=/opt/glava/collab/stabilization_runs/karakulina_full_latest_20260409/karakulina_full_latest_stage4_cover_portrait_20260409_190332.webp
LOG=/opt/glava/exports/run_stage4_v44.log
PREFIX=karakulina_v44

echo '' > "$LOG"
echo '=== v44 Stage 4: gate 2a (LD v3.21, book v36) ===' | tee -a "$LOG"
python3 scripts/test_stage4_karakulina.py \
  --proofreader-report "$PR" \
  --fact-map "$FM" \
  --acceptance-gate 2a \
  --approve-gate \
  --allow-mismatch \
  --allow-legacy-input \
  --prefix "$PREFIX" \
  2>&1 | tee -a "$LOG"

LAYOUT_2A=$(ls -t /opt/glava/exports/${PREFIX}_stage4_layout_iter1_*.json 2>/dev/null | head -1)
echo "Layout 2a: $LAYOUT_2A" | tee -a "$LOG"
if [ -z "$LAYOUT_2A" ]; then echo 'ERROR: layout 2a not found'; exit 1; fi

echo '=== v44 Stage 4: gate 2b ===' | tee -a "$LOG"
python3 scripts/test_stage4_karakulina.py \
  --proofreader-report "$PR" \
  --fact-map "$FM" \
  --acceptance-gate 2b \
  --approve-gate \
  --allow-mismatch \
  --allow-legacy-input \
  --existing-layout "$LAYOUT_2A" \
  --prefix "$PREFIX" \
  2>&1 | tee -a "$LOG"

LAYOUT_2B=$(ls -t /opt/glava/exports/${PREFIX}_reuse_layout_pages_*.json 2>/dev/null | head -1)
echo "Layout 2b: $LAYOUT_2B" | tee -a "$LOG"
if [ -z "$LAYOUT_2B" ]; then echo 'ERROR: layout 2b not found'; exit 1; fi

echo '=== v44 Stage 4: gate 2c ===' | tee -a "$LOG"
python3 scripts/test_stage4_karakulina.py \
  --proofreader-report "$PR" \
  --fact-map "$FM" \
  --acceptance-gate 2c \
  --allow-mismatch \
  --allow-legacy-input \
  --existing-layout "$LAYOUT_2B" \
  --existing-portrait "$PORTRAIT" \
  --prefix "$PREFIX" \
  --no-photos \
  2>&1 | tee -a "$LOG"

echo '=== DONE ===' | tee -a "$LOG"
