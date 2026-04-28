#!/bin/bash
set -euo pipefail
source /opt/glava/venv/bin/activate
cd /opt/glava
python3 scripts/test_stage4_karakulina.py \
  --acceptance-gate 1 \
  --prefix karakulina_v30_gate1 \
  2>&1 | tee /tmp/gate1_v30.log
echo "GATE1_V30_DONE"
