#!/bin/bash
# v65 Stage 3: run on existing revised book (skip Stage 1+2)
# Input: exports/stage2_v65/karakulina_book_FINAL_1779175986_revised.json
# Opus decision: Option C — continue Stage 3 on revised book
# audit_revision_diff false positive → v66 backlog

set -e
cd /opt/glava

set -a
source .env
set +a

ARTIFACTS_DIR="collab/runs/karakulina-v65-artifacts"
STAGE2_DIR="exports/stage2_v65"
STAGE3_DIR="exports/stage3_v65"

FM65=$(ls -t exports/karakulina_v65/karakulina_fact_map_full_*.json | grep -v enriched | grep -v TR1 | head -1)
echo "fact_map: $FM65"

echo ""
echo "=== v65 Stage 3: starting from revised book ==="
echo ""

echo "=== 046d: hist_notes distribution check + enrichment if needed ==="
python scripts/_v65_stage3_hist_check.py

# Stage 3 input = karakulina_book_stage3_input.json (set by hist_check)
BOOK_S3_INPUT="${STAGE2_DIR}/karakulina_book_stage3_input.json"
echo "Stage 3 input: $BOOK_S3_INPUT"

echo ""
echo "=== STAGE 3: Literary Editor + Proofreader ==="
mkdir -p "$STAGE3_DIR"
python scripts/test_stage3.py \
  --book-draft "$BOOK_S3_INPUT" \
  --fact-map "$FM65" \
  --output-dir "$STAGE3_DIR" \
  --prefix karakulina \
  --no-strict-gates

echo ""
echo "=== 049g: preserve_writing_notes in stage3 output ==="
python scripts/_v65_preserve_wn.py

echo ""
echo "=== final validators (post-Stage 3) ==="
python scripts/_v65_final_validators.py

echo ""
echo "=== distribution gate chars summary (bio_data for ch_01) ==="
python scripts/_v65_chars_summary.py

echo ""
echo "=== build_gate1_full_text (required vs optional + chars sum NOT file_size) ==="
BOOK_FINAL_S3=$(ls -t ${STAGE3_DIR}/karakulina_book_FINAL_stage3_*.json | head -1)
echo "Stage 3 final: $BOOK_FINAL_S3"

python scripts/build_gate1_full_text.py \
  --book-final "$BOOK_FINAL_S3" \
  --fact-map "$FM65" \
  --output "${STAGE3_DIR}/karakulina_v65_text_FULL.md" \
  --reports-dir "$STAGE3_DIR" \
  --prefix karakulina \
  --pin-list collab/context/known_episodes_karakulina.md

echo ""
echo "=== verified-on-run report ==="
python scripts/_v65_verified_report.py

echo ""
echo "=== собираем артефакты ==="
mkdir -p "$ARTIFACTS_DIR"

# Stage 3 artifacts
cp ${STAGE3_DIR}/karakulina_book_FINAL_stage3_*.json "$ARTIFACTS_DIR/" 2>/dev/null || true
cp "${STAGE3_DIR}/karakulina_v65_text_FULL.md" "$ARTIFACTS_DIR/" 2>/dev/null || true
cp ${STAGE3_DIR}/karakulina_style_checks_*.json "$ARTIFACTS_DIR/" 2>/dev/null || true
cp ${STAGE3_DIR}/karakulina_chronology_check_*.json "$ARTIFACTS_DIR/" 2>/dev/null || true
cp ${STAGE3_DIR}/karakulina_pin_list_depth_*.json "$ARTIFACTS_DIR/" 2>/dev/null || true
cp ${STAGE3_DIR}/karakulina_discourse_markers_*.json "$ARTIFACTS_DIR/" 2>/dev/null || true
cp ${STAGE3_DIR}/karakulina_stage3_run_manifest_*.json "$ARTIFACTS_DIR/" 2>/dev/null || true
cp "${STAGE3_DIR}/karakulina_v65_final_validators.json" "$ARTIFACTS_DIR/" 2>/dev/null || true
cp "${STAGE3_DIR}/karakulina_required_episodes_coverage.json" "$ARTIFACTS_DIR/" 2>/dev/null || true
cp "${ARTIFACTS_DIR}/karakulina_v65_VERIFIED_ON_RUN_continued.md" "$ARTIFACTS_DIR/" 2>/dev/null || true

echo ""
echo "=== v65 Stage 3: ЗАВЕРШЁН ==="
echo "Артефакты: $ARTIFACTS_DIR"
ls "$ARTIFACTS_DIR/"
