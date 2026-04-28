#!/bin/bash
# Stage2-only: Ghostwriter v2.6 + Fact Checker
# Input: approved fact_map checkpoint + full meeting transcript (03.04.2026)
# Historian: skipped (focus on Ghostwriter quality)
# Prefix: karakulina_gw_v26_fulltr
set -e

cd /opt/glava
source /opt/glava/venv/bin/activate

FACT_MAP="/opt/glava/checkpoints/karakulina/fact_map.json"
TRANSCRIPT="/opt/glava/exports/karakulina_meeting_transcript_20260403.txt"
PREFIX="karakulina_gw_v26_fulltr"

echo "============================================"
echo "Stage 2 — Ghostwriter v2.6 test"
echo "fact_map:   $FACT_MAP"
echo "transcript: $TRANSCRIPT"
echo "prefix:     $PREFIX"
echo "============================================"

if [ ! -f "$FACT_MAP" ]; then
    echo "ERROR: fact_map not found: $FACT_MAP"
    exit 1
fi

if [ ! -f "$TRANSCRIPT" ]; then
    echo "ERROR: transcript not found: $TRANSCRIPT"
    exit 1
fi

python3 -u scripts/test_stage2_pipeline.py \
    --fact-map "$FACT_MAP" \
    --transcript "$TRANSCRIPT" \
    --output-dir "/opt/glava/exports" \
    --skip-historian \
    --skip-historian-pass2 \
    --max-fc-iterations 2

echo ""
echo "============================================"
echo "Stage 2 complete. Today's artifacts:"
TODAY=$(date +%Y%m%d)
ls -la /opt/glava/exports/ | grep "$TODAY" | grep -E "karakulina_(book|fc_report|stage2_text_gates|run_manifest)" | tail -20
echo "============================================"
