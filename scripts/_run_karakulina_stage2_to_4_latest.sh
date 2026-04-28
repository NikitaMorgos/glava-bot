#!/usr/bin/env bash
set -euo pipefail

cd /opt/glava
. .venv/bin/activate

echo "[RUN] Stage2"
python scripts/test_stage2_pipeline.py \
  --fact-map /opt/glava/exports/test_fact_map_karakulina_v5.json \
  --transcript /opt/glava/exports/karakulina_cleaned_transcript.txt \
  --output-dir /opt/glava/exports

BOOK_DRAFT="$(python -c "from pathlib import Path; files=sorted(Path('/opt/glava/exports').glob('karakulina_book_FINAL_*.json'), key=lambda p: p.stat().st_mtime, reverse=True); print(files[0] if files else '')")"
FC_REPORT="$(python -c "from pathlib import Path; files=sorted(Path('/opt/glava/exports').glob('karakulina_fc_report_iter*_*.json'), key=lambda p: p.stat().st_mtime, reverse=True); print(files[0] if files else '')")"

if [[ -z "${BOOK_DRAFT}" || -z "${FC_REPORT}" ]]; then
  echo "[ERROR] Stage2 outputs not found"
  exit 1
fi

echo "[RUN] Stage3"
python scripts/test_stage3.py \
  --book-draft "${BOOK_DRAFT}" \
  --fc-warnings "${FC_REPORT}" \
  --prefix karakulina_full_latest

PR_REPORT="$(python -c "from pathlib import Path; files=sorted(Path('/opt/glava/exports').glob('karakulina_full_latest_proofreader_report_*.json'), key=lambda p: p.stat().st_mtime, reverse=True); print(files[0] if files else '')")"
if [[ -z "${PR_REPORT}" ]]; then
  echo "[ERROR] Proofreader report not found"
  exit 1
fi

echo "[RUN] Approve proofreader checkpoint"
python scripts/checkpoint_save.py save karakulina proofreader "${PR_REPORT}" --approve

echo "[RUN] Stage4 strict with cover"
python scripts/test_stage4_karakulina.py \
  --photos-dir /opt/glava/exports/karakulina_photos \
  --prefix karakulina_full_latest

echo "[DONE] Stage2-4 run completed"
