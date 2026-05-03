#!/bin/bash
# v41 Stage 4 verification run for tasks 024+025
# Uses existing v40 proofreader checkpoint + updated pdf_renderer.py

set -e
cd /opt/glava

echo "=== v41 Stage 4 gate2a ===" | tee /opt/glava/exports/run_stage4_v41_gate2a_log.txt
python3 scripts/test_stage4_karakulina.py \
  --acceptance-gate 2a \
  --allow-mismatch \
  >> /opt/glava/exports/run_stage4_v41_gate2a_log.txt 2>&1
echo "Gate 2a done, exit $?" | tee -a /opt/glava/exports/run_stage4_v41_gate2a_log.txt

LAYOUT=$(ls -t /opt/glava/exports/karakulina_iter1_layout_pages_*.json 2>/dev/null | head -1)
echo "Layout for gate2b/2c: $LAYOUT" | tee -a /opt/glava/exports/run_stage4_v41_gate2a_log.txt

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
