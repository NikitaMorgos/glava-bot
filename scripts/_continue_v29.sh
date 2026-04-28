#!/usr/bin/env bash
# Stage3 + PhaseB manual continuation of v29 run
set -uo pipefail   # no -e to survive strict gates

GLAVA_DIR="/opt/glava"
VENV="$GLAVA_DIR/venv"
EXPORTS="$GLAVA_DIR/exports"
COLLAB="$GLAVA_DIR/collab"
SCRIPTS="$GLAVA_DIR/scripts"

RUN_DIR="$EXPORTS/karakulina_v29_run_20260420_072506"
PREFIX="karakulina_v29"
TR2="$EXPORTS/transcripts/karakulina_meeting_transcript_20260403.txt"

source "$VENV/bin/activate"
set -a; source "$GLAVA_DIR/.env"; set +a
cd "$GLAVA_DIR"

FACT_MAP=$(ls -t "$RUN_DIR"/karakulina_fact_map_full_*.json | head -1)
BOOK_S2=$(ls -t "$RUN_DIR"/karakulina_book_FINAL_*.json | head -1)

echo "[v29-continue] FACT_MAP: $(basename $FACT_MAP)"
echo "[v29-continue] BOOK_S2:  $(basename $BOOK_S2)"
echo "[v29-continue] TR2:      $(basename $TR2)"

echo ""
echo ">>> STAGE 3: LitEditor + Proofreader"
python "$SCRIPTS/test_stage3.py" \
    --book-draft "$BOOK_S2" \
    --fact-map   "$FACT_MAP" \
    --prefix     "$PREFIX" \
    --variant-b

BOOK_S3=$(ls -t "$EXPORTS"/${PREFIX}_book_FINAL_stage3_*.json 2>/dev/null | head -1)
if [ -z "$BOOK_S3" ]; then echo "[ERROR] stage3 book not found"; exit 1; fi
TXT_S3=$(ls -t "$EXPORTS"/${PREFIX}_FINAL_stage3_*.txt 2>/dev/null | head -1 || true)
echo "[OK] stage3: $(basename $BOOK_S3)"

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
echo "[OK] phase_b: $(basename $BOOK_PB)"

FINAL_TXT=$(ls -t "$RUN_DIR"/${PREFIX}_FINAL_phase_b_*.txt 2>/dev/null | head -1 || \
            ls -t "$RUN_DIR"/karakulina_FINAL_phase_b_*.txt 2>/dev/null | head -1 || \
            echo "")

TS=$(date +%Y%m%d_%H%M%S)
COLLAB_RUN="$COLLAB/runs/${PREFIX}_${TS}"
mkdir -p "$COLLAB_RUN"

cp "$FACT_MAP"  "$COLLAB_RUN/fact_map_v29.json"
cp "$BOOK_S2"   "$COLLAB_RUN/book_FINAL_stage2.json"
cp "$BOOK_S3"   "$COLLAB_RUN/book_FINAL_stage3.json"
cp "$BOOK_PB"   "$COLLAB_RUN/book_FINAL_phase_b_v29.json"
test -n "$TXT_S3"    && cp "$TXT_S3"    "$COLLAB_RUN/"
test -n "$FINAL_TXT" && cp "$FINAL_TXT" "$COLLAB_RUN/"

MANIFEST_S2=$(ls -t "$RUN_DIR"/karakulina_stage2_run_manifest_*.json 2>/dev/null | head -1 || true)
test -n "$MANIFEST_S2" && cp "$MANIFEST_S2" "$COLLAB_RUN/run_manifest_s2.json"
MANIFEST_S3=$(ls -t "$EXPORTS"/${PREFIX}_stage3_run_manifest_*.json 2>/dev/null | head -1 || true)
test -n "$MANIFEST_S3" && cp "$MANIFEST_S3" "$COLLAB_RUN/run_manifest_s3.json"

printf "# Run: %s (continued)\nGhostwriter v2.8, FC v2.3, Istorik ENABLED\n" "$PREFIX" > "$COLLAB_RUN/README.md"

echo "${COLLAB_RUN}" > "$EXPORTS/karakulina_v29_last_collab_run.txt"

echo ""
echo "=== DONE: $PREFIX ==="
echo "collab: $COLLAB_RUN"
