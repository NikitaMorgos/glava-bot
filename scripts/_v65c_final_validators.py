#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v65c: run final validators on stage3_v65c output."""
import json, sys, os, glob
sys.path.insert(0, '/opt/glava')
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

STAGE3C_DIR = 'exports/stage3_v65c'
FM_DIR = 'exports/karakulina_v65'

s3_files = sorted(glob.glob(os.path.join(STAGE3C_DIR, 'karakulina_book_FINAL_stage3_*.json')), reverse=True)
if not s3_files:
    print('ERROR: no stage3 book'); sys.exit(1)

fm_files = sorted(glob.glob(os.path.join(FM_DIR, 'karakulina_fact_map_full_*.json')), reverse=True)
book_raw = json.load(open(s3_files[0], encoding='utf-8'))
book = book_raw.get('book_draft') or book_raw.get('book_final') or book_raw
fm = json.load(open(fm_files[0], encoding='utf-8'))

pin_list = parse_pin_list_from_markdown('collab/context/known_episodes_karakulina.md')
chapters = book.get('chapters', [])
full_text = ' '.join((ch.get('content') or '') for ch in chapters)

results = {}

import os as _os
def load_cfg(path):
    return json.load(open(path, encoding='utf-8')) if _os.path.exists(path) else {}

chrono_cfg = load_cfg('collab/context/chronology_check_config.json')
dup_cfg = load_cfg('collab/context/cross_paragraph_duplication_config.json')
hist_cfg = load_cfg('collab/context/historical_notes_distribution_config.json')

print('[A] Chronology:')
r = validate_chronological_consistency(book, fm, chrono_cfg)
results['chronology'] = r
print('  errors=%d, warnings=%d' % (r['errors_count'], r['warnings_count']))

print('[B] Narrative truism Class 17:')
r = validate_narrative_truism(book)
results['narrative_truism'] = r
print('  errors=%d, warnings=%d' % (r['errors_count'], r['warnings_count']))

print('[C] Stop phrases Class 1/11:')
nsp_cfg = load_cfg('collab/context/narrative_stop_phrases.json')
r = validate_narrative_stop_phrases(book, nsp_cfg)
results['stop_phrases'] = r
print('  errors=%d, warnings=%d' % (r['errors_count'], r['warnings_count']))

print('[D] Personal historical voice:')
r = validate_personal_historical_voice(book)
results['personal_historical_voice'] = r
markers = r.get('markers_per_chapter', {})
print('  errors=%d, warnings=%d markers=%s' % (r['errors_count'], r['warnings_count'], markers))

print('[E] Historical notes count:')
inline = _count_inline_historical_notes(book)
field = len(book.get('historical_notes') or [])
print('  inline=%d, field=%d' % (inline, field))

print('[F] Historical notes distribution:')
r = validate_historical_notes_distribution(book, hist_cfg)
results['hist_notes_dist'] = r
print('  errors=%d, warnings=%d' % (r['errors_count'], r['warnings_count']))

print('[G] Descendants early (Class 12):')
r = validate_descendants_in_early_context(book, fm)
results['descendants_early'] = r
print('  errors=%d, warnings=%d' % (r['errors_count'], r['warnings_count']))

print('[H] Cross-paragraph duplication (Class 19):')
r = validate_cross_paragraph_duplication(book, dup_cfg)
results['cross_paragraph_dup'] = r
print('  errors=%d, warnings=%d' % (r['errors_count'], r['warnings_count']))

print('[I] Required episodes coverage (044i):')
r = validate_required_episodes_coverage(book, pin_list)
results['req_ep_coverage'] = r
print('  total_req=%d covered=%d missing=%d' % (
    r.get('total_required', 0), r.get('covered_count', 0), r.get('missing_count', 0)))
for ep in r.get('missing_episodes', [])[:5]:
    print('  MISSING: %s' % ep.get('id', ep))

print('[J] bio_data family format:')
r = validate_bio_data_family_format(book)
results['bio_family_format'] = r
print('  ok=%s malformed=%d' % (r.get('ok'), r.get('malformed', 0)))
maria = any('мария' in str(e).lower() for e in (book.get('chapters', [{}])[0].get('bio_data', {}) or {}).get('family', []))
print('  Мария in family: %s' % ('YES' if maria else 'NO'))

# v65c specific checks
print('\n=== v65c specific content checks ===')
kap_ulitsa = any(x in full_text.lower() for x in ['улица капошвара', 'улице капошвара', 'улицу капошвара'])
kap_ploshad = any(x in full_text.lower() for x in ['площадь капошвара', 'площади капошвара', 'на площадь капошвар'])
print('Капошвара улица: %s | площадь: %s → %s' % (
    kap_ulitsa, kap_ploshad,
    'FIX OK ✅' if not kap_ulitsa and kap_ploshad else 'FIX FAILED ❌' if kap_ulitsa else 'площадь not detected ⚠️'))

baba_anya = any(x in full_text.lower() for x in ['баба аня', 'бабы ани', 'бабе ане', 'бабой аней'])
print('Баба Аня: %s' % ('PRESENT ✅' if baba_anya else 'MISSING ❌'))

dacha_1990 = '1990-е годы семья продала' in full_text or 'в 1990-е годы семья' in full_text.lower()
dacha_1980 = 'до 1990-х' in full_text or 'в 1980-е' in full_text
print('Дача год: wrong_1990=%s fix_applied=%s → %s' % (
    dacha_1990, dacha_1980,
    'FIX OK ✅' if not dacha_1990 else 'STILL WRONG ❌'))

print('Грибы/ягоды: %s' % ('YES' if 'грибы' in full_text.lower() or 'ягоды' in full_text.lower() else 'NO'))
print('Продажа дачи: %s' % ('YES' if 'продала дачу' in full_text.lower() or 'продали дачу' in full_text.lower() else 'CHECK'))
kap_plosad_bio = any(x in json.dumps(book.get('chapters', [{}])[0].get('bio_data', {}), ensure_ascii=False).lower()
                     for x in ['площадь капошвара', 'площади капошвара'])
kap_ulitsa_bio = 'улица капошвара' in json.dumps(book.get('chapters', [{}])[0].get('bio_data', {}), ensure_ascii=False).lower()
print('Капошвара bio_data: улица=%s площадь=%s' % (kap_ulitsa_bio, kap_plosad_bio))

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
hn_chars = sum(len(h.get('text', '') or '') for h in (book.get('historical_notes') or []))
print('\n=== v65c Gate Summary ===')
print('chronology errors: %d' % results['chronology']['errors_count'])
print('narrative_truism errors: %d' % results['narrative_truism']['errors_count'])
print('stop_phrases errors: %d warnings: %d' % (results['stop_phrases']['errors_count'], results['stop_phrases']['warnings_count']))
print('hist_notes_dist errors: %d' % results['hist_notes_dist']['errors_count'])
print('descendants_early errors: %d' % results['descendants_early']['errors_count'])
print('cross_paragraph_dup errors: %d' % results['cross_paragraph_dup']['errors_count'])
print('required_episodes missing: %d / %d' % (results['req_ep_coverage'].get('missing_count', 0), results['req_ep_coverage'].get('total_required', 0)))
print('ch_02=%d ch_03=%d ch_04=%d epilogue=%d' % (
    ch_chars.get('ch_02', 0), ch_chars.get('ch_03', 0), ch_chars.get('ch_04', 0), ch_chars.get('epilogue', 0)))
print('Narrative: %d | Total: %d | Total+hist_notes: %d' % (narrative, total_c, total_c + hn_chars))

out_path = os.path.join(STAGE3C_DIR, 'karakulina_v65c_final_validators.json')
json.dump(results, open(out_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
ep_path = os.path.join(STAGE3C_DIR, 'karakulina_required_episodes_coverage_v65c.json')
json.dump(results.get('req_ep_coverage', {}), open(ep_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('\nSaved: %s' % out_path)
