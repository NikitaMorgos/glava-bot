#!/bin/bash
# v43 Stage 2 — штатный режим: FC с 3 итерациями
set -e
cd /opt/glava

LOG=/opt/glava/exports/run_stage2_v43.log
echo "=== v43 Stage 2 (test_stage2_pipeline.py, fc-iter=3) ===" | tee "$LOG"

python3 scripts/test_stage2_pipeline.py \
  --fact-map /opt/glava/exports/karakulina_fact_map_v42_input.json \
  --transcript /opt/glava/exports/transcripts/karakulina_valentina_interview_assemblyai.txt \
  --max-fc-iterations 3 \
  >> "$LOG" 2>&1

echo "=== DONE ===" | tee -a "$LOG"
