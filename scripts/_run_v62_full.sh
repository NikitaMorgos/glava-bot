#!/bin/bash
# v62a — 10 scripted fixes + 1 meta (NO GW prompt change)
# Промпты: GW v2.20 (без изменений!), LE v3.1, FC v2.13, CA v1.4
# Baseline для diff: v59 (best version) и v61 (last run)
# Ветка: feat/v62a-pointed-fixes (off v61 commit a8809aa)

set -e
cd /opt/glava

echo "=== v62a: git pull ==="
git fetch origin
git checkout feat/v62a-pointed-fixes
git pull origin feat/v62a-pointed-fixes

echo "=== v62a: verify GW version (MUST be v2.20, NOT v2.21) ==="
grep "prompt_file" prompts/pipeline_config.json | grep ghostwriter
# Expected: v2.20

echo "=== v62a: STAGE 1 (split-extract + known-episodes v4 + prev-fact-map v61) ==="
V61_FM="collab/runs/karakulina_v61/karakulina_fact_map_full_*.json"
mkdir -p exports/karakulina_v62

python scripts/test_stage1_karakulina_full.py \
  --transcript1 collab/transcripts/01_karakulina_original_assemblyai_20260326.txt \
  --transcript2 collab/transcripts/02_karakulina_nikita_tatyana_interview.txt \
  --split-extract \
  --prev-fact-map $(ls -t $V61_FM | head -1) \
  --known-episodes collab/context/known_episodes_karakulina.md \
  --output-dir exports/karakulina_v62

echo "=== v62a: STAGE 2 (GW v2.20 + CA v1.4) ==="
FM62=$(ls -t exports/karakulina_v62/karakulina_fact_map_full_*.json | grep -v enriched | grep -v TR1 | head -1)
echo "fact_map: $FM62"

mkdir -p exports/stage2_v62
python scripts/test_stage2_pipeline.py \
  --fact-map "$FM62" \
  --output-dir exports/stage2_v62 \
  --allow-fc-fail

echo "=== v62a: STAGE 3 (LE + Proofreader + validators) ==="
BOOK62=$(ls -t exports/stage2_v62/karakulina_book_FINAL_*.json | head -1)
echo "book: $BOOK62"

mkdir -p exports/stage3_v62
python scripts/test_stage3.py \
  --book-draft "$BOOK62" \
  --fact-map "$FM62" \
  --output-dir exports/stage3_v62 \
  --prefix karakulina \
  --no-strict-gates

echo "=== v62a: build_gate1_full_text (с contributors из pin-list v4) ==="
BOOK_FINAL=$(ls -t exports/stage3_v62/karakulina_book_FINAL_stage3_*.json | head -1)
python scripts/build_gate1_full_text.py \
  --book-final "$BOOK_FINAL" \
  --fact-map "$FM62" \
  --output exports/stage3_v62/karakulina_v62_text_FULL.md \
  --reports-dir exports/stage3_v62 \
  --prefix karakulina \
  --pin-list collab/context/known_episodes_karakulina.md

echo "=== v62a: собираем артефакты ==="
mkdir -p collab/runs/karakulina_v62
cp exports/karakulina_v62/karakulina_fact_map_full_*.json collab/runs/karakulina_v62/ 2>/dev/null || true
cp exports/stage2_v62/karakulina_book_FINAL_*.json collab/runs/karakulina_v62/ 2>/dev/null || true
cp exports/stage2_v62/karakulina_stage2_run_manifest_*.json collab/runs/karakulina_v62/ 2>/dev/null || true
cp exports/stage3_v62/karakulina_text_FULL_*.md collab/runs/karakulina_v62/ 2>/dev/null || true
cp exports/stage3_v62/karakulina_v62_text_FULL.md collab/runs/karakulina_v62/ 2>/dev/null || true
cp exports/stage3_v62/karakulina_book_FINAL_stage3_*.json collab/runs/karakulina_v62/ 2>/dev/null || true
cp exports/stage3_v62/karakulina_style_checks_*.json collab/runs/karakulina_v62/ 2>/dev/null || true
cp exports/stage3_v62/karakulina_chronology_check_*.json collab/runs/karakulina_v62/ 2>/dev/null || true
cp exports/stage3_v62/karakulina_pin_list_depth_*.json collab/runs/karakulina_v62/ 2>/dev/null || true
cp exports/stage3_v62/karakulina_discourse_markers_*.json collab/runs/karakulina_v62/ 2>/dev/null || true
cp exports/stage3_v62/karakulina_timeline_anchors_*.json collab/runs/karakulina_v62/ 2>/dev/null || true
cp exports/stage3_v62/karakulina_relation_overrides_applied_*.json collab/runs/karakulina_v62/ 2>/dev/null || true
cp exports/stage3_v62/karakulina_stage3_run_manifest_*.json collab/runs/karakulina_v62/ 2>/dev/null || true

echo ""
echo "=== v62a ПОЛНЫЙ ПРОГОН ЗАВЕРШЁН ==="
echo ""
echo "Артефакты: collab/runs/karakulina_v62/"
echo ""
echo "=== Verified-on-run checklist (v62a tasks) ==="
echo "044d: text_FULL начало — без ?: ? строк; нет дубля Основные даты жизни"
echo "044e: bio_data.family содержит Бабушка: Марфа с note мать отца Валентины"
echo "044f: Внук: Никита (сын Татьяны), Внучка: Даша (дочь Татьяны) — notes present"
echo "049c: discourse_markers.json ch_02 >= 5 (вместо false 0)"
echo "051c: Дочь: Татьяна (родилась в 1956 году в Калинине) — не Тверь"
echo "048c: chronology_check.json: 1973 + внучка Даша flagged error"
echo "052c: text_FULL в конце имеет Кто работал над этой Главой с 4 именами"
echo "043d: style_checks: определило всю её жизнь flagged + помогая женщинам flagged"
echo "045e: timeline_anchors.json: widowhood (1978-1996) found as separate period"
echo "043e: anti_facts_check.json: af_001 салаты+варенье checked"
echo "meta: text_FULL сводка — Total chars >= 20000"
