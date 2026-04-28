#!/bin/bash
cd /opt/glava
export PYTHONUNBUFFERED=1
nohup .venv/bin/python -u scripts/test_stage4_karakulina.py \
  --photos-dir exports/karakulina_photos/ \
  --fact-map exports/test_fact_map_karakulina_v5.json \
  > /tmp/stage4_run6.log 2>&1 &
echo "PID: $!"
