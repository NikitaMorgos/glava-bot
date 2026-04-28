#!/usr/bin/env bash
# =============================================================================
# Полный прогон Каракулиной: Stage1 → Stage2 → Stage3 → Phase B
# Промпты: FactExtractor v3.3, Ghostwriter v2.7, FactChecker v2.1,
#          LiteraryEditor v3, Proofreader v1
# Phase B: вплести интервью Татьяны ПОСЛЕ Stage3
# =============================================================================
set -euo pipefail

GLAVA_DIR="/opt/glava"
VENV="$GLAVA_DIR/.venv"
EXPORTS="$GLAVA_DIR/exports"
COLLAB="$GLAVA_DIR/collab"
SCRIPTS="$GLAVA_DIR/scripts"

TS=$(date +%Y%m%d_%H%M%S)
RUN_TAG="karakulina_full_${TS}"
RUN_DIR="$EXPORTS/$RUN_TAG"
mkdir -p "$RUN_DIR"

LOG="$RUN_DIR/run.log"
exec > >(tee "$LOG") 2>&1

echo "=============================================="
echo " GLAVA Full Run — Каракулина"
echo " Tag:  $RUN_TAG"
echo " Time: $(date)"
echo "=============================================="

# ── Окружение ──────────────────────────────────────────────────────────────
source "$VENV/bin/activate"
set -a; source "$GLAVA_DIR/.env"; set +a
cd "$GLAVA_DIR"

# ── Транскрипты ────────────────────────────────────────────────────────────
TR1="$EXPORTS/transcripts/karakulina_valentina_interview_assemblyai.txt"
TR2="$EXPORTS/karakulina_meeting_transcript_20260403.txt"

if [ ! -f "$TR1" ]; then
    TR1=$(find "$EXPORTS" -name "*karakulina*assemblyai*.txt" 2>/dev/null | head -1)
fi
if [ ! -f "$TR2" ]; then
    TR2=$(find "$EXPORTS" -name "*karakulina*meeting_transcript*.txt" 2>/dev/null | head -1)
fi

echo "[TRANSCRIPTS]"
echo "  TR1: $TR1 ($(wc -c < "$TR1") bytes)"
echo "  TR2: $TR2 ($(wc -c < "$TR2") bytes)"

# ── STAGE 1: Cleaner + Fact Extractor ─────────────────────────────────────
echo ""
echo ">>> STAGE 1: Cleaner + Fact Extractor v3.3"
python "$SCRIPTS/test_stage1_karakulina_full.py" \
    --transcript1 "$TR1" \
    --output-dir "$RUN_DIR"

FACT_MAP=$(ls -t "$RUN_DIR"/karakulina_fact_map_full_*.json 2>/dev/null | head -1)
if [ -z "$FACT_MAP" ]; then echo "[ERROR] fact_map не найден в $RUN_DIR"; exit 1; fi
echo "[OK] fact_map: $FACT_MAP"

# ── STAGE 2: Ghostwriter v2.7 + Fact Checker v2.1 ─────────────────────────
echo ""
echo ">>> STAGE 2: Ghostwriter v2.7 + Fact Checker v2.1"
python "$SCRIPTS/test_stage2_pipeline.py" \
    --fact-map "$FACT_MAP" \
    --output-dir "$RUN_DIR" \
    --skip-historian \
    --variant-b

BOOK_S2=$(ls -t "$RUN_DIR"/karakulina_book_FINAL_*.json 2>/dev/null | head -1)
if [ -z "$BOOK_S2" ]; then echo "[ERROR] Stage2 книга не найдена в $RUN_DIR"; exit 1; fi
echo "[OK] stage2 book: $BOOK_S2"

# ── STAGE 3: Literary Editor v3 + Proofreader v1 ───────────────────────────
# Важно: test_stage3.py пишет результат в ROOT/exports/, аргумент --book-draft
echo ""
echo ">>> STAGE 3: Literary Editor v3 + Proofreader v1"
S3_START=$(date +%Y%m%d_%H%M%S)
python "$SCRIPTS/test_stage3.py" \
    --book-draft "$BOOK_S2" \
    --fact-map "$FACT_MAP" \
    --variant-b

# Stage3 пишет в /opt/glava/exports/ — найти свежий файл (появился после S3_START)
BOOK_S3=$(ls -t "$EXPORTS"/karakulina_book_FINAL_stage3_*.json 2>/dev/null | head -1)
if [ -z "$BOOK_S3" ]; then echo "[ERROR] Stage3 книга не найдена в $EXPORTS"; exit 1; fi
echo "[OK] stage3 book: $BOOK_S3"

# Скопировать Stage3 артефакты в RUN_DIR
cp "$EXPORTS"/karakulina_book_FINAL_stage3_*.json "$RUN_DIR/" 2>/dev/null || true
cp "$EXPORTS"/karakulina_FINAL_stage3_*.txt "$RUN_DIR/" 2>/dev/null || true

# ── PHASE B: вплести интервью Татьяны ─────────────────────────────────────
echo ""
echo ">>> PHASE B: вплетение интервью Татьяны (TR2)"
python "$SCRIPTS/test_stage2_phase_b.py" \
    --current-book "$BOOK_S3" \
    --new-transcript "$TR2" \
    --fact-map "$FACT_MAP" \
    --output-dir "$RUN_DIR"

BOOK_PB=$(ls -t "$RUN_DIR"/karakulina_book_FINAL_phase_b_*.json 2>/dev/null | head -1)
if [ -z "$BOOK_PB" ]; then echo "[ERROR] Phase B книга не найдена в $RUN_DIR"; exit 1; fi
echo "[OK] phase_b book: $BOOK_PB"

# ── Копирую все артефакты в collab ─────────────────────────────────────────
echo ""
echo ">>> Копирую артефакты в collab/runs/$RUN_TAG"
COLLAB_RUN="$COLLAB/runs/$RUN_TAG"
mkdir -p "$COLLAB_RUN"

cp "$FACT_MAP"  "$COLLAB_RUN/"
cp "$BOOK_S2"   "$COLLAB_RUN/"
cp "$BOOK_S3"   "$COLLAB_RUN/"
cp "$BOOK_PB"   "$COLLAB_RUN/"
cp "$RUN_DIR"/*.txt "$COLLAB_RUN/" 2>/dev/null || true
cp "$LOG"       "$COLLAB_RUN/run.log"

# Краткий README для collab
python3 - <<PYEOF
import json
from pathlib import Path

run_tag = "$RUN_TAG"
run_dir = Path("$RUN_DIR")
collab_run = Path("$COLLAB_RUN")

# Статистика Phase B
pb_path = Path("$BOOK_PB")
data = json.loads(pb_path.read_text(encoding="utf-8"))
book = data.get("book_final") or data
chapters = book.get("chapters", [])

total_chars = 0
lines = [f"# Прогон: {run_tag}", "",
         "## Конфигурация",
         "| Этап | Промпт |",
         "|------|--------|",
         "| Cleaner | 01_cleaner_v1.md |",
         "| Fact Extractor | 02_fact_extractor_v3.3.md |",
         "| Ghostwriter | 03_ghostwriter_v2.6.md (v2.7 внутри) |",
         "| Fact Checker | 04_fact_checker_v2.md (v2.1 внутри) |",
         "| Literary Editor | 05_literary_editor_v3.md |",
         "| Proofreader | 06_proofreader_v1.md |", "",
         "## Входные данные",
         "- TR1 (assemblyai, март 2026): karakulina_valentina_interview_assemblyai.txt",
         "- TR2 (интервью Татьяны, апрель 2026): karakulina_meeting_transcript_20260403.txt", "",
         "## Структура (Phase B — финальный текст)",
         "| Глава | Название |",
         "|-------|---------|"]

for ch in chapters:
    cid = ch.get("id") or ch.get("chapter_id", "?")
    title = ch.get("title", "")
    content = ch.get("content") or ""
    chars = len(content)
    total_chars += chars
    lines.append(f"| {cid} | {title} ({chars:,} симв) |")

lines += ["", f"**Всего текста:** {total_chars:,} символов", "",
          "## Артефакты",
          "- fact_map_full → Stage1 (оба транскрипта)",
          "- book_FINAL → Stage2 (Ghostwriter v2.7)",
          "- book_FINAL_stage3 → Stage3 (LiteraryEditor + Proofreader)",
          "- book_FINAL_phase_b → Phase B (добавлен материал Татьяны)", "",
          "## Статус",
          "✅ Готово к ревью Даши и Клода"]

readme_path = collab_run / "README.md"
readme_path.write_text("\n".join(lines), encoding="utf-8")
print(f"[README] {readme_path}")
PYEOF

echo ""
echo "=============================================="
echo " ПРОГОН ЗАВЕРШЁН: $RUN_TAG"
echo " Артефакты: $COLLAB_RUN"
echo "=============================================="
echo "COLLAB_RUN=$COLLAB_RUN"
echo "$RUN_DIR" > "$EXPORTS/karakulina_last_run_dir.txt"
echo "{\"run_tag\":\"$RUN_TAG\",\"run_dir\":\"$RUN_DIR\",\"collab_run\":\"$COLLAB_RUN\"}" > "$RUN_DIR/run_meta.json"
