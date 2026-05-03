#!/bin/bash
set -e
cd /opt/glava

LAYOUT=$(ls -t /opt/glava/exports/karakulina_iter1_layout_pages_20260503_*.json 2>/dev/null | head -1)
echo "Layout: $LAYOUT"

echo "=== v41 Stage 4 gate2b ===" | tee /opt/glava/exports/run_stage4_v41_gate2b_log.txt
python3 scripts/test_stage4_karakulina.py \
  --acceptance-gate 2b \
  --allow-mismatch \
  --existing-layout "$LAYOUT" \
  >> /opt/glava/exports/run_stage4_v41_gate2b_log.txt 2>&1
echo "Gate 2b done, exit $?" | tee -a /opt/glava/exports/run_stage4_v41_gate2b_log.txt

echo "=== v41 Stage 4 gate2c ===" | tee /opt/glava/exports/run_stage4_v41_gate2c_log.txt
python3 scripts/test_stage4_karakulina.py \
  --acceptance-gate 2c \
  --allow-mismatch \
  --existing-layout "$LAYOUT" \
  >> /opt/glava/exports/run_stage4_v41_gate2c_log.txt 2>&1
echo "Gate 2c done, exit $?" | tee -a /opt/glava/exports/run_stage4_v41_gate2c_log.txt

echo "=== ALL DONE ===" | tee -a /opt/glava/exports/run_stage4_v41_gate2c_log.txt
