#!/usr/bin/env bash
set -euo pipefail
source /opt/glava/.venv/bin/activate
set -a; source /opt/glava/.env; set +a
cd /opt/glava

RUN="/opt/glava/exports/karakulina_full_20260413_075342"
FM="$RUN/karakulina_fact_map_full_20260413_075343.json"
S2="$RUN/karakulina_book_FINAL_20260413_075846.json"
TR2="/opt/glava/exports/karakulina_meeting_transcript_20260403.txt"
LOG="/opt/glava/exports/run_full_karakulina_live4.log"

echo "" >> "$LOG"
echo ">>> STAGE 3 (продолжение после strict-gates fix)" >> "$LOG"

python scripts/test_stage3.py \
    --book-draft "$S2" \
    --fact-map "$FM" >> "$LOG" 2>&1

S3=$(ls -t /opt/glava/exports/karakulina_book_FINAL_stage3_*.json 2>/dev/null | head -1)
echo "[OK] stage3 book: $S3" >> "$LOG"

echo "" >> "$LOG"
echo ">>> PHASE B (продолжение)" >> "$LOG"

python scripts/test_stage2_phase_b.py \
    --current-book "$S3" \
    --new-transcript "$TR2" \
    --fact-map "$FM" \
    --output-dir "$RUN" >> "$LOG" 2>&1

# Копируем в collab
COLLAB="/opt/glava/collab/runs/karakulina_full_20260413_075342"
mkdir -p "$COLLAB"
cp "$FM" "$COLLAB/"
cp "$S2" "$COLLAB/"
cp "$S3" "$COLLAB/"
PB=$(ls -t "$RUN"/karakulina_book_FINAL_phase_b_*.json 2>/dev/null | head -1)
cp "$PB" "$COLLAB/"
cp "$RUN"/karakulina_FINAL_phase_b_*.txt "$COLLAB/" 2>/dev/null || true

echo "" >> "$LOG"
echo "===============================================" >> "$LOG"
echo " ПРОГОН ЗАВЕРШЁН (Вариант B): karakulina_full_20260413_075342" >> "$LOG"
echo " Артефакты: $COLLAB" >> "$LOG"
echo "===============================================" >> "$LOG"
