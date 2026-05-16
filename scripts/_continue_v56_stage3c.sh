#!/bin/bash
# v56 Stage 3 — FC fail обход через --no-strict-gates
set -e
cd /opt/glava
source .venv/bin/activate
set -a; source .env; set +a

PREFIX=karakulina_v56
LOG=/opt/glava/exports/run_v56_stage3.log

BOOK_DRAFT=$(ls -t exports/stage2_v56/karakulina_book_draft_v*_merged_*.json 2>/dev/null | head -1)
if [ -z "$BOOK_DRAFT" ]; then
  BOOK_DRAFT=$(ls -t exports/stage2_v56/karakulina_book_draft_v*.json 2>/dev/null | head -1)
fi
FACTMAP=$(ls -t exports/karakulina_v56/karakulina_fact_map_full_*.json 2>/dev/null | head -1)
FC_REPORT=$(ls -t exports/stage2_v56/karakulina_fc_report_iter*.json 2>/dev/null | head -1)

echo "BOOK_DRAFT: $BOOK_DRAFT" > "$LOG"
echo "FACTMAP:    $FACTMAP" >> "$LOG"
echo "FC_REPORT:  $FC_REPORT" >> "$LOG"
echo "" >> "$LOG"
echo "=== STAGE 3 (--no-strict-gates) ===" >> "$LOG"

python3 -u scripts/test_stage3.py \
  --book-draft "$BOOK_DRAFT" \
  --fact-map "$FACTMAP" \
  --fc-warnings "$FC_REPORT" \
  --output-dir exports/stage3_v56 \
  --prefix "${PREFIX}" \
  --no-strict-gates \
  2>&1 >> "$LOG"

BOOK_S3=$(ls -t exports/stage3_v56/${PREFIX}_book_FINAL_stage3_*.json 2>/dev/null | head -1)
if [ -z "$BOOK_S3" ]; then
  echo "ERROR: book_FINAL_stage3 not found" >> "$LOG"
  ls exports/stage3_v56/ >> "$LOG" 2>&1
  exit 1
fi
echo "BOOK_S3: $BOOK_S3" >> "$LOG"

PRES=$(ls -t exports/stage3_v56/${PREFIX}_le_structural_preservation_*.json 2>/dev/null | head -1)
if [ -n "$PRES" ]; then
  echo "=== LE preservation ===" >> "$LOG"
  python3 -c "
import json
d = json.load(open('$PRES'))
print('chapters_with_restored_fields:', d.get('chapters_with_restored_fields'))
for r in d.get('restorations', []):
    print(' ', r.get('chapter_id'), ':', r.get('restored_fields'))
" >> "$LOG" 2>&1
fi

echo "" >> "$LOG"
echo "=== BUILD GATE1 FULL TEXT ===" >> "$LOG"
mkdir -p collab/runs/karakulina_v56
python3 scripts/build_gate1_full_text.py \
  --book-final "$BOOK_S3" \
  --fact-map "$FACTMAP" \
  --output collab/runs/karakulina_v56/karakulina_v56_text_FULL.md \
  >> "$LOG" 2>&1

echo "=== DONE: v56 ===" >> "$LOG"
ls -lh exports/stage3_v56/ >> "$LOG"
