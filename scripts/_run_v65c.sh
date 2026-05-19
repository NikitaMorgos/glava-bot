#!/bin/bash
# v65c: pointed fix pipeline
# Input: exports/stage2_v65/karakulina_book_FINAL_1779175986_revised.json
# Steps: v65c revision pass → stage3 → preserve_wn → validators → build_gate1 → report

set -e
cd /opt/glava

set -a
source .env
set +a

V65C_DIR="exports/stage2_v65c"
STAGE3C_DIR="exports/stage3_v65c"
ARTIFACTS_DIR="collab/runs/karakulina-v65-artifacts"
FM65=$(ls -t exports/karakulina_v65/karakulina_fact_map_full_*.json | head -1)

mkdir -p "$V65C_DIR" "$STAGE3C_DIR" "$ARTIFACTS_DIR"

echo ""
echo "=== v65c: STEP 1 — revision pass (3 must_apply + 1 optional) ==="
python scripts/_v65c_revision_pass.py

REVISED_BOOK="${V65C_DIR}/karakulina_book_FINAL_v65c_revised.json"
if [ ! -f "$REVISED_BOOK" ]; then
    echo "ERROR: v65c revised book not found"; exit 1
fi
echo "v65c revised book: $REVISED_BOOK"

echo ""
echo "=== v65c: STEP 2 — Stage 3 (LE + Proofreader) ==="
python scripts/test_stage3.py \
  --book-draft "$REVISED_BOOK" \
  --fact-map "$FM65" \
  --output-dir "$STAGE3C_DIR" \
  --prefix karakulina \
  --no-strict-gates

echo ""
echo "=== v65c: STEP 3 — preserve writing_notes post-LE ==="
python scripts/_v65c_preserve_wn.py

echo ""
echo "=== v65c: STEP 4 — final validators ==="
python scripts/_v65c_final_validators.py

echo ""
echo "=== v65c: STEP 5 — build_gate1_full_text ==="
BOOK_FINAL_S3C=$(ls -t ${STAGE3C_DIR}/karakulina_book_FINAL_stage3_*.json | head -1)
echo "Stage 3 v65c final: $BOOK_FINAL_S3C"

python scripts/build_gate1_full_text.py \
  --book-final "$BOOK_FINAL_S3C" \
  --fact-map "$FM65" \
  --output "${STAGE3C_DIR}/karakulina_v65c_text_FULL.md" \
  --reports-dir "$STAGE3C_DIR" \
  --prefix karakulina \
  --pin-list collab/context/known_episodes_karakulina.md

echo ""
echo "=== v65c: STEP 6 — verified-on-run report ==="
python scripts/_v65c_verified_report.py

echo ""
echo "=== v65c: собираем артефакты ==="
cp "$REVISED_BOOK" "$ARTIFACTS_DIR/karakulina_book_FINAL_v65c_revised.json" 2>/dev/null || true
cp "${V65C_DIR}/revision_diff_audit_v65c.json" "$ARTIFACTS_DIR/" 2>/dev/null || true
cp ${STAGE3C_DIR}/karakulina_book_FINAL_stage3_*.json "$ARTIFACTS_DIR/karakulina_book_FINAL_stage3_v65c.json" 2>/dev/null || true
cp "${STAGE3C_DIR}/karakulina_v65c_text_FULL.md" "$ARTIFACTS_DIR/" 2>/dev/null || true
cp "${STAGE3C_DIR}/karakulina_v65c_final_validators.json" "$ARTIFACTS_DIR/" 2>/dev/null || true
cp "${STAGE3C_DIR}/karakulina_required_episodes_coverage_v65c.json" "$ARTIFACTS_DIR/" 2>/dev/null || true
cp ${STAGE3C_DIR}/karakulina_style_checks_*.json "$ARTIFACTS_DIR/" 2>/dev/null || true
cp ${STAGE3C_DIR}/karakulina_chronology_check_*.json "$ARTIFACTS_DIR/" 2>/dev/null || true
cp ${STAGE3C_DIR}/karakulina_stage3_run_manifest_*.json "$ARTIFACTS_DIR/karakulina_stage3_run_manifest_v65c.json" 2>/dev/null || true
cp "${ARTIFACTS_DIR}/karakulina_v65c_VERIFIED_ON_RUN.md" "$ARTIFACTS_DIR/" 2>/dev/null || true

echo ""
echo "=== v65c ЗАВЕРШЁН ==="
echo "Артефакты: $ARTIFACTS_DIR"
ls "$ARTIFACTS_DIR/"
