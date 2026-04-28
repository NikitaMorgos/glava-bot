#!/usr/bin/env python3
"""Run on server: python3 /tmp/gen_resume.py — generates the resume bash script."""
import os

script = r"""#!/usr/bin/env bash
set -euo pipefail
GLAVA=/opt/glava
source $GLAVA/.venv/bin/activate
set -a; source $GLAVA/.env; set +a
cd $GLAVA
RUN=$GLAVA/exports/karakulina_full_20260414_062711
FM=$RUN/karakulina_fact_map_full_20260414_062712.json
TR2=$GLAVA/exports/karakulina_meeting_transcript_20260403.txt
PREFIX=karakulina_full_20260414_062711
LOG=$RUN/run_resume_s2_s4.log
exec > >(tee $LOG) 2>&1
echo "=== RESUME karakulina_full_20260414_062711 Stage2->Phase B->Stage4 ==="
echo "Started: $(date)"

echo ">>> STAGE 2 (--variant-b)"
python scripts/test_stage2_pipeline.py \
    --fact-map $FM \
    --output-dir $RUN \
    --skip-historian \
    --variant-b

BOOK_S2=$(ls -t $RUN/karakulina_book_FINAL_*.json 2>/dev/null | head -1)
[ -z "$BOOK_S2" ] && echo "[ERROR] stage2 book not found" && exit 1
echo "[OK] stage2: $(basename $BOOK_S2)"

echo ">>> STAGE 3 (--variant-b)"
python scripts/test_stage3.py \
    --book-draft $BOOK_S2 \
    --fact-map $FM \
    --variant-b

BOOK_S3=$(ls -t $GLAVA/exports/karakulina_book_FINAL_stage3_*.json 2>/dev/null | head -1)
[ -z "$BOOK_S3" ] && echo "[ERROR] stage3 book not found" && exit 1
cp $GLAVA/exports/karakulina_book_FINAL_stage3_*.json $RUN/ 2>/dev/null || true
cp $GLAVA/exports/karakulina_FINAL_stage3_*.txt $RUN/ 2>/dev/null || true
echo "[OK] stage3: $(basename $BOOK_S3)"

echo ">>> PHASE B (Incremental FE + GW + FC, --variant-b)"
python scripts/test_stage2_phase_b.py \
    --current-book $BOOK_S3 \
    --new-transcript $TR2 \
    --fact-map $FM \
    --output-dir $RUN \
    --variant-b

BOOK_PB=$(ls -t $RUN/karakulina_book_FINAL_phase_b_*.json 2>/dev/null | head -1)
[ -z "$BOOK_PB" ] && echo "[ERROR] phase_b book not found" && exit 1
FM_PB=$(ls -t $RUN/karakulina_fact_map_phase_b_*.json 2>/dev/null 2>/dev/null | head -1 || echo $FM)
echo "[OK] phase_b: $(basename $BOOK_PB)"
echo "[OK] fact_map for S4: $(basename $FM_PB)"

echo ">>> CHECKPOINTS"
python scripts/checkpoint_save.py save karakulina fact_map $FM_PB
python scripts/checkpoint_save.py approve karakulina fact_map
python scripts/checkpoint_save.py save karakulina proofreader $BOOK_PB
python scripts/checkpoint_save.py approve karakulina proofreader

echo ">>> STAGE 4"
PHOTOS=$GLAVA/exports/karakulina_photos
if [ -d "$PHOTOS" ] && [ -f "$PHOTOS/manifest.json" ]; then
    python scripts/test_stage4_karakulina.py --photos-dir $PHOTOS --prefix $PREFIX
else
    echo "[WARN] No photos at $PHOTOS"
    python scripts/test_stage4_karakulina.py --prefix $PREFIX
fi

echo ">>> COPY TO COLLAB"
CRUN=$GLAVA/collab/runs/$PREFIX
mkdir -p $CRUN
cp $FM_PB $BOOK_S2 $BOOK_S3 $BOOK_PB $CRUN/ 2>/dev/null || true
cp $RUN/karakulina_FINAL_*.txt $CRUN/ 2>/dev/null || true
cp $RUN/karakulina_*_run_manifest_*.json $CRUN/ 2>/dev/null || true
cp $GLAVA/exports/${PREFIX}_stage4_pdf_*.pdf $CRUN/ 2>/dev/null || true
cp $LOG $CRUN/ 2>/dev/null || true
echo "=== DONE $(date) ==="
"""

dst = "/opt/glava/scripts/_resume_karakulina_20260414.sh"
with open(dst, "w", newline="\n") as f:
    f.write(script)
os.chmod(dst, 0o755)
print(f"Written {dst}")
