#!/usr/bin/env bash
set -euo pipefail

cd /opt/glava
. .venv/bin/activate

TS="$(date +%Y%m%d_%H%M%S)"
PREFIX="karakulina_strict_control_${TS}"
FACT_MAP_PATH="/opt/glava/exports/${PREFIX}_fact_map_input.json"

python3 - <<PY
import json
from pathlib import Path
cp = Path("/opt/glava/checkpoints/karakulina/fact_map.json")
if not cp.exists():
    raise SystemExit("fact_map checkpoint missing")
data = json.loads(cp.read_text(encoding="utf-8"))
content = data.get("content", {})
out = Path("${FACT_MAP_PATH}")
out.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"[INPUT] fact_map materialized: {out}")
PY

python -u scripts/test_stage2_pipeline.py \
  --fact-map "${FACT_MAP_PATH}" \
  --transcript /opt/glava/exports/transcripts/karakulina_valentina_interview_assemblyai.txt \
  --output-dir /opt/glava/exports \
  --skip-historian \
  --skip-historian-pass2

BOOK_DRAFT="$(
python3 - <<PY
from pathlib import Path
candidates = list(Path("/opt/glava/exports").glob("karakulina_book_FINAL_*.json"))
if not candidates:
    raise SystemExit("no Stage2 final book found")
print(max(candidates, key=lambda p: p.stat().st_mtime))
PY
)"
echo "[INPUT] stage3 book_draft: ${BOOK_DRAFT}"

python -u scripts/test_stage3.py \
  --book-draft "${BOOK_DRAFT}" \
  --prefix "${PREFIX}"

PR_PATH="$(
python3 - <<PY
from pathlib import Path
candidates = list(Path("/opt/glava/exports").glob("${PREFIX}_proofreader_report_*.json"))
if not candidates:
    raise SystemExit("no proofreader report found")
print(max(candidates, key=lambda p: p.stat().st_mtime))
PY
)"
echo "[INPUT] proofreader report for checkpoint: ${PR_PATH}"

python -u scripts/checkpoint_save.py save karakulina proofreader "${PR_PATH}" --approve

python -u scripts/test_stage4_karakulina.py \
  --photos-dir /opt/glava/exports/karakulina_photos \
  --prefix "${PREFIX}"

echo "STRICT_RUN_PREFIX=${PREFIX}"
