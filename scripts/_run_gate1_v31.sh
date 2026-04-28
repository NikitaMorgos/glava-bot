#!/bin/bash
set -euo pipefail
source /opt/glava/venv/bin/activate
cd /opt/glava
python3 scripts/test_stage4_karakulina.py \
  --acceptance-gate 1 \
  --prefix karakulina_v31_gate1 \
  2>&1 | tee /tmp/gate1_v31.log
echo "GATE1_V31_DONE"
