#!/usr/bin/env python3
"""Generates _resume3_karakulina_20260414.sh (Phase B + Stage4) on server."""
import os

script = (
    "#!/bin/bash\n"
    "set -euo pipefail\n"
    "source /opt/glava/.venv/bin/activate\n"
    "set -a; source /opt/glava/.env; set +a\n"
    "\n"
    'RUN_DIR="/opt/glava/exports/karakulina_full_20260414_062711"\n'
    'SCRIPTS="/opt/glava/scripts"\n'
    'EXPORTS="/opt/glava/exports"\n'
    'COLLAB="/opt/glava/collab/runs/karakulina_full_20260414_062711"\n'
    'TR2="/opt/glava/exports/karakulina_meeting_transcript_20260403.txt"\n'
    "\n"
    'FACT_MAP="$RUN_DIR/karakulina_fact_map_full_20260414_062712.json"\n'
    'BOOK_S3="/opt/glava/exports/karakulina_book_FINAL_stage3_20260414_120045.json"\n'
    "\n"
    'LOG="$RUN_DIR/run_resume3_pb_s4.log"\n'
    'mkdir -p "$COLLAB"\n'
    "\n"
    'echo "=== RESUME3 karakulina_full_20260414_062711 PhaseB->Stage4 ===" | tee -a "$LOG"\n'
    'echo "Started: $(date)" | tee -a "$LOG"\n'
    'echo "Stage3 book: $BOOK_S3" | tee -a "$LOG"\n'
    "\n"
    "# --- PHASE B ---\n"
    'echo "" | tee -a "$LOG"\n'
    'echo ">>> PHASE B (incremental FE + GW content_addition + FC)" | tee -a "$LOG"\n'
    "cd /opt/glava\n"
    'python "$SCRIPTS/test_stage2_phase_b.py" \\\n'
    '    --current-book "$BOOK_S3" \\\n'
    '    --fact-map "$FACT_MAP" \\\n'
    '    --new-transcript "$TR2" \\\n'
    '    --output-dir "$RUN_DIR" \\\n'
    "    --variant-b \\\n"
    '    2>&1 | tee -a "$LOG"\n'
    "\n"
    "# Find Phase B output\n"
    'BOOK_PB=$(ls -t "$RUN_DIR"/karakulina_book_FINAL_phase_b_*.json 2>/dev/null | head -1 || true)\n'
    'if [ -z "$BOOK_PB" ]; then\n'
    '    echo "ERROR: Phase B book not found!" | tee -a "$LOG"\n'
    '    exit 1\n'
    'fi\n'
    'echo "Phase B book: $BOOK_PB" | tee -a "$LOG"\n'
    "\n"
    "# --- CHECKPOINT fact_map ---\n"
    'echo "" | tee -a "$LOG"\n'
    'echo ">>> CHECKPOINT: fact_map" | tee -a "$LOG"\n'
    'python "$SCRIPTS/checkpoint_save.py" save karakulina fact_map "$FACT_MAP" 2>&1 | tee -a "$LOG" || true\n'
    'python "$SCRIPTS/checkpoint_save.py" approve karakulina fact_map --skip-regression 2>&1 | tee -a "$LOG" || true\n'
    "\n"
    "# --- CHECKPOINT proofreader ---\n"
    'echo "" | tee -a "$LOG"\n'
    'echo ">>> CHECKPOINT: proofreader" | tee -a "$LOG"\n'
    'python "$SCRIPTS/checkpoint_save.py" save karakulina proofreader "$BOOK_PB" 2>&1 | tee -a "$LOG" || true\n'
    'python "$SCRIPTS/checkpoint_save.py" approve karakulina proofreader --skip-regression 2>&1 | tee -a "$LOG" || true\n'
    "\n"
    "# --- STAGE 4 ---\n"
    'echo "" | tee -a "$LOG"\n'
    'echo ">>> STAGE 4 (layout + cover)" | tee -a "$LOG"\n'
    'python "$SCRIPTS/test_stage4_karakulina.py" 2>&1 | tee -a "$LOG"\n'
    "\n"
    "# --- COPY ARTIFACTS to collab ---\n"
    'echo "" | tee -a "$LOG"\n'
    'echo ">>> COPY ARTIFACTS to $COLLAB" | tee -a "$LOG"\n'
    'cp -v "$FACT_MAP" "$COLLAB/" 2>&1 | tee -a "$LOG" || true\n'
    'cp -v "$BOOK_S3" "$COLLAB/" 2>&1 | tee -a "$LOG" || true\n'
    'cp -v "$BOOK_PB" "$COLLAB/" 2>&1 | tee -a "$LOG" || true\n'
    'ls "$RUN_DIR"/*.pdf 2>/dev/null | while read f; do cp -v "$f" "$COLLAB/"; done 2>&1 | tee -a "$LOG" || true\n'
    'ls "$EXPORTS"/karakulina_*stage4*.pdf 2>/dev/null | tail -1 | while read f; do cp -v "$f" "$COLLAB/"; done 2>&1 | tee -a "$LOG" || true\n'
    "\n"
    'echo "" | tee -a "$LOG"\n'
    'echo "=== DONE: $(date) ===" | tee -a "$LOG"\n'
)

out_path = "/opt/glava/scripts/_resume3_karakulina_20260414.sh"
with open(out_path, "w", newline="\n") as f:
    f.write(script)
os.chmod(out_path, 0o755)
print(f"OK: {out_path} written ({len(script)} bytes)")
