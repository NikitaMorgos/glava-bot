#!/bin/bash
# v43 Stage 3 (LE + PR)
set -e
cd /opt/glava

BOOK=$(ls /opt/glava/exports/karakulina_book_FINAL_20260505_133931.json)
FC=$(ls /opt/glava/exports/karakulina_fc_report_iter3_20260505_133931.json 2>/dev/null || echo "")
FM=/opt/glava/exports/karakulina_fact_map_v42_input.json
LOG=/opt/glava/exports/run_stage3_v43.log

echo "=== v43 Stage 3 ===" | tee "$LOG"
echo "Book: $BOOK" | tee -a "$LOG"

CMD="python3 scripts/test_stage3.py --book-draft $BOOK --fact-map $FM"
if [ -n "$FC" ]; then
  CMD="$CMD --fc-warnings $FC"
fi
echo "CMD: $CMD" | tee -a "$LOG"

$CMD >> "$LOG" 2>&1

echo "=== DONE ===" | tee -a "$LOG"
