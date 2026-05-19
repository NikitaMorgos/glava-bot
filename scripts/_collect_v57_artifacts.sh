#!/bin/bash
# Сбор артефактов v57 в collab/runs/karakulina_v57/
set -e
cd /opt/glava

DEST="collab/runs/karakulina_v57"
mkdir -p "$DEST"

echo "=== Collecting v57 artifacts ==="

# Stage 1 artifacts
for f in exports/karakulina_v57/karakulina_fact_map_TR1_*.json \
          exports/karakulina_v57/karakulina_fact_map_full_*.json \
          exports/karakulina_v57/karakulina_fact_map_enriched_*.json \
          exports/karakulina_v57/karakulina_completeness_audit_*.json \
          exports/karakulina_v57/karakulina_topo_normalize_factmap_*.json \
          exports/karakulina_v57/karakulina_stage1_full_run_manifest_*.json; do
  [ -f "$f" ] && cp "$f" "$DEST/$(basename "$f" | sed 's/karakulina_/karakulina_v57_/')" && echo "  + $(basename $f)"
done

# Stage 2 artifacts (FC reports)
for f in exports/stage2_v57/karakulina_fc_report_iter*.json \
          exports/stage2_v57/karakulina_stage2_run_manifest_*.json; do
  [ -f "$f" ] && cp "$f" "$DEST/$(basename "$f" | sed 's/karakulina_/karakulina_v57_/')" && echo "  + $(basename $f)"
done

# Stage 3 artifacts
for f in exports/stage3_v57/karakulina_book_FINAL_stage3_*.json \
          exports/stage3_v57/karakulina_liteditor_report_*.json \
          exports/stage3_v57/karakulina_le_structural_preservation_*.json \
          exports/stage3_v57/karakulina_bio_data_integrity_*.json \
          exports/stage3_v57/karakulina_topo_normalize_report_*.json \
          exports/stage3_v57/karakulina_stage3_run_manifest_*.json; do
  [ -f "$f" ] && cp "$f" "$DEST/$(basename "$f" | sed 's/karakulina_/karakulina_v57_/')" && echo "  + $(basename $f)"
done

echo "=== v57 artifacts collected to $DEST ==="
ls -la "$DEST/"
