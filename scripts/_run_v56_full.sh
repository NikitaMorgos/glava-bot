#!/bin/bash
# v56: split-extract (TR1→PhaseA, TR2→PhaseB) + CA v1.2 pin-list от v55 fact_map
# Цель: проверить что pin-list events CA v1.2 восстанавливает огурцы/счётчик/Нинвану/шарлотку
# Промпты: GW v2.18 + LE v3.1 + CA v1.2 (без изменений vs v55, только +pin-list)
# НЕТ Stage 4
set -e
cd /opt/glava
source .venv/bin/activate
set -a; source /opt/glava/.env; set +a

PREFIX=karakulina_v56
TR1=collab/transcripts/01_karakulina_original_assemblyai_20260326.txt
TR2=collab/transcripts/02_karakulina_nikita_tatyana_interview.txt
PREV_FM=collab/runs/karakulina_v55/karakulina_v55_fact_map_full_20260515_122058.json
LOG=/opt/glava/exports/run_v56_full.log

mkdir -p exports/karakulina_v56 exports/stage2_v56 exports/stage3_v56 collab/runs/karakulina_v56
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
" | tee -a "$LOG"

echo "" | tee -a "$LOG"
python3 -c "
import json
fm = json.load(open('$PREV_FM', encoding='utf-8'))
tl = fm.get('timeline', [])
ps = fm.get('persons', [])
print(f'prev-fact-map v55: {len(tl)} events, {len(ps)} persons (pin-list source)')
" | tee -a "$LOG"

ls -lh "$TR1" "$TR2" | tee -a "$LOG"
ls -lh "$PREV_FM" | tee -a "$LOG"

# ── STAGE 1 (split-extract + pin-list от v55) ─────────────────────────────────
echo "" | tee -a "$LOG"
echo "=== STAGE 1 (split-extract + --prev-fact-map v55) ===" | tee -a "$LOG"
python3 -u scripts/test_stage1_karakulina_full.py \
  --transcript1 "$TR1" \
  --transcript2 "$TR2" \
  --split-extract \
  --prev-fact-map "$PREV_FM" \
  --output-dir exports/karakulina_v56 \
  2>&1 | tee -a "$LOG"

FACTMAP=$(ls -t exports/karakulina_v56/karakulina_fact_map_full_*.json 2>/dev/null | head -1)
AUDIT=$(ls -t exports/karakulina_v56/karakulina_completeness_audit_*.json 2>/dev/null | head -1)
FM_TR1=$(ls -t exports/karakulina_v56/karakulina_fact_map_TR1_*.json 2>/dev/null | head -1)
if [ -z "$FACTMAP" ]; then echo 'ERROR: fact_map_full not found'; exit 1; fi
echo "FACTMAP: $FACTMAP" | tee -a "$LOG"
echo "AUDIT:   $AUDIT" | tee -a "$LOG"

# CA auto_enrich summary (pin-list results)
echo "" | tee -a "$LOG"
echo "=== CA v1.2 PIN-LIST РЕЗУЛЬТАТЫ ===" | tee -a "$LOG"
python3 -c "
import json
if not '$AUDIT':
    print('audit not found')
else:
    a = json.load(open('$AUDIT', encoding='utf-8'))
    ae = a.get('auto_enrich', {})
    ae_tl = ae.get('timeline', [])
    ae_ps = ae.get('persons', [])
    pin_tl = [e for e in ae_tl if e.get('was_in_pin_list') or e.get('pin_list_source')]
    pin_ps = [p for p in ae_ps if p.get('was_in_pin_list') or p.get('pin_list_source')]
    print(f'auto_enrich.timeline: {len(ae_tl)} events ({len(pin_tl)} was_in_pin_list)')
    print(f'auto_enrich.persons:  {len(ae_ps)} persons ({len(pin_ps)} was_in_pin_list)')
    for e in ae_tl:
        pin = e.get('was_in_pin_list', False)
        print(f'  [{\"PIN\" if pin else \"NEW\"}] {e.get(\"title\",\"\")[:60]}')
    lop = a.get('log_only_gaps', {})
    me = lop.get('missing_events', [])
    pin_me = [e for e in me if e.get('was_in_pin_list')]
    print(f'log_only_gaps.missing_events: {len(me)} ({len(pin_me)} was_in_pin_list=true)')
    for e in pin_me[:5]:
        print(f'  [MISSING-PIN] {e.get(\"keyword\",\"\")} — {e.get(\"reason_low_confidence\",\"\")[:60]}')
" | tee -a "$LOG"

# Маркеры в fact_map_full
echo "" | tee -a "$LOG"
echo "=== МАРКЕРЫ В fact_map_full (task 035) ===" | tee -a "$LOG"
python3 -c "
import json
fm = json.load(open('$FACTMAP', encoding='utf-8'))
timeline = fm.get('timeline', [])
persons = fm.get('persons', [])
print(f'fact_map_full: {len(timeline)} events, {len(persons)} persons')
markers = {
    'огурцы': ['огурц', 'молдав'],
    'счётчик': ['счётчик', 'счетчик'],
    'Нинвана': ['нинван'],
    'шарлотка': ['шарлотк'],
}
for name, kws in markers.items():
    found = [e for e in timeline if any(kw.lower() in (e.get('title','') + ' ' + e.get('description','')).lower() for kw in kws)]
    if found:
        for fe in found:
            print(f'  [{fe.get(\"id\")}] {fe.get(\"title\",\"\")[:50]}')
    else:
        print(f'  {name}: ОТСУТСТВУЕТ')
" | tee -a "$LOG"

# ── STAGE 2 ───────────────────────────────────────────────────────────────────
echo "" | tee -a "$LOG"
echo "=== STAGE 2 ===" | tee -a "$LOG"
python3 -u scripts/test_stage2_pipeline.py \
  --fact-map "$FACTMAP" \
  --output-dir exports/stage2_v56 \
  2>&1 | tee -a "$LOG"

BOOK_S2_RAW=$(ls -t exports/stage2_v56/karakulina_book_FINAL_*.json 2>/dev/null | head -1)
if [ -z "$BOOK_S2_RAW" ]; then echo 'ERROR: book_FINAL S2 not found'; exit 1; fi
TS_S2=$(basename "$BOOK_S2_RAW" | sed 's/karakulina_book_FINAL_//' | sed 's/.json//')
BOOK_S2="${BOOK_S2_RAW%karakulina_book_FINAL_*}${PREFIX}_book_FINAL_stage2_${TS_S2}.json"
cp "$BOOK_S2_RAW" "$BOOK_S2"
echo "BOOK_S2: $BOOK_S2" | tee -a "$LOG"
FC_REPORT=$(ls -t exports/stage2_v56/karakulina_fc_report_iter*.json 2>/dev/null | head -1)

# ── STAGE 3 ───────────────────────────────────────────────────────────────────
echo "" | tee -a "$LOG"
echo "=== STAGE 3 (LE v3.1 + preserve) ===" | tee -a "$LOG"
if [ -n "$FC_REPORT" ]; then
  python3 -u scripts/test_stage3.py \
    --book-draft "$BOOK_S2" \
    --fact-map "$FACTMAP" \
    --fc-warnings "$FC_REPORT" \
    --output-dir exports/stage3_v56 \
    --prefix "${PREFIX}" \
    2>&1 | tee -a "$LOG"
else
  python3 -u scripts/test_stage3.py \
    --book-draft "$BOOK_S2" \
    --fact-map "$FACTMAP" \
    --output-dir exports/stage3_v56 \
    --prefix "${PREFIX}" \
    2>&1 | tee -a "$LOG"
fi

BOOK_S3=$(ls -t exports/stage3_v56/${PREFIX}_book_FINAL_stage3_*.json 2>/dev/null | head -1)
if [ -z "$BOOK_S3" ]; then echo 'ERROR: book_FINAL_stage3 not found'; exit 1; fi
echo "BOOK_S3: $BOOK_S3" | tee -a "$LOG"

# ── LE STRUCTURAL PRESERVATION ────────────────────────────────────────────────
echo "" | tee -a "$LOG"
echo "=== LE STRUCTURAL PRESERVATION ===" | tee -a "$LOG"
PRES=$(ls -t exports/stage3_v56/${PREFIX}_le_structural_preservation_*.json 2>/dev/null | head -1)
if [ -n "$PRES" ]; then
  python3 -c "
import json
d = json.load(open('$PRES', encoding='utf-8'))
print('chapters_with_restored_fields:', d.get('chapters_with_restored_fields'))
for r in d.get('restorations', []):
    print('  ', r.get('chapter_id'), ':', r.get('restored_fields'))
" | tee -a "$LOG"
fi

# ── BUILD GATE1 FULL TEXT ─────────────────────────────────────────────────────
echo "" | tee -a "$LOG"
echo "=== BUILD GATE1 FULL TEXT ===" | tee -a "$LOG"
python3 scripts/build_gate1_full_text.py \
  --book-final "$BOOK_S3" \
  --fact-map "$FACTMAP" \
  --output collab/runs/karakulina_v56/karakulina_v56_text_FULL.md \
  2>&1 | tee -a "$LOG"

echo "" | tee -a "$LOG"
echo "=== ARTIFACTS SUMMARY ===" | tee -a "$LOG"
ls -lh exports/karakulina_v56/ | tee -a "$LOG"
ls -lh exports/stage2_v56/ | tee -a "$LOG"
ls -lh exports/stage3_v56/ | tee -a "$LOG"

echo "" | tee -a "$LOG"
echo "=== DONE: v56 ===" | tee -a "$LOG"
echo "TEXT: collab/runs/karakulina_v56/karakulina_v56_text_FULL.md" | tee -a "$LOG"
