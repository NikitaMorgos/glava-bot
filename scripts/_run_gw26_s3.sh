#!/bin/bash
# Stage2 (Ghostwriter v2.6 + FC) + Stage3 (LitEditor + Proofreader)
# Input: approved fact_map checkpoint + full meeting transcript (03.04.2026)
# Historian: skipped; Layout (Stage4): skipped
# Prefix: karakulina_gw26_s3
set -e

cd /opt/glava
source /opt/glava/venv/bin/activate

FACT_MAP="/opt/glava/checkpoints/karakulina/fact_map.json"
TRANSCRIPT="/opt/glava/exports/karakulina_meeting_transcript_20260403.txt"
EXPORTS="/opt/glava/exports"
PREFIX="karakulina"
RUN_TAG="gw26_s3"

echo "============================================"
echo "Stage 2+3 run — Ghostwriter v2.6 + LitEditor + Proofreader"
echo "fact_map:   $FACT_MAP"
echo "transcript: $TRANSCRIPT"
echo "============================================"

# ── Stage 2 ──────────────────────────────────────────────────────────
echo ""
echo ">>> STAGE 2: Ghostwriter + Fact Checker"
python3 -u scripts/test_stage2_pipeline.py \
    --fact-map "$FACT_MAP" \
    --transcript "$TRANSCRIPT" \
    --output-dir "$EXPORTS" \
    --skip-historian \
    --skip-historian-pass2 \
    --max-fc-iterations 2

# Находим финальный book из Stage2 (самый свежий)
BOOK_FINAL=$(ls -t "$EXPORTS"/karakulina_book_FINAL_*.json 2>/dev/null | head -1)
FC_REPORT=$(ls -t "$EXPORTS"/karakulina_fc_report_iter*.json 2>/dev/null | head -1)

if [ -z "$BOOK_FINAL" ]; then
    echo "ERROR: Stage2 не создал book_FINAL"
    exit 1
fi

echo ""
echo ">>> Stage 2 готов: $BOOK_FINAL"
echo ">>> FC report:     $FC_REPORT"

# ── Stage 3 ──────────────────────────────────────────────────────────
echo ""
echo ">>> STAGE 3: Literary Editor + Proofreader"
python3 -u scripts/test_stage3.py \
    --book-draft "$BOOK_FINAL" \
    --fc-warnings "$FC_REPORT" \
    --fact-map "$FACT_MAP" \
    --prefix "$PREFIX"

# Итоговые артефакты
echo ""
echo "============================================"
echo "Stage 2+3 complete. Today's artifacts:"
TODAY=$(date +%Y%m%d)
ls -la "$EXPORTS"/ | grep "$TODAY" | grep -E "karakulina_(book|fc_report|liteditor|proofreader|stage[23]|run_manifest|FINAL)" | sort | tail -30
echo "============================================"
