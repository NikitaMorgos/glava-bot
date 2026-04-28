#!/usr/bin/env bash
# Karakulina v29: Stage1->Stage2(+historian)->Stage3->PhaseB
set -euo pipefail

GLAVA_DIR="/opt/glava"
VENV="$GLAVA_DIR/venv"
EXPORTS="$GLAVA_DIR/exports"
COLLAB="$GLAVA_DIR/collab"
SCRIPTS="$GLAVA_DIR/scripts"

TS=$(date +%Y%m%d_%H%M%S)
V="v29"
PREFIX="karakulina_${V}"
RUN_DIR="$EXPORTS/${PREFIX}_run_${TS}"
mkdir -p "$RUN_DIR"

LOG="$RUN_DIR/run.log"
exec > >(tee "$LOG") 2>&1

echo "=============================================="
echo " GLAVA Full Run Karakulina $V"
echo " Tag:  $PREFIX"
echo " Time: $(date)"
echo " Istorik: VKLYUCHEN"
echo "=============================================="

source "$VENV/bin/activate"
set -a; source "$GLAVA_DIR/.env"; set +a
cd "$GLAVA_DIR"

TR1="$EXPORTS/transcripts/karakulina_valentina_interview_assemblyai.txt"
TR2="$EXPORTS/transcripts/karakulina_meeting_transcript_20260403.txt"

if [ ! -f "$TR1" ]; then
    TR1=$(find "$EXPORTS" -name "*karakulina*assemblyai*.txt" 2>/dev/null | head -1)
fi
if [ ! -f "$TR2" ]; then
    TR2=$(find "$EXPORTS" -name "*meeting_transcript*.txt" 2>/dev/null | head -1)
fi

echo "[TR1] $TR1 ($(wc -c < "$TR1") bytes)"
echo "[TR2] $TR2 ($(wc -c < "$TR2") bytes)"

echo ""
echo ">>> STAGE 1: Fact Extractor v3.3"
python "$SCRIPTS/test_stage1_karakulina_full.py" \
    --transcript1 "$TR1" \
    --output-dir  "$RUN_DIR"

FACT_MAP=$(ls -t "$RUN_DIR"/karakulina_fact_map_full_*.json 2>/dev/null | head -1)
if [ -z "$FACT_MAP" ]; then echo "[ERROR] fact_map not found"; exit 1; fi
echo "[OK] fact_map: $(basename $FACT_MAP)"

echo ""
echo ">>> STAGE 2: Istorik v3 + Ghostwriter v2.8 + FC v2.3 (historian ENABLED)"
python "$SCRIPTS/test_stage2_pipeline.py" \
    --fact-map          "$FACT_MAP" \
    --output-dir        "$RUN_DIR" \
    --variant-b \
    --max-fc-iterations 5 || true  # strict_gates exit != FC fail — продолжаем

BOOK_S2=$(ls -t "$RUN_DIR"/karakulina_book_FINAL_*.json 2>/dev/null | head -1)
if [ -z "$BOOK_S2" ]; then echo "[ERROR] stage2 book not found"; exit 1; fi
echo "[OK] stage2 book: $(basename $BOOK_S2)"

echo ""
echo ">>> STAGE 3: LitEditor v3 + Proofreader v1"
python "$SCRIPTS/test_stage3.py" \
    --book-draft "$BOOK_S2" \
    --fact-map   "$FACT_MAP" \
    --prefix     "$PREFIX" \
    --variant-b

BOOK_S3=$(ls -t "$EXPORTS"/${PREFIX}_book_FINAL_stage3_*.json 2>/dev/null | head -1)
if [ -z "$BOOK_S3" ]; then echo "[ERROR] stage3 book not found"; exit 1; fi
TXT_S3=$(ls -t "$EXPORTS"/${PREFIX}_FINAL_stage3_*.txt 2>/dev/null | head -1 || true)
echo "[OK] stage3 book: $(basename $BOOK_S3)"

cp "$BOOK_S3" "$RUN_DIR/"
test -n "$TXT_S3" && cp "$TXT_S3" "$RUN_DIR/"

echo ""
echo ">>> PHASE B: TR2 + Incremental FactExtractor"
python "$SCRIPTS/test_stage2_phase_b.py" \
    --current-book   "$BOOK_S3" \
    --new-transcript "$TR2" \
    --fact-map       "$FACT_MAP" \
    --output-dir     "$RUN_DIR" \
    --prefix         "$PREFIX" \
    --variant-b

BOOK_PB=$(ls -t "$RUN_DIR"/${PREFIX}_book_FINAL_phase_b_*.json 2>/dev/null | head -1 || true)
if [ -z "$BOOK_PB" ]; then
    BOOK_PB=$(ls -t "$RUN_DIR"/karakulina_book_FINAL_phase_b_*.json 2>/dev/null | head -1)
fi
if [ -z "$BOOK_PB" ]; then echo "[ERROR] Phase B book not found"; exit 1; fi
echo "[OK] phase_b: $(basename $BOOK_PB)"

FINAL_TXT=$(ls -t "$RUN_DIR"/${PREFIX}_FINAL_phase_b_*.txt 2>/dev/null | head -1 || \
            ls -t "$RUN_DIR"/karakulina_FINAL_phase_b_*.txt 2>/dev/null | head -1 || \
            echo "")

COLLAB_RUN="$COLLAB/runs/${PREFIX}_${TS}"
mkdir -p "$COLLAB_RUN"

cp "$FACT_MAP" "$COLLAB_RUN/fact_map_v29.json"
cp "$BOOK_S2"  "$COLLAB_RUN/book_FINAL_stage2.json"
cp "$BOOK_S3"  "$COLLAB_RUN/book_FINAL_stage3.json"
cp "$BOOK_PB"  "$COLLAB_RUN/book_FINAL_phase_b_v29.json"
test -n "$TXT_S3"    && cp "$TXT_S3"    "$COLLAB_RUN/"
test -n "$FINAL_TXT" && cp "$FINAL_TXT" "$COLLAB_RUN/"
cp "$LOG" "$COLLAB_RUN/run.log"

MANIFEST_S2=$(ls -t "$RUN_DIR"/karakulina_stage2_run_manifest_*.json 2>/dev/null | head -1 || true)
test -n "$MANIFEST_S2" && cp "$MANIFEST_S2" "$COLLAB_RUN/run_manifest_s2.json"
MANIFEST_S3=$(ls -t "$EXPORTS"/${PREFIX}_stage3_run_manifest_*.json 2>/dev/null | head -1 || true)
test -n "$MANIFEST_S3" && cp "$MANIFEST_S3" "$COLLAB_RUN/run_manifest_s3.json"

printf "# Run: %s (%s)\n\nGhostwriter v2.8, FC v2.3, Istorik ENABLED\nTR1: assemblyai\nTR2: meeting transcript\n" "$PREFIX" "$TS" > "$COLLAB_RUN/README.md"

echo "${COLLAB_RUN}" > "$EXPORTS/karakulina_v29_last_collab_run.txt"

echo ""
echo "=============================================="
echo " DONE: ${PREFIX}"
echo " collab: $COLLAB_RUN"
echo "=============================================="
