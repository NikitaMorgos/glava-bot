#!/bin/bash
# v65 continuation — starts AFTER Stage 2 first pass + validators/hints already done
# Picks up from: exports/stage2_v65/revision_hints.json (18 hints)
# Runs: Stage 2 revision pass → schema → diff_audit → hist_notes enrichment
#       → Stage 3 + preserve_writing_notes → build_gate1 → final validators → collect artifacts

set -e
cd /opt/glava

set -a
source .env
set +a

ARTIFACTS_DIR="collab/runs/karakulina-v65-artifacts"

echo ""
echo "=== v65 CONTINUE: Stage 2 revision pass → Stage 3 → build_gate1 ==="
echo ""

STAGE2_DIR="exports/stage2_v65"
FM65=$(ls -t exports/karakulina_v65/karakulina_fact_map_full_*.json | grep -v enriched | grep -v TR1 | head -1)
echo "fact_map: $FM65"

REVISION_HINTS="$STAGE2_DIR/revision_hints.json"
HINTS_COUNT=$(python -c "import json; h=json.load(open('$REVISION_HINTS',encoding='utf-8')); print(len(h))")
echo "revision_hints loaded: $HINTS_COUNT hints"

echo ""
echo "=== STAGE 2 revision pass (GW v2.24 call_type=revision) ==="
python scripts/test_stage2_pipeline.py \
  --fact-map "$FM65" \
  --output-dir "$STAGE2_DIR" \
  --revision-pass "$REVISION_HINTS" \
  --allow-fc-fail || echo "NOTE: revision pass flag not supported — using book_draft as final"

echo ""
echo "=== 049e-2: schema validation — rule13_revision_applied must be list of dicts ==="
python scripts/_v65_schema_check.py

echo ""
echo "=== diff audit (authorized vs unauthorized changes) ==="
python scripts/_v65_diff_audit.py

echo ""
echo "=== 046d: historical_notes enrichment (post-revision) ==="
python scripts/_v65_hist_enrich.py

echo ""
echo "=== STAGE 3 (LE + Proofreader + validators + 049g preserve_writing_notes) ==="
BOOK_V65=$(ls -t "$STAGE2_DIR/karakulina_book_FINAL_*_enriched.json" 2>/dev/null | head -1)
if [ -z "$BOOK_V65" ]; then
    BOOK_V65=$(ls -t "$STAGE2_DIR/karakulina_book_FINAL_*.json" | grep -v draft | head -1)
fi
echo "book for stage3: $BOOK_V65"

mkdir -p exports/stage3_v65
python scripts/test_stage3.py \
  --book-draft "$BOOK_V65" \
  --fact-map "$FM65" \
  --output-dir exports/stage3_v65 \
  --prefix karakulina \
  --no-strict-gates

echo ""
echo "=== 049g: verify + apply preserve_writing_notes in stage3 output ==="
python scripts/_v65_preserve_wn.py

echo ""
echo "=== build_gate1_full_text (required vs optional + chars sum NOT file_size) ==="
BOOK_FINAL_S3=$(ls -t exports/stage3_v65/karakulina_book_FINAL_stage3_*.json | head -1)
python scripts/build_gate1_full_text.py \
  --book-final "$BOOK_FINAL_S3" \
  --fact-map "$FM65" \
  --output exports/stage3_v65/karakulina_v65_text_FULL.md \
  --reports-dir exports/stage3_v65 \
  --prefix karakulina \
  --pin-list collab/context/known_episodes_karakulina.md

echo ""
echo "=== final validators (post-revision, on stage3 output) ==="
python scripts/_v65_final_validators.py

echo ""
echo "=== distribution gate chars summary ==="
python scripts/_v65_chars_summary.py

echo ""
echo "=== собираем артефакты в $ARTIFACTS_DIR ==="
mkdir -p "$ARTIFACTS_DIR"
cp exports/karakulina_v65/karakulina_fact_map_full_*.json "$ARTIFACTS_DIR/" 2>/dev/null || true
cp "$STAGE2_DIR/karakulina_book_draft.json" "$ARTIFACTS_DIR/" 2>/dev/null || true
cp "$STAGE2_DIR/karakulina_book_FINAL_*.json" "$ARTIFACTS_DIR/" 2>/dev/null || true
cp "$STAGE2_DIR/karakulina_stage2_run_manifest_*.json" "$ARTIFACTS_DIR/" 2>/dev/null || true
cp "$STAGE2_DIR/validators_on_draft.json" "$ARTIFACTS_DIR/" 2>/dev/null || true
cp "$STAGE2_DIR/revision_hints.json" "$ARTIFACTS_DIR/" 2>/dev/null || true
cp "$STAGE2_DIR/revision_diff_audit.json" "$ARTIFACTS_DIR/" 2>/dev/null || true
cp "$STAGE2_DIR/revision_pass_log.json" "$ARTIFACTS_DIR/" 2>/dev/null || true
cp "$STAGE2_DIR/karakulina_revision_input.json" "$ARTIFACTS_DIR/" 2>/dev/null || true
cp exports/stage3_v65/karakulina_book_FINAL_stage3_*.json "$ARTIFACTS_DIR/" 2>/dev/null || true
cp exports/stage3_v65/karakulina_v65_text_FULL.md "$ARTIFACTS_DIR/" 2>/dev/null || true
cp exports/stage3_v65/karakulina_style_checks_*.json "$ARTIFACTS_DIR/" 2>/dev/null || true
cp exports/stage3_v65/karakulina_chronology_check_*.json "$ARTIFACTS_DIR/" 2>/dev/null || true
cp exports/stage3_v65/karakulina_pin_list_depth_*.json "$ARTIFACTS_DIR/" 2>/dev/null || true
cp exports/stage3_v65/karakulina_discourse_markers_*.json "$ARTIFACTS_DIR/" 2>/dev/null || true
cp exports/stage3_v65/karakulina_stage3_run_manifest_*.json "$ARTIFACTS_DIR/" 2>/dev/null || true
cp exports/stage3_v65/karakulina_v65_final_validators.json "$ARTIFACTS_DIR/" 2>/dev/null || true
cp exports/stage3_v65/karakulina_required_episodes_coverage.json "$ARTIFACTS_DIR/" 2>/dev/null || true

echo ""
echo "=== v65 CONTINUE: ЗАВЕРШЁН ==="
echo "Артефакты: $ARTIFACTS_DIR"
