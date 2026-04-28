#!/bin/bash
cd /opt/glava
source .venv/bin/activate
python scripts/test_stage1_pipeline.py \
  --transcript /opt/glava/transcript_karakulina_only.txt \
  --character-name "Каракулина Валентина Ивановна" \
  --output-dir /opt/glava/exports \
  2>&1
