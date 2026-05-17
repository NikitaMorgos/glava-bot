#!/bin/bash
set -e
cd /opt/glava
source venv/bin/activate
set -a; source /opt/glava/.env; set +a

LOG=/opt/glava/exports/run_v53b_full.log
PORTRAIT=/opt/glava/collab/stabilization_runs/karakulina_full_latest_20260409/karakulina_full_latest_stage4_cover_portrait_20260409_190332.webp
PREFIX=karakulina_v53b

mkdir -p exports/karakulina_v53b exports/stage2_v53b exports/stage3_v53b
echo '' > "$LOG"

# ── STAGE 1 ──────────────────────────────────────────────────────────────────
echo '=== STAGE 1 ===' | tee -a "$LOG"
python3 -u scripts/test_stage1_karakulina_full.py \
  --transcript1 /opt/glava/exports/transcripts/karakulina_nikita_tatyana_interview_20260403.txt \
  --output-dir exports/karakulina_v53b \
  2>&1 | tee -a "$LOG"

FACT_MAP_FULL=$(ls -t exports/karakulina_v53b/karakulina_fact_map_full_*.json 2>/dev/null | head -1)
if [ -z "$FACT_MAP_FULL" ]; then echo 'ERROR: fact_map_full not found'; exit 1; fi
echo "FACT_MAP_FULL: $FACT_MAP_FULL" | tee -a "$LOG"

# ── STAGE 2 ──────────────────────────────────────────────────────────────────
echo '=== STAGE 2 ===' | tee -a "$LOG"
python3 -u scripts/test_stage2_pipeline.py \
  --fact-map "$FACT_MAP_FULL" \
  --output-dir exports/stage2_v53b \
  2>&1 | tee -a "$LOG"

BOOK_FINAL_S2=$(ls -t exports/stage2_v53b/karakulina_book_FINAL_*.json 2>/dev/null | head -1)
if [ -z "$BOOK_FINAL_S2" ]; then echo 'ERROR: book_FINAL S2 not found'; exit 1; fi
echo "BOOK_FINAL_S2: $BOOK_FINAL_S2" | tee -a "$LOG"

FC_REPORT_LAST=$(ls -t exports/stage2_v53b/karakulina_fc_report_iter*.json 2>/dev/null | head -1)

# Log scope_merge artifacts
echo 'scope_merge artifacts:' | tee -a "$LOG"
ls -t exports/stage2_v53b/karakulina_scope_merge_iter*.json 2>/dev/null | tee -a "$LOG"

# ── STAGE 3 ──────────────────────────────────────────────────────────────────
echo '=== STAGE 3 ===' | tee -a "$LOG"
if [ -n "$FC_REPORT_LAST" ]; then
  python3 -u scripts/test_stage3.py \
    --book-draft "$BOOK_FINAL_S2" \
    --fact-map "$FACT_MAP_FULL" \
    --fc-warnings "$FC_REPORT_LAST" \
    --output-dir exports/stage3_v53b \
    --prefix "$PREFIX" \
    2>&1 | tee -a "$LOG"
else
  python3 -u scripts/test_stage3.py \
    --book-draft "$BOOK_FINAL_S2" \
    --fact-map "$FACT_MAP_FULL" \
    --output-dir exports/stage3_v53b \
    --prefix "$PREFIX" \
    2>&1 | tee -a "$LOG"
fi

PR_REPORT=$(ls -t exports/stage3_v53b/${PREFIX}_proofreader_report_*.json 2>/dev/null | head -1)
if [ -z "$PR_REPORT" ]; then echo 'ERROR: proofreader_report not found'; exit 1; fi
echo "PR_REPORT: $PR_REPORT" | tee -a "$LOG"

# ── STAGE 4 gate 1 ───────────────────────────────────────────────────────────
echo '=== STAGE 4 gate 1 ===' | tee -a "$LOG"
python3 -u scripts/test_stage4_karakulina.py \
  --proofreader-report "$PR_REPORT" \
  --fact-map "$FACT_MAP_FULL" \
  --acceptance-gate 1 \
  --approve-gate \
  --allow-legacy-input \
  --prefix "$PREFIX" \
  2>&1 | tee -a "$LOG"

# ── STAGE 4 gate 2a ──────────────────────────────────────────────────────────
echo '=== STAGE 4 gate 2a ===' | tee -a "$LOG"
python3 -u scripts/test_stage4_karakulina.py \
  --proofreader-report "$PR_REPORT" \
  --fact-map "$FACT_MAP_FULL" \
  --acceptance-gate 2a \
  --approve-gate \
  --allow-legacy-input \
  --prefix "$PREFIX" \
  2>&1 | tee -a "$LOG"

LAYOUT_2A=$(ls -t exports/${PREFIX}_stage4_layout_iter1_*.json 2>/dev/null | head -1)
if [ -z "$LAYOUT_2A" ]; then echo 'ERROR: layout 2a not found'; exit 1; fi
echo "LAYOUT_2A: $LAYOUT_2A" | tee -a "$LOG"

# ── STAGE 4 gate 2b ──────────────────────────────────────────────────────────
echo '=== STAGE 4 gate 2b ===' | tee -a "$LOG"
python3 -u scripts/test_stage4_karakulina.py \
  --proofreader-report "$PR_REPORT" \
  --fact-map "$FACT_MAP_FULL" \
  --acceptance-gate 2b \
  --approve-gate \
  --allow-legacy-input \
  --existing-layout "$LAYOUT_2A" \
  --prefix "$PREFIX" \
  2>&1 | tee -a "$LOG"

LAYOUT_2B=$(ls -t exports/${PREFIX}_reuse_layout_pages_*.json 2>/dev/null | head -1)
if [ -z "$LAYOUT_2B" ]; then echo 'ERROR: layout 2b not found'; exit 1; fi
echo "LAYOUT_2B: $LAYOUT_2B" | tee -a "$LOG"

# ── STAGE 4 gate 2c (no-photos, NO allow-mismatch) ───────────────────────────
echo '=== STAGE 4 gate 2c ===' | tee -a "$LOG"
python3 -u scripts/test_stage4_karakulina.py \
  --proofreader-report "$PR_REPORT" \
  --fact-map "$FACT_MAP_FULL" \
  --acceptance-gate 2c \
  --allow-legacy-input \
  --existing-layout "$LAYOUT_2B" \
  --existing-portrait "$PORTRAIT" \
  --prefix "$PREFIX" \
  --no-photos \
  2>&1 | tee -a "$LOG"

echo '=== DONE ===' | tee -a "$LOG"
