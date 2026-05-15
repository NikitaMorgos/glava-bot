#!/bin/bash
# Сбор артефактов v54 в collab/runs/karakulina_v54/ для PR
# Запускать ПОСЛЕ завершения _run_v54_full.sh
set -e
cd /opt/glava

PREFIX=karakulina_v54
DEST=collab/runs/karakulina_v54

mkdir -p "$DEST"

echo "=== Сбор артефактов v54 ==="

# fact_map_full (из Stage 1)
for f in exports/karakulina_v54/karakulina_fact_map_full_*.json; do
  [ -f "$f" ] && cp -v "$f" "$DEST/${PREFIX}_fact_map_full_$(basename $f | sed 's/karakulina_fact_map_full_//')" || true
done

# stage1 manifest
for f in exports/karakulina_v54/karakulina_stage1_full_run_manifest_*.json; do
  [ -f "$f" ] && cp -v "$f" "$DEST/" || true
done

# book_FINAL_stage2 (переименованный)
for f in exports/stage2_v54/${PREFIX}_book_FINAL_stage2_*.json; do
  [ -f "$f" ] && cp -v "$f" "$DEST/" || true
done

# scope_merge
for f in exports/stage2_v54/karakulina_scope_merge_iter*.json; do
  [ -f "$f" ] && cp -v "$f" "$DEST/${PREFIX}_scope_merge_$(basename $f | sed 's/karakulina_scope_merge_//')" || true
done

# stage2 manifest
for f in exports/stage2_v54/karakulina_stage2_run_manifest_*.json; do
  [ -f "$f" ] && cp -v "$f" "$DEST/${PREFIX}_stage2_run_manifest_$(basename $f | sed 's/karakulina_stage2_run_manifest_//')" || true
done

# book_FINAL_stage3
for f in exports/stage3_v54/${PREFIX}_book_FINAL_stage3_*.json; do
  [ -f "$f" ] && cp -v "$f" "$DEST/" || true
done

# liteditor_report
for f in exports/stage3_v54/${PREFIX}_liteditor_report_*.json; do
  [ -f "$f" ] && cp -v "$f" "$DEST/" || true
done

# le_structural_preservation (новый артефакт Этапа 1)
for f in exports/stage3_v54/${PREFIX}_le_structural_preservation_*.json; do
  [ -f "$f" ] && cp -v "$f" "$DEST/" || true
done

# stage3 manifest
for f in exports/stage3_v54/${PREFIX}_stage3_run_manifest_*.json; do
  [ -f "$f" ] && cp -v "$f" "$DEST/" || true
done

# text_FULL.md (уже там)
[ -f "$DEST/${PREFIX}_text_FULL.md" ] && echo "FOUND: text_FULL.md" || echo "WARN: text_FULL.md not found"

echo ""
echo "=== Итог ==="
ls -lh "$DEST/"
echo ""
echo "=== le_structural_preservation summary ==="
PRES=$(ls -t "$DEST"/${PREFIX}_le_structural_preservation_*.json 2>/dev/null | head -1)
if [ -n "$PRES" ]; then
  python3 -c "
import json
d = json.load(open('$PRES', encoding='utf-8'))
print('chapters_with_restored_fields:', d.get('chapters_with_restored_fields', []))
print('total_fields_restored:', d.get('total_fields_restored', 0))
"
fi

echo "=== READY FOR PR ==="
