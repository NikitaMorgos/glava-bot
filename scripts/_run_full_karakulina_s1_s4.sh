#!/usr/bin/env bash
# =============================================================================
# Каракулина: Stage1 → Stage2 → Stage3 → Phase B → чекпоинты → Stage4 (вёрстка)
# После текста: save+approve fact_map и proofreader (Phase B JSON), затем test_stage4_karakulina.py
# =============================================================================
set -euo pipefail

GLAVA_DIR="/opt/glava"
VENV="$GLAVA_DIR/.venv"
EXPORTS="$GLAVA_DIR/exports"
SCRIPTS="$GLAVA_DIR/scripts"

source "$VENV/bin/activate"
set -a; source "$GLAVA_DIR/.env"; set +a
cd "$GLAVA_DIR"

LOG="$EXPORTS/karakulina_full_s1_s4_$(date +%Y%m%d_%H%M%S).log"

echo "=============================================="
echo " GLAVA Full + Stage4 — Каракулина"
echo " Started: $(date)"
echo " Лог чекпоинтов/Stage4: $LOG"
echo " (Stage1–3+Phase B пишут в RUN_DIR/run.log внутри прогона)"
echo "=============================================="

bash "$SCRIPTS/_run_full_karakulina_s1_s3.sh"

RUN_DIR=$(cat "$EXPORTS/karakulina_last_run_dir.txt")
echo ""
echo ">>> RUN_DIR from meta: $RUN_DIR"

FACT_MAP=$(ls -t "$RUN_DIR"/karakulina_fact_map_phase_b_*.json 2>/dev/null | head -1)
if [ -z "$FACT_MAP" ]; then
  FACT_MAP=$(ls -t "$RUN_DIR"/karakulina_fact_map_full_*.json 2>/dev/null | head -1)
fi
BOOK_PB=$(ls -t "$RUN_DIR"/karakulina_book_FINAL_phase_b_*.json 2>/dev/null | head -1)

if [ -z "$FACT_MAP" ] || [ -z "$BOOK_PB" ]; then
  echo "[ERROR] Не найдены fact_map или Phase B книга в $RUN_DIR"
  exit 1
fi

echo "[OK] fact_map: $FACT_MAP"
echo "[OK] phase_b book (proofreader checkpoint): $BOOK_PB"

echo ""
echo ">>> Чекпоинты: fact_map → approve → proofreader → approve"
{
  python "$SCRIPTS/checkpoint_save.py" save karakulina fact_map "$FACT_MAP"
  python "$SCRIPTS/checkpoint_save.py" approve karakulina fact_map

  python "$SCRIPTS/checkpoint_save.py" save karakulina proofreader "$BOOK_PB"
  python "$SCRIPTS/checkpoint_save.py" approve karakulina proofreader

  RUN_TAG=$(basename "$RUN_DIR")
  PREFIX="karakulina_${RUN_TAG}"

  PHOTOS="$EXPORTS/karakulina_photos"
  echo ""
  echo ">>> Stage4 (prefix=$PREFIX)"
  if [ -d "$PHOTOS" ] && [ -f "$PHOTOS/manifest.json" ]; then
    python "$SCRIPTS/test_stage4_karakulina.py" --photos-dir "$PHOTOS" --prefix "$PREFIX"
  else
    echo "[WARN] Нет $PHOTOS/manifest.json — Stage4 без фото (text-only)"
    python "$SCRIPTS/test_stage4_karakulina.py" --prefix "$PREFIX"
  fi

  echo ""
  echo "=============================================="
  echo " ГОТОВО: текст + Phase B + Stage4"
  echo " RUN_DIR=$RUN_DIR"
  echo " LOG=$LOG"
  echo "=============================================="
} 2>&1 | tee "$LOG"
