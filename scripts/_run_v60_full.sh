#!/bin/bash
# v60 — полный прогон Каракулиной (v60 sprint: Batch 1 + Batch 2 + Batch 2-fix + v60 sprint)
# RP-1 candidate: 11 задач v60 sprint реализованы
# Промпты: GW v2.21, LE v3.1, FC v2.13, CA v1.4
# Baseline для diff: v59

set -e
cd /opt/glava

echo "=== v60: git pull ==="
git fetch origin
git checkout feat/v60-sprint
git pull origin feat/v60-sprint

echo "=== v60: STAGE 1 (split-extract + known-episodes + prev-fact-map) ==="
# ОБЯЗАТЕЛЬНО: --known-episodes для task 041b (Класс 9)
V59_FM="collab/runs/karakulina_v59/karakulina_v59_fact_map_full_*.json"

python scripts/test_stage1_karakulina_full.py \
  --transcript1 collab/transcripts/01_karakulina_original_assemblyai_20260326.txt \
  --transcript2 collab/transcripts/02_karakulina_nikita_tatyana_interview.txt \
  --split-extract \
  --prev-fact-map $(ls -t $V59_FM | head -1) \
  --known-episodes collab/context/known_episodes_karakulina.md \
  --output-dir exports/karakulina_v60

echo "=== v60: STAGE 2 (GW v2.21 + CA v1.4 — verify в manifest) ==="
FM60=$(ls -t exports/karakulina_v60/karakulina_fact_map_*.json | grep -v enriched | grep -v TR1 | head -1)
echo "fact_map: $FM60"

python scripts/test_stage2_pipeline.py \
  --fact-map "$FM60" \
  --output-dir exports/stage2_v60 \
  --allow-fc-fail

# Verify GW v2.21 в manifest:
echo "--- Verify ghostwriter_version в manifest ---"
grep -h "ghostwriter_version" exports/stage2_v60/karakulina_stage2_run_manifest_*.json || echo "[WARN] ghostwriter_version не найден в manifest!"

echo "=== v60: STAGE 3 (все v60 фиксы активны) ==="
BOOK_FINAL=$(ls -t exports/stage2_v60/karakulina_book_FINAL_*.json 2>/dev/null | head -1)
BOOK_DRAFT=$(ls -t exports/stage2_v60/karakulina_book_draft_*.json 2>/dev/null | head -1)

if [ -n "$BOOK_FINAL" ]; then
  BOOK_IN="$BOOK_FINAL"
  echo "Stage 3 input: book_FINAL (FC passed)"
else
  BOOK_IN="$BOOK_DRAFT"
  echo "Stage 3 input: book_draft (FC failed — using --no-strict-gates)"
fi

python scripts/test_stage3.py \
  --book-draft "$BOOK_IN" \
  --fact-map "$FM60" \
  --output-dir exports/stage3_v60 \
  --prefix karakulina \
  --no-strict-gates

echo "=== v60: Gate1 full text + Contributors ==="
BOOK_FINAL_S3=$(ls -t exports/stage3_v60/karakulina_book_FINAL_stage3_*.json | head -1)
mkdir -p collab/runs/karakulina_v60

python scripts/build_gate1_full_text.py \
  --book-final "$BOOK_FINAL_S3" \
  --fact-map "$FM60" \
  --reports-dir exports/stage3_v60 \
  --prefix karakulina \
  --contributors collab/context/contributors_karakulina.json \
  --output collab/runs/karakulina_v60/karakulina_v60_text_FULL.md

echo "=== v60: Копируем ключевые отчёты в collab/runs/karakulina_v60/ ==="
cp exports/stage3_v60/karakulina_style_checks_*.json collab/runs/karakulina_v60/ 2>/dev/null || true
cp exports/stage3_v60/karakulina_chronology_check_*.json collab/runs/karakulina_v60/ 2>/dev/null || true
cp exports/stage3_v60/karakulina_temporal_place_naming_*.json collab/runs/karakulina_v60/ 2>/dev/null || true
cp exports/stage3_v60/karakulina_chapter_sections_anchors_*.json collab/runs/karakulina_v60/ 2>/dev/null || true
cp exports/stage3_v60/karakulina_pin_list_depth_*.json collab/runs/karakulina_v60/ 2>/dev/null || true
cp exports/stage3_v60/karakulina_relation_overrides_applied_*.json collab/runs/karakulina_v60/ 2>/dev/null || true

echo ""
echo "=== v60: VERIFIED-ON-RUN checklist ==="
echo "Запустить после завершения:"
echo ""
echo "1. [046b] style_checks.json: убедись что epilogue_stop_phrases.errors соответствует финальному тексту"
echo "   grep -c 'error' exports/stage3_v60/karakulina_style_checks_*.json"
echo ""
echo "2. [044c] bio_data.family: убедись что 'Баба Аня' отсутствует"
echo "   grep -i 'аня' exports/stage3_v60/karakulina_book_FINAL_stage3_*.json || echo 'OK - не найдено'"
echo ""
echo "3. [049b] manifest ghostwriter_version:"
echo "   python -c \"import json,glob; d=json.load(open(glob.glob('exports/stage2_v60/karakulina_stage2_run_manifest_*.json')[0])); print(d.get('notes',{}).get('ghostwriter_version'))\""
echo ""
echo "4. [043c] epilogue stop phrases v60:"
echo "   grep -i 'верила в идеалы\|не сломленная\|такой ушла\|сохранившая до конца' collab/runs/karakulina_v60/karakulina_v60_text_FULL.md || echo 'OK - чисто'"
echo ""
echo "5. [050b] pin_list_depth errors:"
echo "   python -c \"import json,glob; d=json.load(open(glob.glob('exports/stage3_v60/karakulina_pin_list_depth_*.json')[0])); print('errors:', d['errors_count'])\""
echo ""
echo "6. [040b] Сапон grep:"
echo "   grep -c 'Сапон' collab/runs/karakulina_v60/karakulina_v60_text_FULL.md || echo 'OK'"
echo ""
echo "7. [048b] chronology grandchild_before_inferred_birth:"
echo "   python -c \"import json,glob; d=json.load(open(glob.glob('exports/stage3_v60/karakulina_chronology_check_*.json')[0])); print([i for i in d['issues'] if 'grandchild' in i['type']])\""
echo ""
echo "8. [051] temporal place names (Калинин vs Тверь):"
echo "   grep -i 'калинин' collab/runs/karakulina_v60/karakulina_v60_text_FULL.md | head -5"
echo ""
echo "9. [052] Contributors section:"
echo "   grep 'Кто работал над этой Главой' collab/runs/karakulina_v60/karakulina_v60_text_FULL.md && echo 'OK'"
echo ""
echo "10. [045c] chapter_sections_anchors — Гостеприимство:"
echo "    grep 'Гостеприимство и кулинария' collab/runs/karakulina_v60/karakulina_v60_text_FULL.md && echo 'OK'"
echo ""
echo "=== v60: DONE ==="
ls -la collab/runs/karakulina_v60/
