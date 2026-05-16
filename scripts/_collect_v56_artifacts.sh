#!/bin/bash
# Сбор артефактов v56 в collab/runs/karakulina_v56/
cd /opt/glava
mkdir -p collab/runs/karakulina_v56

TS1=20260515_154819
TS2=20260515_160346
TS3=20260516_061657
PREFIX=karakulina_v56

echo "=== Сбор артефактов v56 ==="

# Stage 1
cp exports/karakulina_v56/karakulina_fact_map_full_${TS1}.json \
   collab/runs/karakulina_v56/${PREFIX}_fact_map_full_${TS1}.json

cp exports/karakulina_v56/karakulina_fact_map_TR1_${TS1}.json \
   collab/runs/karakulina_v56/${PREFIX}_fact_map_TR1_${TS1}.json

cp exports/karakulina_v56/karakulina_completeness_audit_${TS1}.json \
   collab/runs/karakulina_v56/${PREFIX}_completeness_audit_${TS1}.json

cp exports/karakulina_v56/karakulina_stage1_full_run_manifest_${TS1}.json \
   collab/runs/karakulina_v56/${PREFIX}_stage1_run_manifest_${TS1}.json

# Stage 2 (FC fail iter3 — диагностика)
cp exports/stage2_v56/karakulina_fc_report_iter3_${TS2}.json \
   collab/runs/karakulina_v56/${PREFIX}_fc_report_iter3_${TS2}.json || true

cp exports/stage2_v56/karakulina_book_draft_v4_merged_${TS2}.json \
   collab/runs/karakulina_v56/${PREFIX}_book_draft_v4_merged_${TS2}.json

cp exports/stage2_v56/karakulina_stage2_run_manifest_${TS2}.json \
   collab/runs/karakulina_v56/${PREFIX}_stage2_run_manifest_${TS2}.json || true

# Stage 3
cp exports/stage3_v56/${PREFIX}_book_FINAL_stage3_${TS3}.json \
   collab/runs/karakulina_v56/ || true

cp exports/stage3_v56/${PREFIX}_liteditor_report_${TS3}.json \
   collab/runs/karakulina_v56/ || true

cp exports/stage3_v56/${PREFIX}_le_structural_preservation_${TS3}.json \
   collab/runs/karakulina_v56/ || true

cp exports/stage3_v56/${PREFIX}_stage3_run_manifest_${TS3}.json \
   collab/runs/karakulina_v56/ || true

# text_FULL.md уже в collab/runs/karakulina_v56/
ls -lh collab/runs/karakulina_v56/
echo "=== READY FOR PR ==="
