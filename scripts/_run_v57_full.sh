#!/bin/bash
# v57 — полный прогон Каракулиной с Batch 1 защитами (tasks 039, 040, 042)
# Ветка: feat/batch1-script-defenses
# Baseline для diff: v56
# Промпты: GW v2.18, LE v3.1, FC v2.13, CA v1.2 (те же что v56)

set -e
cd /opt/glava

echo "=== v57: git pull feat/batch1-script-defenses ==="
git fetch origin
git checkout feat/batch1-script-defenses
git pull origin feat/batch1-script-defenses

echo "=== v57: STAGE 1 (split-extract + prev-fact-map + subject_age + topo normalize) ==="
V56_FM="collab/runs/karakulina_v56/karakulina_v56_fact_map_full_20260515_154819.json"

python scripts/test_stage1_karakulina_full.py \
  --transcript1 collab/transcripts/01_karakulina_original_assemblyai_20260326.txt \
  --transcript2 collab/transcripts/02_karakulina_nikita_tatyana_interview.txt \
  --split-extract \
  --prev-fact-map "$V56_FM" \
  --output-dir exports/karakulina_v57

echo "=== v57: STAGE 2 ==="
FM57=$(ls -t exports/karakulina_v57/karakulina_fact_map_*.json | grep -v enriched | grep -v TR1 | head -1)
echo "fact_map: $FM57"

python scripts/test_stage2_pipeline.py \
  --fact-map "$FM57" \
  --output-dir exports/stage2_v57 \
  --allow-fc-fail

echo "=== v57: STAGE 3 (bio_data integrity + topo normalize на book) ==="
# Предпочитаем book_FINAL если есть, иначе book_draft
BOOK_FINAL=$(ls -t exports/stage2_v57/karakulina_book_FINAL_*.json 2>/dev/null | head -1)
BOOK_DRAFT=$(ls -t exports/stage2_v57/karakulina_book_draft_*.json 2>/dev/null | head -1)

if [ -n "$BOOK_FINAL" ]; then
  BOOK_IN="$BOOK_FINAL"
  echo "Stage 3 input: book_FINAL (FC passed)"
else
  BOOK_IN="$BOOK_DRAFT"
  echo "Stage 3 input: book_draft (FC failed - using --no-strict-gates)"
fi

python scripts/test_stage3.py \
  --book-draft "$BOOK_IN" \
  --fact-map "$FM57" \
  --output-dir exports/stage3_v57 \
  --prefix karakulina \
  --no-strict-gates

echo "=== v57: Gate1 full text ==="
BOOK_FINAL_S3=$(ls -t exports/stage3_v57/karakulina_book_FINAL_stage3_*.json | head -1)
mkdir -p collab/runs/karakulina_v57

python scripts/build_gate1_full_text.py \
  --book-final "$BOOK_FINAL_S3" \
  --output collab/runs/karakulina_v57/karakulina_v57_text_FULL.md

echo "=== v57: DONE ==="
echo "book_FINAL_stage3: $BOOK_FINAL_S3"
ls -la exports/karakulina_v57/ exports/stage2_v57/ exports/stage3_v57/
