#!/bin/bash
# Phase B: вплетение нового интервью (Татьяна о Валентине, запись Никиты)
# в существующую книгу Каракулиной после Stage3.
# Затем прогоняет Stage3 (LitEditor + Proofreader) на обогащённом тексте.
set -e

cd /opt/glava
source /opt/glava/venv/bin/activate
set -a; source /opt/glava/.env; set +a

EXPORTS="/opt/glava/exports"
FACT_MAP="/opt/glava/checkpoints/karakulina/fact_map.json"
NEW_TRANSCRIPT="/opt/glava/exports/karakulina_cleaned_transcript_20260403.txt"
PREFIX="karakulina"

# Находим последнюю книгу Stage3
CURRENT_BOOK=$(ls -t "$EXPORTS"/karakulina_book_FINAL_stage3_*.json 2>/dev/null | head -1)
if [ -z "$CURRENT_BOOK" ]; then
    echo "WARN: Stage3 book not found, trying any FINAL..."
    CURRENT_BOOK=$(ls -t "$EXPORTS"/karakulina_book_FINAL_*.json 2>/dev/null | head -1)
fi
if [ -z "$CURRENT_BOOK" ]; then
    echo "ERROR: current_book не найден"
    exit 1
fi

echo "============================================"
echo "Phase B: content_addition (новое интервью Татьяны)"
echo "current_book: $CURRENT_BOOK"
echo "new_transcript: $NEW_TRANSCRIPT"
echo "fact_map: $FACT_MAP"
echo "============================================"

if [ ! -f "$NEW_TRANSCRIPT" ]; then
    echo "ERROR: Новый транскрипт не найден: $NEW_TRANSCRIPT"
    echo "Доступные транскрипты:"
    ls -la "$EXPORTS"/karakulina_*transcript*.txt 2>/dev/null || echo "  (нет)"
    exit 1
fi

# ── Phase B: Ghostwriter + Fact Checker ──────────────────────────────────────
echo ""
echo ">>> PHASE B: Ghostwriter content_addition + Fact Checker"
python3 -u scripts/test_stage2_phase_b.py \
    --current-book "$CURRENT_BOOK" \
    --new-transcript "$NEW_TRANSCRIPT" \
    --speaker-name "Татьяна Каракулина" \
    --speaker-relation "дочь" \
    --fact-map "$FACT_MAP" \
    --output-dir "$EXPORTS" \
    --prefix "$PREFIX" \
    --max-fc-iterations 2

# Находим финальный Phase B book
PHASE_B_BOOK=$(ls -t "$EXPORTS"/karakulina_book_FINAL_phase_b_*.json 2>/dev/null | head -1)
if [ -z "$PHASE_B_BOOK" ]; then
    echo "ERROR: Phase B не создал книгу"
    exit 1
fi
echo ""
echo ">>> Phase B готов: $PHASE_B_BOOK"

# ── Stage 3: Literary Editor + Proofreader ───────────────────────────────────
FC_REPORT=$(ls -t "$EXPORTS"/karakulina_phase_b_fc_report_*.json 2>/dev/null | head -1)

echo ""
echo ">>> STAGE 3: Literary Editor + Proofreader (на обогащённой книге)"
python3 -u scripts/test_stage3.py \
    --book-draft "$PHASE_B_BOOK" \
    --fc-warnings "$FC_REPORT" \
    --fact-map "$FACT_MAP" \
    --prefix "${PREFIX}_pb"

# Итоговые артефакты
echo ""
echo "============================================"
echo "Phase B + Stage3 complete. Артефакты:"
TODAY=$(date +%Y%m%d)
ls -la "$EXPORTS"/ | grep "$TODAY" | grep -E "karakulina_(phase_b|pb_book|pb_liteditor|pb_proofreader|book_FINAL_phase)" | sort | tail -30
echo "============================================"
