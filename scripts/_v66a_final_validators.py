#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v66a final validators on stage3 output."""
import json, sys, os, glob, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding='utf-8')

from pipeline_utils import (
    validate_chronological_consistency,
    validate_narrative_truism,
    validate_narrative_stop_phrases,
    validate_personal_historical_voice,
    validate_historical_notes_distribution,
    validate_descendants_in_early_context,
    validate_cross_paragraph_duplication,
    validate_required_episodes_coverage,
    validate_bio_data_family_format,
    parse_pin_list_from_markdown,
    _count_inline_historical_notes,
)

STAGE3_DIR = ROOT / 'exports' / 'stage3_v66a'
FM_DIR = ROOT / 'exports' / 'karakulina_v66a'

s3_files = sorted(glob.glob(str(STAGE3_DIR / 'karakulina_book_FINAL_stage3_*.json')), reverse=True)
fm_files = sorted(glob.glob(str(FM_DIR / 'karakulina_fact_map_full_*.json')), reverse=True)
if not s3_files:
    print('ERROR: no stage3 book'); sys.exit(1)

book_raw = json.load(open(s3_files[0], encoding='utf-8'))
book = book_raw.get('book_draft') or book_raw.get('book_final') or book_raw
fm = json.load(open(fm_files[0], encoding='utf-8'))

pin_list = parse_pin_list_from_markdown(str(ROOT / 'collab/context/known_episodes_karakulina.md'))
pin_episodes = pin_list.get('episodes', []) + pin_list.get('bytovye', [])
chapters = book.get('chapters', [])
full_text = ' '.join((ch.get('content') or '') for ch in chapters)

def load_cfg(name):
    p = ROOT / 'collab' / 'context' / name
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}

chrono_cfg = load_cfg('chronology_check_config.json')
dup_cfg = load_cfg('cross_paragraph_duplication_config.json')
hist_cfg = load_cfg('historical_notes_distribution_config.json')
nsp_cfg = load_cfg('narrative_stop_phrases.json')

results = {}
print(f'\n[INPUT] Stage3 book: {Path(s3_files[0]).name}')
print('\n=== v66a final validators (post-Stage3) ===\n')

print('[A] Chronology:')
r = validate_chronological_consistency(book, fm, chrono_cfg)
results['chronology'] = r
print(f'  errors={r["errors_count"]}, warnings={r["warnings_count"]}')

print('[B] Narrative truism Class 17:')
r = validate_narrative_truism(book)
results['narrative_truism'] = r
print(f'  errors={r["errors_count"]}, warnings={r["warnings_count"]}')

print('[C] Stop phrases Class 1/11:')
r = validate_narrative_stop_phrases(book, nsp_cfg)
results['stop_phrases'] = r
print(f'  errors={r["errors_count"]}, warnings={r["warnings_count"]}')
for i in r.get('issues', [])[:3]:
    print(f'  [{i.get("severity")}] {i.get("category")} ch={i.get("chapter_id")}: {str(i.get("snippet",""))[:60]}')

print('[D] Personal historical voice:')
r = validate_personal_historical_voice(book)
results['personal_historical_voice'] = r
print(f'  errors={r["errors_count"]}, warnings={r["warnings_count"]} markers={r.get("markers_per_chapter",{})}')

print('[E] Historical notes:')
inline = _count_inline_historical_notes(book)
field = len(book.get('historical_notes') or [])
print(f'  inline={inline}, field={field}')

print('[F] Historical notes distribution:')
r = validate_historical_notes_distribution(book, hist_cfg)
results['hist_notes_dist'] = r
print(f'  errors={r["errors_count"]}, warnings={r["warnings_count"]}')

print('[G] Descendants early (Class 12):')
r = validate_descendants_in_early_context(book, fm)
results['descendants_early'] = r
print(f'  errors={r["errors_count"]}, warnings={r["warnings_count"]}')

print('[H] Cross-paragraph duplication (Class 19):')
r = validate_cross_paragraph_duplication(book, dup_cfg)
results['cross_paragraph_dup'] = r
print(f'  errors={r["errors_count"]}, warnings={r["warnings_count"]}')

print('[I] Required episodes coverage:')
r = validate_required_episodes_coverage(book, pin_episodes)
results['req_ep_coverage'] = r
print(f'  total_req={r.get("total_required",0)} covered={r.get("covered_count",0)} missing={r.get("missing_count",0)}')
for ep in r.get('missing_episodes', [])[:5]:
    print(f'  MISSING: {ep.get("id", ep)}')

print('[J] bio_data family format:')
r = validate_bio_data_family_format(book)
results['bio_family_format'] = r
print(f'  ok={r.get("ok")} malformed={r.get("malformed",0)}')

# ---- v66a specific checks ----
print('\n=== v66a Nikitin content blockers ===')

kap_ulitsa = any(x in full_text.lower() for x in ['улица капошвара', 'улице капошвара', 'на улицу капошвара'])
kap_ploshad = any(x in full_text.lower() for x in ['площадь капошвара', 'площади капошвара', 'на площадь капошвар'])
kap_present = 'капошвара' in full_text.lower()
print(f'Капошвара = площадь: {kap_ploshad} | = улица: {kap_ulitsa} | present: {kap_present}')
m = re.search(r'.{0,50}[Кк]апошвар.{0,80}', full_text)
if m: print(f'  Context: ...{m.group()}...')

baba_anya = any(x in full_text.lower() for x in ['баба аня', 'бабы ани', 'бабе ане', 'бабой аней'])
print(f'Баба Аня в narrative: {baba_anya}')

# Check ch_03 specifically
for ch in chapters:
    if ch.get('id') == 'ch_03':
        c = ch.get('content', '')
        ba = any(x in c.lower() for x in ['баба аня', 'бабы ани', 'бабе ане'])
        print(f'  Баба Аня in ch_03: {ba}')

ogurtsy = 'огурц' in full_text.lower() and 'молдав' in full_text.lower()
print(f'Огурцы Молдавия (Class 1): {ogurtsy}')
m2 = re.search(r'.{0,30}огурц.{0,80}', full_text, re.I)
if m2: print(f'  Context: ...{m2.group()}...')

# Дача без 1990-е годы
dacha_1990 = '1990-е годы семья продала' in full_text or '1990-е годы семья' in full_text.lower()
dacha_bez = any(x in full_text.lower() for x in ['продала дачу', 'продали дачу', 'продала дачи'])
print(f'Дача без 1990-е в context продажи: wrong={dacha_1990}, sale_mentioned={dacha_bez}')

# writing_notes rule13
wn = book.get('writing_notes', {})
r13 = wn.get('rule13_revision_applied')
print(f'\nwriting_notes.rule13_revision_applied: type={type(r13).__name__}, is_list={isinstance(r13, list)}')
if isinstance(r13, list) and r13:
    print(f'  len={len(r13)}, first: {json.dumps(r13[0], ensure_ascii=False)[:100]}')

# char counts
ch_chars = {}
total_c = 0
for ch in chapters:
    cid = ch.get('id', '?')
    c = ch.get('content') or ''
    if cid == 'ch_01' and not c:
        c = json.dumps(ch.get('bio_data', {}), ensure_ascii=False)
    ch_chars[cid] = len(c)
    total_c += len(c)
narrative = sum(ch_chars.get(k, 0) for k in ['ch_02', 'ch_03', 'ch_04', 'epilogue'])

print('\n=== v66a Gate Summary ===')
print(f'Total chars (chapters): {total_c}')
print(f'chronology errors: {results["chronology"]["errors_count"]}')
print(f'narrative_truism errors: {results["narrative_truism"]["errors_count"]}')
print(f'stop_phrases errors: {results["stop_phrases"]["errors_count"]} warnings: {results["stop_phrases"]["warnings_count"]}')
print(f'cross_paragraph_dup errors: {results["cross_paragraph_dup"]["errors_count"]}')
print(f'required_episodes missing: {results["req_ep_coverage"].get("missing_count",0)} / {results["req_ep_coverage"].get("total_required",0)}')
print(f'ch_02={ch_chars.get("ch_02",0)} ch_03={ch_chars.get("ch_03",0)} ch_04={ch_chars.get("ch_04",0)} epilogue={ch_chars.get("epilogue",0)}')
print(f'Narrative: {narrative} | Total: {total_c}')

out_path = str(STAGE3_DIR / 'karakulina_v66a_final_validators.json')
json.dump(results, open(out_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
ep_path = str(STAGE3_DIR / 'karakulina_required_episodes_coverage_v66a.json')
json.dump(results.get('req_ep_coverage', {}), open(ep_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(f'\nSaved: {out_path}')
print(f'Saved: {ep_path}')
