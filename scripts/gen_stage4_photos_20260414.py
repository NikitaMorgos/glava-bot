#!/usr/bin/env python3
"""Generates _stage4_with_photos_20260414.sh on server."""
import os

script = (
    "#!/bin/bash\n"
    "set -euo pipefail\n"
    "source /opt/glava/.venv/bin/activate\n"
    "set -a; source /opt/glava/.env; set +a\n"
    "\n"
    'SCRIPTS="/opt/glava/scripts"\n'
    'EXPORTS="/opt/glava/exports"\n'
    'COLLAB="/opt/glava/collab/runs/karakulina_full_20260414_062711"\n'
    'PHOTOS="/opt/glava/exports/karakulina_photos"\n'
    'LOG="$EXPORTS/stage4_photos_20260414.log"\n'
    'mkdir -p "$COLLAB"\n'
    "\n"
    'echo "=== STAGE4 with photos ===" | tee "$LOG"\n'
    'echo "Started: $(date)" | tee -a "$LOG"\n'
    "\n"
    "cd /opt/glava\n"
    'python "$SCRIPTS/test_stage4_karakulina.py" \\\n'
    '    --photos-dir "$PHOTOS" \\\n'
    '    2>&1 | tee -a "$LOG"\n'
    "\n"
    "# Find final PDF\n"
    'PDF=$(ls -t "$EXPORTS"/karakulina_stage4_pdf_iter*.pdf 2>/dev/null | head -1 || true)\n'
    'echo "Final PDF: $PDF" | tee -a "$LOG"\n'
    "\n"
    "# Copy to collab\n"
    'if [ -n "$PDF" ]; then\n'
    '    cp -v "$PDF" "$COLLAB/karakulina_FINAL_with_photos_20260414.pdf" | tee -a "$LOG"\n'
    'fi\n'
    "\n"
    'echo "=== DONE: $(date) ===" | tee -a "$LOG"\n'
)

out_path = "/opt/glava/scripts/_stage4_with_photos_20260414.sh"
with open(out_path, "w", newline="\n") as f:
    f.write(script)
os.chmod(out_path, 0o755)
print(f"OK: {out_path} written ({len(script)} bytes)")
