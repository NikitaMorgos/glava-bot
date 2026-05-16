#!/bin/bash
# Продолжение v56 после FC fail — Stage 3 с --allow-fc-fail
set -e
cd /opt/glava
source .venv/bin/activate
set -a; source .env; set +a

PREFIX=karakulina_v56
LOG=/opt/glava/exports/run_v56_full.log

BOOK_S2=$(ls -t exports/stage2_v56/karakulina_v56_book_FINAL_stage2_*.json 2>/dev/null | head -1)
if [ -z "$BOOK_S2" ]; then
  BOOK_S2_RAW=$(ls -t exports/stage2_v56/karakulina_book_FINAL_*.json 2>/dev/null | head -1)
  TS_S2=$(basename "$BOOK_S2_RAW" | sed 's/karakulina_book_FINAL_//' | sed 's/.json//')
  BOOK_S2="exports/stage2_v56/${PREFIX}_book_FINAL_stage2_${TS_S2}.json"
  cp "$BOOK_S2_RAW" "$BOOK_S2"
fi

FACTMAP=$(ls -t exports/karakulina_v56/karakulina_fact_map_full_*.json 2>/dev/null | head -1)
FC_REPORT=$(ls -t exports/stage2_v56/karakulina_fc_report_iter*.json 2>/dev/null | head -1)

echo "" | tee -a "$LOG"
echo "=== STAGE 3 (--allow-fc-fail, LE v3.1 + preserve) ===" | tee -a "$LOG"
echo "BOOK_S2: $BOOK_S2" | tee -a "$LOG"
echo "FACTMAP: $FACTMAP" | tee -a "$LOG"
echo "FC_REPORT: $FC_REPORT" | tee -a "$LOG"

if [ -n "$FC_REPORT" ]; then
  python3 -u scripts/test_stage3.py \
    --book-draft "$BOOK_S2" \
    --fact-map "$FACTMAP" \
    --fc-warnings "$FC_REPORT" \
    --output-dir exports/stage3_v56 \
    --prefix "${PREFIX}" \
    --allow-fc-fail \
    2>&1 | tee -a "$LOG"
else
  python3 -u scripts/test_stage3.py \
    --book-draft "$BOOK_S2" \
    --fact-map "$FACTMAP" \
    --output-dir exports/stage3_v56 \
    --prefix "${PREFIX}" \
    --allow-fc-fail \
    2>&1 | tee -a "$LOG"
fi

BOOK_S3=$(ls -t exports/stage3_v56/${PREFIX}_book_FINAL_stage3_*.json 2>/dev/null | head -1)
if [ -z "$BOOK_S3" ]; then echo 'ERROR: book_FINAL_stage3 not found'; exit 1; fi
echo "BOOK_S3: $BOOK_S3" | tee -a "$LOG"

echo "" | tee -a "$LOG"
echo "=== LE STRUCTURAL PRESERVATION ===" | tee -a "$LOG"
PRES=$(ls -t exports/stage3_v56/${PREFIX}_le_structural_preservation_*.json 2>/dev/null | head -1)
if [ -n "$PRES" ]; then
  python3 -c "
import json
d = json.load(open('$PRES', encoding='utf-8'))
print('chapters_with_restored_fields:', d.get('chapters_with_restored_fields'))
for r in d.get('restorations', []):
    print(' ', r.get('chapter_id'), ':', r.get('restored_fields'))
" | tee -a "$LOG"
fi

echo "" | tee -a "$LOG"
echo "=== BUILD GATE1 FULL TEXT ===" | tee -a "$LOG"
mkdir -p collab/runs/karakulina_v56
python3 scripts/build_gate1_full_text.py \
  --book-final "$BOOK_S3" \
  --fact-map "$FACTMAP" \
  --output collab/runs/karakulina_v56/karakulina_v56_text_FULL.md \
  2>&1 | tee -a "$LOG"

echo "" | tee -a "$LOG"
echo "=== DONE: v56 ===" | tee -a "$LOG"
ls -lh exports/stage3_v56/ | tee -a "$LOG"
