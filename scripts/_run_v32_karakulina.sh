#!/usr/bin/env bash
# Karakulina v32: Stage1->Stage2(+historian)->Stage3->PhaseB
# Ghostwriter v2.11 (АБСОЛЮТНЫЕ ЗАПРЕТЫ), FC v2.4, temp=0.4
# Phase B: FC FAIL -> Ghostwriter retry, max 3 итерации FC (2 ревизии)
set -euo pipefail

GLAVA_DIR="/opt/glava"
VENV="$GLAVA_DIR/venv"
EXPORTS="$GLAVA_DIR/exports"
COLLAB="$GLAVA_DIR/collab"
SCRIPTS="$GLAVA_DIR/scripts"

TS=$(date +%Y%m%d_%H%M%S)
V="v32"
PREFIX="karakulina_${V}"
RUN_DIR="$EXPORTS/${PREFIX}_run_${TS}"
mkdir -p "$RUN_DIR"

LOG="$RUN_DIR/run.log"
exec > >(tee "$LOG") 2>&1

echo "=============================================="
echo " GLAVA Full Run Karakulina $V"
echo " Tag:    $PREFIX"
echo " Time:   $(date)"
echo " Config: prompts/pipeline_config.json"
echo " GW:     03_ghostwriter_v2.6.md (v2.11), temp=0.4"
echo " FC:     04_fact_checker_v2.md (v2.4)"
echo " Istorik: 12_historian_v3.md, VKLYUCHEN"
echo " Phase B FC iterations: max 3 (2 Ghostwriter retries)"
echo "=============================================="

source "$VENV/bin/activate"
set -a; source "$GLAVA_DIR/.env"; set +a
cd "$GLAVA_DIR"

# Verify config before run
echo "[CONFIG-CHECK] Ghostwriter:"
python3 -c "import json; c=json.load(open('prompts/pipeline_config.json')); gw=c['ghostwriter']; print(f'  prompt={gw[\"prompt_file\"]} temp={gw[\"temperature\"]}')"
echo "[CONFIG-CHECK] FC:"
python3 -c "import json; c=json.load(open('prompts/pipeline_config.json')); fc=c['fact_checker']; print(f'  prompt={fc[\"prompt_file\"]} temp={fc[\"temperature\"]}')"

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
python3 "$SCRIPTS/test_stage1_karakulina_full.py" \
    --transcript1 "$TR1" \
    --output-dir  "$RUN_DIR"

FACT_MAP=$(ls -t "$RUN_DIR"/karakulina_fact_map_full_*.json 2>/dev/null | head -1)
if [ -z "$FACT_MAP" ]; then echo "[ERROR] fact_map not found"; exit 1; fi
echo "[OK] fact_map: $(basename $FACT_MAP)"

echo ""
echo ">>> STAGE 2: Istorik v3 + Ghostwriter v2.11 + FC v2.4 (historian ENABLED)"
python3 "$SCRIPTS/test_stage2_pipeline.py" \
    --fact-map          "$FACT_MAP" \
    --output-dir        "$RUN_DIR" \
    --variant-b \
    --max-fc-iterations 5 || true

BOOK_S2=$(ls -t "$RUN_DIR"/karakulina_book_FINAL_*.json 2>/dev/null | head -1)
if [ -z "$BOOK_S2" ]; then echo "[ERROR] stage2 book not found"; exit 1; fi
echo "[OK] stage2 book: $(basename $BOOK_S2)"

echo ""
echo ">>> STAGE 3: LitEditor v3 + Proofreader v1"
python3 "$SCRIPTS/test_stage3.py" \
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
echo ">>> PHASE B: TR2 + Incremental FactExtractor + FC max 3 iterations"
python3 "$SCRIPTS/test_stage2_phase_b.py" \
    --current-book      "$BOOK_S3" \
    --new-transcript    "$TR2" \
    --fact-map          "$FACT_MAP" \
    --output-dir        "$RUN_DIR" \
    --prefix            "$PREFIX" \
    --variant-b \
    --max-fc-iterations 3

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

cp "$FACT_MAP"  "$COLLAB_RUN/fact_map_v32.json"
cp "$BOOK_S2"   "$COLLAB_RUN/book_FINAL_stage2.json"
cp "$BOOK_S3"   "$COLLAB_RUN/book_FINAL_stage3.json"
cp "$BOOK_PB"   "$COLLAB_RUN/book_FINAL_phase_b_v32.json"
test -n "$TXT_S3"    && cp "$TXT_S3"    "$COLLAB_RUN/"
test -n "$FINAL_TXT" && cp "$FINAL_TXT" "$COLLAB_RUN/"
cp "$LOG" "$COLLAB_RUN/run.log"

MANIFEST_S2=$(ls -t "$RUN_DIR"/karakulina_stage2_run_manifest_*.json 2>/dev/null | head -1 || true)
test -n "$MANIFEST_S2" && cp "$MANIFEST_S2" "$COLLAB_RUN/run_manifest_s2.json"
MANIFEST_S3=$(ls -t "$EXPORTS"/${PREFIX}_stage3_run_manifest_*.json 2>/dev/null | head -1 || true)
test -n "$MANIFEST_S3" && cp "$MANIFEST_S3" "$COLLAB_RUN/run_manifest_s3.json"

# Copy Phase B manifest
MANIFEST_PB=$(ls -t "$RUN_DIR"/${PREFIX}_phase_b_run_manifest_*.json 2>/dev/null | head -1 || true)
test -n "$MANIFEST_PB" && cp "$MANIFEST_PB" "$COLLAB_RUN/run_manifest_phase_b.json"

printf "# Run: %s (%s)\n\nGhostwriter v2.11 (АБСОЛЮТНЫЕ ЗАПРЕТЫ), temp=0.4\nFC v2.4 (framing_distortion)\nIstorik 12_historian_v3.md\nPhase B: max 3 FC iterations\nTR1: assemblyai\nTR2: meeting transcript\n" "$PREFIX" "$TS" > "$COLLAB_RUN/README.md"

echo "${COLLAB_RUN}" > "$EXPORTS/karakulina_v32_last_collab_run.txt"

echo ""
echo "=============================================="
echo " DONE: ${PREFIX}"
echo " collab: $COLLAB_RUN"
echo "=============================================="
