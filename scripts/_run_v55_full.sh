#!/bin/bash
# v55: Stage 1 split-extract (TR1→Phase A, TR2→Phase B) → Stage 2 → Stage 3
# Задача 035: защита от потери TR2-уникальных эпизодов (огурцы, счётчик, Нинвана)
# Активные промпты: GW v2.18 + LE v3.1 + CA v1.2 (pin-list events)
# НЕТ Stage 4 — по решению Никиты
set -e
cd /opt/glava
source .venv/bin/activate
set -a; source /opt/glava/.env; set +a

PREFIX=karakulina_v55
TR1=collab/transcripts/01_karakulina_original_assemblyai_20260326.txt
TR2=collab/transcripts/02_karakulina_nikita_tatyana_interview.txt
LOG=/opt/glava/exports/run_v55_full.log

mkdir -p exports/karakulina_v55 exports/stage2_v55 exports/stage3_v55 collab/runs/karakulina_v55
echo '' > "$LOG"

# ── SANITY CHECK ──────────────────────────────────────────────────────────────
echo "=== SANITY CHECK ===" | tee -a "$LOG"
git log -1 --oneline | tee -a "$LOG"
python3 -c "
import json, sys
sys.path.insert(0, '/opt/glava')
from pipeline_utils import preserve_chapter_structural_fields, merge_fact_maps
cfg = json.load(open('prompts/pipeline_config.json', encoding='utf-8'))
print('GW prompt:', cfg['ghostwriter']['prompt_file'])
print('LE prompt:', cfg['literary_editor']['prompt_file'])
print('CA prompt:', cfg['completeness_auditor']['prompt_file'])
print('FC prompt:', cfg['fact_checker']['prompt_file'])
print('preserve_chapter_structural_fields: OK')
print('merge_fact_maps: OK')
" | tee -a "$LOG"

echo "" | tee -a "$LOG"
ls -lh "$TR1" "$TR2" | tee -a "$LOG"

# ── STAGE 1 (split-extract: Phase A → Phase B) ────────────────────────────────
echo "" | tee -a "$LOG"
echo "=== STAGE 1 (split-extract: TR1→PhaseA, TR2→PhaseB) ===" | tee -a "$LOG"
python3 -u scripts/test_stage1_karakulina_full.py \
  --transcript1 "$TR1" \
  --transcript2 "$TR2" \
  --split-extract \
  --output-dir exports/karakulina_v55 \
  2>&1 | tee -a "$LOG"

FACTMAP=$(ls -t exports/karakulina_v55/karakulina_fact_map_full_*.json 2>/dev/null | head -1)
if [ -z "$FACTMAP" ]; then echo 'ERROR: fact_map_full not found'; exit 1; fi
echo "FACTMAP: $FACTMAP" | tee -a "$LOG"

# Быстрая проверка ключевых эпизодов
echo "" | tee -a "$LOG"
echo "=== ЭПИЗОДЫ-МАРКЕРЫ (task 035 regression check) ===" | tee -a "$LOG"
python3 -c "
import json
fm = json.load(open('$FACTMAP', encoding='utf-8'))
timeline = fm.get('timeline', [])
persons = fm.get('persons', [])
print(f'timeline: {len(timeline)} events, persons: {len(persons)}')

markers = {
    'огурцы': ['огурц', 'молдави'],
    'счётчик': ['счётчик', '1977'],
    'Нинвана': ['нинван', 'полсачев'],
    'шарлотка': ['шарлотк'],
}
for name, kws in markers.items():
    found = any(
        any(kw.lower() in (e.get('title','') + ' ' + e.get('description','')).lower() for kw in kws)
        for e in timeline
    )
    print(f'  {name}: {\"✅ НАЙДЕН\" if found else \"❌ ОТСУТСТВУЕТ\"}')
" | tee -a "$LOG"

# ── STAGE 2 ───────────────────────────────────────────────────────────────────
echo "" | tee -a "$LOG"
echo "=== STAGE 2 ===" | tee -a "$LOG"
python3 -u scripts/test_stage2_pipeline.py \
  --fact-map "$FACTMAP" \
  --output-dir exports/stage2_v55 \
  2>&1 | tee -a "$LOG"

BOOK_S2_RAW=$(ls -t exports/stage2_v55/karakulina_book_FINAL_*.json 2>/dev/null | head -1)
if [ -z "$BOOK_S2_RAW" ]; then echo 'ERROR: book_FINAL S2 not found'; exit 1; fi

# Переименовываем Stage 2 book с версионным префиксом
TS_S2=$(basename "$BOOK_S2_RAW" | sed 's/karakulina_book_FINAL_//' | sed 's/.json//')
BOOK_S2="${BOOK_S2_RAW%karakulina_book_FINAL_*}${PREFIX}_book_FINAL_stage2_${TS_S2}.json"
cp "$BOOK_S2_RAW" "$BOOK_S2"
echo "BOOK_S2: $BOOK_S2" | tee -a "$LOG"

FC_REPORT=$(ls -t exports/stage2_v55/karakulina_fc_report_iter*.json 2>/dev/null | head -1)
echo "scope_merge:" | tee -a "$LOG"
ls -t exports/stage2_v55/karakulina_scope_merge_iter*.json 2>/dev/null | tee -a "$LOG"

# ── STAGE 3 (LE v3.1 + preserve_chapter_structural_fields) ───────────────────
echo "" | tee -a "$LOG"
echo "=== STAGE 3 (LE v3.1 + preserve) ===" | tee -a "$LOG"
if [ -n "$FC_REPORT" ]; then
  python3 -u scripts/test_stage3.py \
    --book-draft "$BOOK_S2" \
    --fact-map "$FACTMAP" \
    --fc-warnings "$FC_REPORT" \
    --output-dir exports/stage3_v55 \
    --prefix "${PREFIX}" \
    2>&1 | tee -a "$LOG"
else
  python3 -u scripts/test_stage3.py \
    --book-draft "$BOOK_S2" \
    --fact-map "$FACTMAP" \
    --output-dir exports/stage3_v55 \
    --prefix "${PREFIX}" \
    2>&1 | tee -a "$LOG"
fi

BOOK_S3=$(ls -t exports/stage3_v55/${PREFIX}_book_FINAL_stage3_*.json 2>/dev/null | head -1)
if [ -z "$BOOK_S3" ]; then echo 'ERROR: book_FINAL_stage3 not found'; exit 1; fi
echo "BOOK_S3: $BOOK_S3" | tee -a "$LOG"

# ── LE STRUCTURAL PRESERVATION ────────────────────────────────────────────────
echo "" | tee -a "$LOG"
echo "=== LE STRUCTURAL PRESERVATION ===" | tee -a "$LOG"
PRES=$(ls -t exports/stage3_v55/${PREFIX}_le_structural_preservation_*.json 2>/dev/null | head -1)
if [ -n "$PRES" ]; then
  python3 -c "
import json
d = json.load(open('$PRES', encoding='utf-8'))
print('chapters_with_restored_fields:', d.get('chapters_with_restored_fields', []))
restorations = d.get('restorations', [])
for r in restorations:
    print('  ', r.get('chapter_id'), ':', r.get('restored_fields'))
" | tee -a "$LOG"
fi

# ── TR2-ЭПИЗОДЫ В BOOK_FINAL_STAGE3 ─────────────────────────────────────────
echo "" | tee -a "$LOG"
echo "=== TR2-ЭПИЗОДЫ В BOOK_FINAL_STAGE3 (task 035 primary check) ===" | tee -a "$LOG"
python3 -c "
import json
book = json.load(open('$BOOK_S3', encoding='utf-8'))
chapters = book.get('book_final', {}).get('chapters', book.get('chapters', []))
full_text = ' '.join(
    ch.get('content', '') for ch in chapters
).lower()

checks = [
    ('Огурцы Молдавия 1990', ['огурц', 'молдав']),
    ('Счётчик 1977', ['счётчик']),
    ('Нинвана Полсачева', ['нинван']),
    ('Шарлотка', ['шарлотк']),
    ('выковыривал (task 036)', ['выковыривал']),
    ('зарубиться (task 036)', ['зарубиться']),
    ('болью отозвалось (СТОП)', ['болью отозвалось']),
    ('трагически (СТОП)', ['трагически']),
]
for name, kws in checks:
    found = any(kw in full_text for kw in kws)
    verdict = '✅' if found else '❌'
    # СТОП-фразы — инвертируем
    if 'СТОП' in name:
        verdict = '❌ FOUND (BAD)' if found else '✅ OK (absent)'
    print(f'  {verdict} {name}')
" | tee -a "$LOG"

# ── BUILD GATE1 FULL TEXT ─────────────────────────────────────────────────────
echo "" | tee -a "$LOG"
echo "=== BUILD GATE1 FULL TEXT ===" | tee -a "$LOG"
python3 scripts/build_gate1_full_text.py \
  --book-final "$BOOK_S3" \
  --fact-map "$FACTMAP" \
  --output collab/runs/karakulina_v55/karakulina_v55_text_FULL.md \
  2>&1 | tee -a "$LOG"

echo "" | tee -a "$LOG"
echo "=== ARTIFACTS SUMMARY ===" | tee -a "$LOG"
ls -lh exports/karakulina_v55/ | tee -a "$LOG"
ls -lh exports/stage2_v55/ | tee -a "$LOG"
ls -lh exports/stage3_v55/ | tee -a "$LOG"

echo "" | tee -a "$LOG"
echo "=== DONE: v55 ===" | tee -a "$LOG"
echo "TEXT: collab/runs/karakulina_v55/karakulina_v55_text_FULL.md" | tee -a "$LOG"
