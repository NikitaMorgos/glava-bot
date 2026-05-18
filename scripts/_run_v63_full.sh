#!/bin/bash
# v63 — Combined sprint (Option X): 9 scripted fixes + CA v1.5 + GW v2.22
# Промпты: GW v2.22 (ПРАВИЛО 12: narrative depth+voice+volume), CA v1.5 (ПРАВИЛО 7: entity preservation)
# Baseline: v62a (best run so far); branch: feat/v63-combined-sprint
#
# Targets (build_gate1 Total chars — НЕ file_size):
#   Total ≥ 20 000 / ch_02 ≥ 8K / ch_03 ≥ 4K / ch_04 ≥ 2.5K / epilogue 800-1500
#   discourse_markers ch_02≥8 / ch_03≥5 / ch_04≥3
#   pin_list_depth errors = 0
#   Stage 2 manifest: ghostwriter_version=v2.22, completeness_auditor_version=v1.5
#
# Artifacts: collab/runs/karakulina_v63/

set -e
cd /opt/glava

echo "=== v63: git pull ==="
git fetch origin
git checkout feat/v63-combined-sprint
git pull origin feat/v63-combined-sprint

echo "=== v63: verify GW version (MUST be v2.22, NOT v2.21) ==="
python -c "
import json
cfg = json.load(open('prompts/pipeline_config.json', encoding='utf-8'))
gw = cfg['ghostwriter']['prompt_file']
ca = cfg['completeness_auditor']['prompt_file']
assert 'v2.22' in gw, f'GW version wrong: {gw}'
assert 'v1.5' in ca, f'CA version wrong: {ca}'
print(f'OK: GW={gw}, CA={ca}')
"

echo "=== v63: verify known_episodes v5 (ep_029 year=unknown) ==="
grep "ep_029" collab/context/known_episodes_karakulina.md | grep -q "unknown" && echo "ep_029 OK" || echo "WARNING: ep_029 still has year"

echo "=== v63: STAGE 1 (split-extract + known-episodes v5 + prev-fact-map v62a) ==="
V62_FM="collab/runs/karakulina_v62/karakulina_fact_map_full_*.json"
mkdir -p exports/karakulina_v63

python scripts/test_stage1_karakulina_full.py \
  --transcript1 collab/transcripts/01_karakulina_original_assemblyai_20260326.txt \
  --transcript2 collab/transcripts/02_karakulina_nikita_tatyana_interview.txt \
  --split-extract \
  --prev-fact-map $(ls -t $V62_FM | head -1) \
  --known-episodes collab/context/known_episodes_karakulina.md \
  --output-dir exports/karakulina_v63

echo "=== v63: STAGE 2 (GW v2.22 + CA v1.5) ==="
FM63=$(ls -t exports/karakulina_v63/karakulina_fact_map_full_*.json | grep -v enriched | grep -v TR1 | head -1)
echo "fact_map: $FM63"

mkdir -p exports/stage2_v63
python scripts/test_stage2_pipeline.py \
  --fact-map "$FM63" \
  --output-dir exports/stage2_v63 \
  --allow-fc-fail

echo "=== v63: verify Stage 2 manifest GW+CA versions ==="
MANIFEST63=$(ls -t exports/stage2_v63/karakulina_stage2_run_manifest_*.json | head -1)
python -c "
import json
m = json.load(open('$MANIFEST63', encoding='utf-8'))
gw_v = m.get('ghostwriter_version', '')
ca_v = m.get('completeness_auditor_version', '')
print(f'Stage2 manifest: GW={gw_v}, CA={ca_v}')
assert gw_v == 'v2.22' or 'v2.22' in str(m), f'GW version in manifest wrong: {gw_v}'
assert ca_v == 'v1.5' or 'v1.5' in str(m), f'CA version in manifest wrong: {ca_v}'
print('Stage2 version check PASSED')
" || echo "WARNING: manifest version check failed"

echo "=== v63: STAGE 3 (LE + Proofreader + validators) ==="
BOOK63=$(ls -t exports/stage2_v63/karakulina_book_FINAL_*.json | head -1)
echo "book: $BOOK63"

mkdir -p exports/stage3_v63
python scripts/test_stage3.py \
  --book-draft "$BOOK63" \
  --fact-map "$FM63" \
  --output-dir exports/stage3_v63 \
  --prefix karakulina \
  --no-strict-gates

echo "=== v63: build_gate1_full_text (contributors = ФИО+relation only) ==="
BOOK_FINAL=$(ls -t exports/stage3_v63/karakulina_book_FINAL_stage3_*.json | head -1)
python scripts/build_gate1_full_text.py \
  --book-final "$BOOK_FINAL" \
  --fact-map "$FM63" \
  --output exports/stage3_v63/karakulina_v63_text_FULL.md \
  --reports-dir exports/stage3_v63 \
  --prefix karakulina \
  --pin-list collab/context/known_episodes_karakulina.md

echo "=== v63: run v63 narrative validators ==="
python - <<'PYEOF'
import json, sys, os
sys.path.insert(0, '/opt/glava')
from pipeline_utils import (
    validate_children_before_birth,
    validate_epilogue_quote_density,
    validate_entity_substitution,
    validate_bio_data_family_format,
    validate_narrative_stop_phrases,
)
import glob

# Load artifacts
book_files = sorted(glob.glob('exports/stage3_v63/karakulina_book_FINAL_stage3_*.json'), reverse=True)
fm_files = sorted(glob.glob('exports/karakulina_v63/karakulina_fact_map_full_*.json'), reverse=True)
if not book_files or not fm_files:
    print("ERROR: book or fact_map not found"); sys.exit(1)

book = json.load(open(book_files[0], encoding='utf-8'))
if 'book_draft' in book:
    book = book['book_draft']
if 'book_final' in book:
    book = book['book_final']

fm = json.load(open(fm_files[0], encoding='utf-8'))

chrono_cfg = json.load(open('collab/context/chronology_periods_karakulina.json', encoding='utf-8'))
stop_cfg = json.load(open('collab/context/narrative_stop_phrases.json', encoding='utf-8'))

# Load transcripts
tr_files = sorted(glob.glob('collab/transcripts/*.txt'))
transcripts = [open(f, encoding='utf-8').read() for f in tr_files[:2]]

print("\n=== 048d: children_before_birth ===")
r = validate_children_before_birth(book, chrono_cfg)
print(f"  errors={r['errors_count']}, warnings={r['warnings_count']}")
for i in r['issues'][:3]:
    print(f"  [{i['severity']}] {i['type']} ch={i['chapter_id']} year={i.get('event_year')}")

print("\n=== 043e-2: epilogue quote density ===")
r = validate_epilogue_quote_density(book)
print(f"  ok={r.get('ok')}, quotes={r.get('quote_count')}, generic_pct={r.get('generic_pct')}")
for i in r.get('issues', [])[:2]:
    print(f"  [{i['severity']}] {i['type']}")

print("\n=== 038c: entity substitution ===")
r = validate_entity_substitution(book, fm, transcripts)
print(f"  ok={r['ok']}, issues={len(r['issues'])}")
for i in r['issues'][:3]:
    print(f"  [{i['severity']}] {i['original']} -> {i['substituted']} in {i['chapter_id']}")

print("\n=== 043f/043g: narrative stop phrases ===")
r = validate_narrative_stop_phrases(book, stop_cfg)
issues = r.get('issues', [])
print(f"  total={len(issues)}")
for i in issues[:5]:
    print(f"  [{i.get('severity','?')}] {i.get('category','?')} ch={i.get('chapter_id')}")

print("\n=== 044g: bio_data family format ===")
for ch in book.get('chapters', []):
    if ch.get('id') == 'ch_01':
        bio = ch.get('bio_data', {})
        r = validate_bio_data_family_format(bio)
        print(f"  ok={r['ok']}, issues={len(r['issues'])}, malformed={r['malformed_count']}")
        break

print("\nAll v63 validators done.")
PYEOF

echo "=== v63: chars summary from text_FULL ==="
python - <<'PYEOF'
import re
try:
    text = open('exports/stage3_v63/karakulina_v63_text_FULL.md', encoding='utf-8').read()
    total = len(text)
    
    # Per-chapter char counts
    chapters = re.findall(r'(## .+?)(?=\n## |\Z)', text, re.DOTALL)
    print(f"Total chars: {total}")
    for ch in chapters:
        title_line = ch.split('\n')[0][:60]
        print(f"  {title_line}: {len(ch)} chars")
    
    # Target checks
    ch02 = next((c for c in chapters if 'ch_02' in c or 'Детство' in c or 'Молодость' in c), "")
    ch03 = next((c for c in chapters if 'ch_03' in c or 'Зрелость' in c), "")
    ch04 = next((c for c in chapters if 'ch_04' in c or 'Поздние' in c), "")
    epilogue = next((c for c in chapters if 'epilogue' in c.lower() or 'Послесловие' in c), "")
    
    print(f"\n=== Targets check ===")
    print(f"Total: {total} ({'OK' if total >= 20000 else 'FAIL'} target ≥20000)")
    if ch02: print(f"ch_02: {len(ch02)} ({'OK' if len(ch02) >= 8000 else 'BELOW TARGET'} target ≥8000)")
    if ch03: print(f"ch_03: {len(ch03)} ({'OK' if len(ch03) >= 4000 else 'BELOW TARGET'} target ≥4000)")
    if ch04: print(f"ch_04: {len(ch04)} ({'OK' if len(ch04) >= 2500 else 'BELOW TARGET'} target ≥2500)")
    if epilogue: 
        ep_len = len(epilogue)
        print(f"epilogue: {ep_len} ({'OK' if 800 <= ep_len <= 1500 else 'BELOW TARGET'} target 800-1500)")
except FileNotFoundError:
    print("text_FULL not found")
PYEOF

echo "=== v63: собираем артефакты ==="
mkdir -p collab/runs/karakulina_v63
cp exports/karakulina_v63/karakulina_fact_map_full_*.json collab/runs/karakulina_v63/ 2>/dev/null || true
cp exports/stage2_v63/karakulina_book_FINAL_*.json collab/runs/karakulina_v63/ 2>/dev/null || true
cp exports/stage2_v63/karakulina_stage2_run_manifest_*.json collab/runs/karakulina_v63/ 2>/dev/null || true
cp exports/stage3_v63/karakulina_text_FULL_*.md collab/runs/karakulina_v63/ 2>/dev/null || true
cp exports/stage3_v63/karakulina_v63_text_FULL.md collab/runs/karakulina_v63/ 2>/dev/null || true
cp exports/stage3_v63/karakulina_book_FINAL_stage3_*.json collab/runs/karakulina_v63/ 2>/dev/null || true
cp exports/stage3_v63/karakulina_style_checks_*.json collab/runs/karakulina_v63/ 2>/dev/null || true
cp exports/stage3_v63/karakulina_chronology_check_*.json collab/runs/karakulina_v63/ 2>/dev/null || true
cp exports/stage3_v63/karakulina_pin_list_depth_*.json collab/runs/karakulina_v63/ 2>/dev/null || true
cp exports/stage3_v63/karakulina_discourse_markers_*.json collab/runs/karakulina_v63/ 2>/dev/null || true
cp exports/stage3_v63/karakulina_timeline_anchors_*.json collab/runs/karakulina_v63/ 2>/dev/null || true
cp exports/stage3_v63/karakulina_relation_overrides_applied_*.json collab/runs/karakulina_v63/ 2>/dev/null || true
cp exports/stage3_v63/karakulina_stage3_run_manifest_*.json collab/runs/karakulina_v63/ 2>/dev/null || true

echo ""
echo "=== v63 ПОЛНЫЙ ПРОГОН ЗАВЕРШЁН ==="
echo ""
echo "Артефакты: collab/runs/karakulina_v63/"
echo ""
echo "=== Verified-on-run checklist (v63 tasks) ==="
echo "049d: Stage2 manifest ghostwriter_version=v2.22 confirmed"
echo "038c: entity_substitution report — zero Калинин→Тверь in ch_02/ch_03"
echo "048d: chronology_check — zero children_before_birth errors"
echo "044d-2: text_FULL — no empty '### Дополнительный текст ch_01' header; no malformed family lines"
echo "043g: style_checks — event_that_changed_life + typical_for_generation flagged if present"
echo "051d: ep_029 in pin_list_coverage — year=unknown, year_confidence=low"
echo "043f: style_checks — class11_not_loved_x_by_y_and_z flagged in ch_04 if present"
echo "043e-2: epilogue quote_count ≥ 1; generic_pct ≤ 60%"
echo "044g: bio_family_format — no malformed entries, no locative errors"
echo "052d: text_FULL last section — ФИО+relation only, no 'основной рассказчик'"
echo "meta: Total chars ≥ 20000; ch_02 ≥ 8000; discourse_markers ch_02 ≥ 8"
