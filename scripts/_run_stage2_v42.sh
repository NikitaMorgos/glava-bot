#!/bin/bash
# v42 Stage 2 run via test_stage2_pipeline.py
# Tests task 027: enforce_bio_data_completeness

set -e
cd /opt/glava

echo "=== v42 Stage 2 (test_stage2_pipeline.py) ===" | tee /opt/glava/exports/run_stage2_v42.log

python3 scripts/test_stage2_pipeline.py \
  --fact-map /opt/glava/exports/karakulina_fact_map_v42_input.json \
  --transcript /opt/glava/exports/transcripts/karakulina_valentina_interview_assemblyai.txt \
  --max-fc-iterations 1 \
  --allow-fc-fail \
  >> /opt/glava/exports/run_stage2_v42.log 2>&1

echo "=== DONE ===" | tee -a /opt/glava/exports/run_stage2_v42.log
