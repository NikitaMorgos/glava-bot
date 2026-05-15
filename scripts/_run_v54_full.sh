#!/bin/bash
# v54: Stage 1 (TR1+TR2 combined) → Stage 2 → Stage 3 (LE v3.1 + preserve)
# НЕТ Stage 4 — по решению Никиты (вёрстку не делаем)
set -e
cd /opt/glava
source .venv/bin/activate
set -a; source /opt/glava/.env; set +a

PREFIX=karakulina_v54
TR1=/opt/glava/exports/transcripts/karakulina_valentina_interview_assemblyai.txt
TR2=/opt/glava/exports/transcripts/karakulina_nikita_tatyana_interview_20260403.txt
LOG=/opt/glava/exports/run_v54_full.log

mkdir -p exports/karakulina_v54 exports/stage2_v54 exports/stage3_v54 collab/runs/karakulina_v54
echo '' > "$LOG"

# ── SANITY CHECK ──────────────────────────────────────────────────────────────
echo "=== SANITY CHECK ===" | tee -a "$LOG"
git log -1 --oneline | tee -a "$LOG"
python3 -c "
import json, sys
sys.path.insert(0, '/opt/glava')
from pipeline_utils import preserve_chapter_structural_fields
cfg = json.load(open('prompts/pipeline_config.json', encoding='utf-8'))
print('GW prompt:', cfg['ghostwriter']['prompt_file'])
print('LE prompt:', cfg['literary_editor']['prompt_file'])
print('FC prompt:', cfg['fact_checker']['prompt_file'])
print('preserve_chapter_structural_fields: OK')
" | tee -a "$LOG"

# ── STAGE 1 (TR1+TR2 combined) ────────────────────────────────────────────────
echo "" | tee -a "$LOG"
echo "=== STAGE 1 (TR1+TR2 combined) ===" | tee -a "$LOG"
python3 -u scripts/test_stage1_karakulina_full.py \
  --transcript1 "$TR1" \
  --transcript2 "$TR2" \
  --output-dir exports/karakulina_v54 \
  2>&1 | tee -a "$LOG"

FACTMAP=$(ls -t exports/karakulina_v54/karakulina_fact_map_full_*.json 2>/dev/null | head -1)
if [ -z "$FACTMAP" ]; then echo 'ERROR: fact_map_full not found'; exit 1; fi
echo "FACTMAP: $FACTMAP" | tee -a "$LOG"

# ── STAGE 2 ───────────────────────────────────────────────────────────────────
echo "" | tee -a "$LOG"
echo "=== STAGE 2 ===" | tee -a "$LOG"
python3 -u scripts/test_stage2_pipeline.py \
  --fact-map "$FACTMAP" \
  --output-dir exports/stage2_v54 \
  2>&1 | tee -a "$LOG"

BOOK_S2_RAW=$(ls -t exports/stage2_v54/karakulina_book_FINAL_*.json 2>/dev/null | head -1)
if [ -z "$BOOK_S2_RAW" ]; then echo 'ERROR: book_FINAL S2 not found'; exit 1; fi

# Переименовываем Stage 2 book чтобы явно отметить v54 и stage2
TS_S2=$(basename "$BOOK_S2_RAW" | sed 's/karakulina_book_FINAL_//' | sed 's/.json//')
BOOK_S2="${BOOK_S2_RAW%karakulina_book_FINAL_*}${PREFIX}_book_FINAL_stage2_${TS_S2}.json"
cp "$BOOK_S2_RAW" "$BOOK_S2"
echo "BOOK_S2: $BOOK_S2" | tee -a "$LOG"

FC_REPORT=$(ls -t exports/stage2_v54/karakulina_fc_report_iter*.json 2>/dev/null | head -1)

echo "scope_merge artifacts:" | tee -a "$LOG"
ls -t exports/stage2_v54/karakulina_scope_merge_iter*.json 2>/dev/null | tee -a "$LOG"

# ── STAGE 3 (LE v3.1 + preserve_chapter_structural_fields) ───────────────────
echo "" | tee -a "$LOG"
echo "=== STAGE 3 (LE v3.1 + preserve_chapter_structural_fields) ===" | tee -a "$LOG"
if [ -n "$FC_REPORT" ]; then
  python3 -u scripts/test_stage3.py \
    --book-draft "$BOOK_S2" \
    --fact-map "$FACTMAP" \
    --fc-warnings "$FC_REPORT" \
    --output-dir exports/stage3_v54 \
    --prefix "${PREFIX}" \
    2>&1 | tee -a "$LOG"
else
  python3 -u scripts/test_stage3.py \
    --book-draft "$BOOK_S2" \
    --fact-map "$FACTMAP" \
    --output-dir exports/stage3_v54 \
    --prefix "${PREFIX}" \
    2>&1 | tee -a "$LOG"
fi

BOOK_S3=$(ls -t exports/stage3_v54/${PREFIX}_book_FINAL_stage3_*.json 2>/dev/null | head -1)
if [ -z "$BOOK_S3" ]; then echo 'ERROR: book_FINAL_stage3 not found'; exit 1; fi
echo "BOOK_S3: $BOOK_S3" | tee -a "$LOG"

# ── LE STRUCTURAL PRESERVATION REPORT ────────────────────────────────────────
echo "" | tee -a "$LOG"
echo "=== LE STRUCTURAL PRESERVATION ===" | tee -a "$LOG"
PRES=$(ls -t exports/stage3_v54/${PREFIX}_le_structural_preservation_*.json 2>/dev/null | head -1)
if [ -n "$PRES" ]; then
  python3 -c "
import json
d = json.load(open('$PRES', encoding='utf-8'))
print('chapters_with_restored_fields:', d.get('chapters_with_restored_fields', []))
print('total_fields_restored:', d.get('total_fields_restored', 0))
" | tee -a "$LOG"
else
  echo "WARN: le_structural_preservation json not found" | tee -a "$LOG"
fi

# ── BUILD GATE1 FULL TEXT (детерминированный MD-сборщик) ─────────────────────
echo "" | tee -a "$LOG"
echo "=== BUILD GATE1 FULL TEXT ===" | tee -a "$LOG"
python3 scripts/build_gate1_full_text.py \
  --book-final "$BOOK_S3" \
  --fact-map "$FACTMAP" \
  --output collab/runs/karakulina_v54/karakulina_v54_text_FULL.md \
  2>&1 | tee -a "$LOG"

# ── ИТОГ ──────────────────────────────────────────────────────────────────────
echo "" | tee -a "$LOG"
echo "=== ARTIFACTS SUMMARY ===" | tee -a "$LOG"
echo "--- exports/karakulina_v54/ ---" | tee -a "$LOG"
ls -lh exports/karakulina_v54/ 2>/dev/null | tee -a "$LOG"
echo "--- exports/stage2_v54/ ---" | tee -a "$LOG"
ls -lh exports/stage2_v54/ 2>/dev/null | tee -a "$LOG"
echo "--- exports/stage3_v54/ ---" | tee -a "$LOG"
ls -lh exports/stage3_v54/ 2>/dev/null | tee -a "$LOG"
echo "--- collab/runs/karakulina_v54/ ---" | tee -a "$LOG"
ls -lh collab/runs/karakulina_v54/ 2>/dev/null | tee -a "$LOG"

echo "" | tee -a "$LOG"
echo "=== DONE: v54 ===" | tee -a "$LOG"
echo "TEXT: collab/runs/karakulina_v54/karakulina_v54_text_FULL.md" | tee -a "$LOG"
