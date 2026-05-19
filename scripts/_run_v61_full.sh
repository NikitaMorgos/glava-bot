#!/bin/bash
# v61 — Hybrid rollback: branch off v59, cherry-pick 8 scripted fixes
# Промпты: GW v2.20 (как v59 — стабильный baseline), LE v3.1, FC v2.13, CA v1.4
# Baseline для diff: v59 (НЕ v60 — v60 регрессировал)
# Выполненные cherry-picks: 044c 046b 049b 050b 040b 043c 048b 046c

set -e
cd /opt/glava

echo "=== v61: git pull ==="
git fetch origin
git checkout feat/v61-hybrid-rollback
git pull origin feat/v61-hybrid-rollback

echo "=== v61: verify GW version ==="
grep "prompt_file" prompts/pipeline_config.json | grep ghostwriter
# Ожидается: v2.20 (НЕ v2.21)

echo "=== v61: STAGE 1 (split-extract + known-episodes + prev-fact-map) ==="
V60_FM="collab/runs/karakulina_v60/karakulina_fact_map_full_*.json"
mkdir -p exports/karakulina_v61

python scripts/test_stage1_karakulina_full.py \
  --transcript1 collab/transcripts/01_karakulina_original_assemblyai_20260326.txt \
  --transcript2 collab/transcripts/02_karakulina_nikita_tatyana_interview.txt \
  --split-extract \
  --prev-fact-map $(ls -t $V60_FM | head -1) \
  --known-episodes collab/context/known_episodes_karakulina.md \
  --output-dir exports/karakulina_v61

echo "=== v61: STAGE 2 (GW v2.20 + CA v1.4 — verify v2.20 в manifest) ==="
FM61=$(ls -t exports/karakulina_v61/karakulina_fact_map_full_*.json | grep -v enriched | grep -v TR1 | head -1)
echo "fact_map: $FM61"

mkdir -p exports/stage2_v61
python scripts/test_stage2_pipeline.py \
  --fact-map "$FM61" \
  --output-dir exports/stage2_v61 \
  --allow-fc-fail

echo "=== v61: STAGE 3 (LE + Proofreader + validators) ==="
BOOK61=$(ls -t exports/stage2_v61/karakulina_book_FINAL_*.json | head -1)
echo "book: $BOOK61"

mkdir -p exports/stage3_v61
python scripts/test_stage3.py \
  --book-draft "$BOOK61" \
  --fact-map "$FM61" \
  --output-dir exports/stage3_v61 \
  --prefix karakulina \
  --no-strict-gates

echo "=== v61: собираем артефакты ==="
mkdir -p collab/runs/karakulina_v61
cp exports/karakulina_v61/karakulina_fact_map_full_*.json collab/runs/karakulina_v61/ 2>/dev/null || true
cp exports/stage2_v61/karakulina_book_FINAL_*.json collab/runs/karakulina_v61/ 2>/dev/null || true
cp exports/stage2_v61/karakulina_stage2_run_manifest_*.json collab/runs/karakulina_v61/ 2>/dev/null || true
cp exports/stage3_v61/karakulina_text_FULL_*.md collab/runs/karakulina_v61/ 2>/dev/null || true
cp exports/stage3_v61/karakulina_book_FINAL_stage3_*.json collab/runs/karakulina_v61/ 2>/dev/null || true
cp exports/stage3_v61/karakulina_style_checks_*.json collab/runs/karakulina_v61/ 2>/dev/null || true
cp exports/stage3_v61/karakulina_chronology_check_*.json collab/runs/karakulina_v61/ 2>/dev/null || true
cp exports/stage3_v61/karakulina_pin_list_depth_*.json collab/runs/karakulina_v61/ 2>/dev/null || true
cp exports/stage3_v61/karakulina_relation_overrides_applied_*.json collab/runs/karakulina_v61/ 2>/dev/null || true
cp exports/stage3_v61/karakulina_stage3_run_manifest_*.json collab/runs/karakulina_v61/ 2>/dev/null || true

echo ""
echo "=== v61 ПОЛНЫЙ ПРОГОН ЗАВЕРШЁН ==="
echo ""
echo "Артефакты: collab/runs/karakulina_v61/"
echo ""
echo "=== Verified-on-run checklist (проверить вручную) ==="
echo "044c: bio_data.family — баба Аня НЕТ, тётя Маша НЕТ"
echo "046b: style_checks на ФИНАЛЬНОМ тексте (после auto_rewrite, не до)"
echo "049b: stage2_run_manifest notes: ghostwriter_version: v2.20 (НЕ v2.21!)"
echo "050b: pin_list_depth scope только narrative ch_02-04, epilogue excluded"
echo "040b: grep по «Сапон» в text_FULL → 0; есть Сафронова/Сафронове"
echo "043c: epilogue stop phrases ≤1 error (vs v59)"
echo "046c: grep по «путь от» в text_FULL → 0 hits после auto_rewrite"
echo "048b: chronology_check — grandchild bound если triggered"
echo ""
echo "Content quality (v59 baseline):"
echo "  ✅ Власьево / Воскресенская церковь"
echo "  ✅ «Разные отцы у В/П»"
echo "  ✅ Детский сад № 95"
echo "  ✅ Тётя Маня в bio_data.family"
echo "  ✅ Французская бабушка с бабой Аней (контекст ch_03)"
echo "  ✅ Огурцы развёрнутый эпизод"
