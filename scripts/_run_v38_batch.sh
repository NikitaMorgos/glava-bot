#!/bin/bash
# v38 full batch run: Stage 1a → 1b → compare → Stage 2 → Stage 3 → Stage 4 (gate2c)
set -e
cd /opt/glava
VENV=.venv/bin/python
LOG=/tmp/v38_batch.log
TR1=exports/transcripts/karakulina_valentina_interview_assemblyai.txt
TR2=exports/transcripts/karakulina_nikita_tatyana_interview_20260403.txt
OUT_V38A=exports/karakulina_v38a
OUT_V38B=exports/karakulina_v38b
OUT_S2=exports/stage2_v38
OUT_S3=exports/stage3_v38

echo "=== v38 BATCH START $(date) ===" | tee -a $LOG

echo "--- STAGE 1a ---" | tee -a $LOG
mkdir -p $OUT_V38A
$VENV scripts/test_stage1_karakulina_full.py \
  --transcript1 $TR1 \
  --transcript2 $TR2 \
  --output-dir $OUT_V38A 2>&1 | tee -a $LOG
echo "STAGE 1a EXIT: $?" | tee -a $LOG

echo "--- STAGE 1b ---" | tee -a $LOG
mkdir -p $OUT_V38B
$VENV scripts/test_stage1_karakulina_full.py \
  --transcript1 $TR1 \
  --transcript2 $TR2 \
  --output-dir $OUT_V38B 2>&1 | tee -a $LOG
echo "STAGE 1b EXIT: $?" | tee -a $LOG

# Find outputs from 1a and 1b for stability compare
FACT_MAP_A=$(ls $OUT_V38A/karakulina_fact_map_full_*.json 2>/dev/null | tail -1)
FACT_MAP_B=$(ls $OUT_V38B/karakulina_fact_map_full_*.json 2>/dev/null | tail -1)
echo "Fact maps: A=$FACT_MAP_A B=$FACT_MAP_B" | tee -a $LOG

if [ -n "$FACT_MAP_A" ] && [ -n "$FACT_MAP_B" ]; then
  echo "--- STABILITY COMPARE ---" | tee -a $LOG
  $VENV scripts/compare_persons_across_runs.py \
    --run-a $FACT_MAP_A \
    --run-b $FACT_MAP_B \
    --output $OUT_V38A/v38_stability_report.json 2>&1 | tee -a $LOG
fi

# Find clean fact_map from 1a for stage2 (not 'full', not 'normalization')
FACT_MAP_CLEAN=$(ls $OUT_V38A/karakulina_fact_map_[0-9]*.json 2>/dev/null | grep -v 'full\|normalization' | tail -1)
if [ -z "$FACT_MAP_CLEAN" ]; then
  FACT_MAP_CLEAN=$(ls $OUT_V38A/karakulina_fact_map_*.json 2>/dev/null | grep -v 'full\|normalization' | tail -1)
fi
echo "Clean fact map for stage2: $FACT_MAP_CLEAN" | tee -a $LOG

echo "--- STAGE 2 ---" | tee -a $LOG
mkdir -p $OUT_S2
$VENV scripts/test_stage2_pipeline.py \
  --fact-map $FACT_MAP_CLEAN \
  --output-dir $OUT_S2 2>&1 | tee -a $LOG
echo "STAGE 2 EXIT: $?" | tee -a $LOG

# Find stage2 book output
BOOK_S2=$(ls $OUT_S2/karakulina_book_FINAL_*.json 2>/dev/null | tail -1)
echo "Stage2 book: $BOOK_S2" | tee -a $LOG

echo "--- STAGE 3 ---" | tee -a $LOG
mkdir -p $OUT_S3
$VENV scripts/test_stage3.py \
  --book-draft $BOOK_S2 \
  --fact-map $FACT_MAP_CLEAN \
  --prefix karakulina_v38 \
  --output-dir $OUT_S3 2>&1 | tee -a $LOG
echo "STAGE 3 EXIT: $?" | tee -a $LOG

# Find stage3 book output  
BOOK_S3=$(ls $OUT_S3/karakulina_v38_book_FINAL_stage3_*.json 2>/dev/null | tail -1)
if [ -z "$BOOK_S3" ]; then
  BOOK_S3=$(ls $OUT_S3/karakulina_v38_*stage3*.json 2>/dev/null | grep -v 'manifest\|gates\|text' | tail -1)
fi
echo "Stage3 book: $BOOK_S3" | tee -a $LOG

echo "--- STAGE 4 (gate2c) ---" | tee -a $LOG
$VENV scripts/test_stage4_karakulina.py \
  --allow-legacy-input \
  --proofreader-report $BOOK_S3 \
  --fact-map $FACT_MAP_CLEAN \
  --prefix karakulina_v38 \
  --acceptance-gate 2c \
  --no-photos 2>&1 | tee -a $LOG
echo "STAGE 4 EXIT: $?" | tee -a $LOG

echo "=== v38 BATCH DONE $(date) ===" | tee -a $LOG

