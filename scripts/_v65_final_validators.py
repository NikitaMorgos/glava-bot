#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v65 final validators on stage3 output."""
import json, sys, os, glob
sys.path.insert(0, '/opt/glava')
sys.stdout.reconfigure(encoding='utf-8')
from pipeline_utils import (
    validate_children_before_birth,
    validate_chronological_consistency,
    validate_narrative_stop_phrases,
    validate_narrative_truism,
    validate_personal_historical_voice,
    validate_epilogue_quote_density,
    validate_bio_data_family_format,
    validate_descendants_in_early_context,
    validate_cross_paragraph_duplication,
    validate_historical_notes_distribution,
    validate_required_episodes_coverage,
    _count_inline_historical_notes,
    parse_pin_list_from_markdown,
)

book_files = sorted(glob.glob('exports/stage3_v65/karakulina_book_FINAL_stage3_*.json'), reverse=True)
fm_files = sorted(glob.glob('exports/karakulina_v65/karakulina_fact_map_full_*.json'), reverse=True)
if not book_files or not fm_files:
    print("ERROR: book or fact_map not found"); sys.exit(1)

book_raw = json.load(open(book_files[0], encoding='utf-8'))
book = book_raw.get('book_draft') or book_raw.get('book_final') or book_raw
fm = json.load(open(fm_files[0], encoding='utf-8'))

chrono_cfg = json.load(open('collab/context/chronology_check_config.json', encoding='utf-8'))
stop_cfg = json.load(open('collab/context/narrative_stop_phrases.json', encoding='utf-8'))
dupl_cfg = json.load(open('collab/context/cross_paragraph_duplication_config.json', encoding='utf-8'))
hist_dist_cfg = json.load(open('collab/context/historical_notes_distribution_config.json', encoding='utf-8'))
pin_list_data = parse_pin_list_from_markdown('collab/context/known_episodes_karakulina.md')

print("\n=== FINAL VALIDATORS (post-revision, on stage3 output) ===\n")
results = {}

print("[A] 048e: chronological_consistency (FP fix):")
r = validate_chronological_consistency(book, fm, chrono_cfg)
results['chronology'] = r
print(f"  errors={r['errors_count']}, warnings={r['warnings_count']}")
for i in r['issues'][:3]:
    print(f"  [{i['severity']}] person={i.get('person_name')} ch={i['chapter_id']}")

print("\n[B] 043h: narrative_truism (Class 17):")
r = validate_narrative_truism(book)
results['narrative_truism'] = r
print(f"  errors={r['errors_count']}, warnings={r['warnings_count']}")
for i in r.get('issues', [])[:3]:
    print(f"  [{i.get('severity','?')}] {i.get('category','?')} ch={i.get('chapter_id')}")
    print(f"    '{i.get('snippet','')[:80]}'")

print("\n[C] 043f-3: narrative_stop_phrases (Class 1/11 v7):")
r = validate_narrative_stop_phrases(book, stop_cfg)
results['stop_phrases'] = r
print(f"  errors={r['errors_count']}, warnings={r['warnings_count']}")
class1_11 = [i for i in r.get('issues', []) if any(c in i.get('category','') for c in ('class1','class11'))]
print(f"  Class1/11 issues: {len(class1_11)}")
for i in class1_11[:3]:
    print(f"  [{i.get('severity','?')}] {i.get('category','?')} ch={i.get('chapter_id')}: '{i.get('snippet','')[:60]}'")

print("\n[D] 046e: personal_historical_voice:")
r = validate_personal_historical_voice(book)
results['personal_historical_voice'] = r
print(f"  markers_per_chapter={r.get('markers_found_per_chapter')}")
for i in r.get('issues', []):
    print(f"  [{i.get('severity','?')}] ch={i.get('chapter_id')} found={i.get('found')}/need={i.get('needed')}")

print("\n[E] Historical notes count:")
inline = _count_inline_historical_notes(book)
hn = book.get('historical_notes') or []
print(f"  inline_notes={inline}, field_notes={len(hn)}")
print(f"  target: >=5 inline ({'OK' if inline >= 5 else 'BELOW'}), >=3 field ({'OK' if len(hn) >= 3 else 'BELOW'})")

print("\n[F] 046f: historical_notes_distribution (per-chapter v65):")
r = validate_historical_notes_distribution(book, hist_dist_cfg)
results['hist_notes_dist'] = r
print(f"  errors={r['errors_count']}, warnings={r['warnings_count']}")
for i in r.get('issues', []):
    print(f"  [{i['severity']}] ch={i.get('chapter_id')} found={i.get('found')}/need={i.get('needed')}")

print("\n[G] 048f: descendants_in_early_context (Class 12 extend):")
r = validate_descendants_in_early_context(book, fm)
results['descendants_early'] = r
print(f"  errors={r['errors_count']}, warnings={r['warnings_count']}")
for i in r.get('issues', []):
    print(f"  [{i['severity']}] {i['person_name']} ch={i['chapter_id']}: '{i.get('snippet','')[:60]}'")

print("\n[H] 048g: cross_paragraph_duplication (Class 19):")
r = validate_cross_paragraph_duplication(book, dupl_cfg)
results['cross_paragraph_dup'] = r
print(f"  errors={r['errors_count']}, warnings={r['warnings_count']}")
for i in r.get('issues', [])[:3]:
    print(f"  [{i['severity']}] sim={i.get('similarity',0):.2f}: '{i.get('para_a_snippet','')[:60]}'")

print("\n[I] 044i: required_episodes_coverage:")
pin_episodes = pin_list_data.get('episodes', []) if isinstance(pin_list_data, dict) else pin_list_data
r = validate_required_episodes_coverage(book, pin_episodes)
results['req_ep_coverage'] = r
print(f"  total_required={r.get('total_required')}, covered={r.get('covered_count')}, missing={r.get('missing_count')}")
for ep in [e for e in r.get('required_episodes', []) if not e.get('found')]:
    print(f"  MISSING: {ep['episode_id']} '{ep.get('title','')}'")

print("\n[J] bio_data family format:")
for ch in book.get('chapters', []):
    if ch.get('id') == 'ch_01':
        bio = ch.get('bio_data', {})
        r = validate_bio_data_family_format(bio)
        print(f"  ok={r['ok']}, malformed={r['malformed_count']}")
        family = bio.get('family', [])
        maria_found = any('Мария' in str(e) or 'Мар' in str(e) for e in family)
        print(f"  Мария in family: {'YES' if maria_found else 'MISSING'}")
        break

# Content checks (Nikitin feedback v64)
print("\n=== Content checks (Nikitin feedback v64) ===")
full_text = ' '.join(ch.get('content', '') for ch in book.get('chapters', []))
print(f"Баба Аня in narrative: {'YES' if 'баба аня' in full_text.lower() or 'баб' in full_text.lower() and 'ан' in full_text.lower() else 'CHECK'}")
print(f"Грибы/ягоды in narrative: {'YES' if 'гриб' in full_text.lower() or 'ягод' in full_text.lower() else 'MISSING'}")
print(f"Продажа дачи in narrative: {'YES' if 'продаж' in full_text.lower() and 'дач' in full_text.lower() else 'CHECK'}")
ch02_content = next((ch.get('content','') for ch in book.get('chapters',[]) if ch.get('id')=='ch_02'), '')
if '1933' in ch02_content and any(n in ch02_content for n in ['Толя','Коля','Витя']):
    print(f"Полина 1933 context: WARNING — Толя/Коля/Витя may be in ch_02 1933 context")
else:
    print(f"Полина 1933 context: OK — clean")
if 'Капошвар' in full_text:
    if 'площадь Капошвар' in full_text or 'Капошвар' in full_text:
        if 'улица Капошвар' in full_text.lower() or 'улице Капошвар' in full_text.lower():
            print(f"Капошвара: WRONG — улица found (should be площадь)")
        else:
            print(f"Капошвара: OK (no 'улица', площадь fix applied)")
else:
    print(f"Капошвара: not in text")

print("\n=== v65 GATE SUMMARY ===")
print(f"chronology errors: {results.get('chronology', {}).get('errors_count', '?')}")
print(f"narrative_truism errors: {results.get('narrative_truism', {}).get('errors_count', '?')}")
stop_r = results.get('stop_phrases', {})
print(f"stop_phrases errors: {stop_r.get('errors_count', '?')} warnings: {stop_r.get('warnings_count', '?')}")
print(f"hist_notes_dist errors: {results.get('hist_notes_dist', {}).get('errors_count', '?')}")
print(f"descendants_early errors: {results.get('descendants_early', {}).get('errors_count', '?')}")
print(f"cross_paragraph_dup errors: {results.get('cross_paragraph_dup', {}).get('errors_count', '?')}")
req_ep = results.get('req_ep_coverage', {})
print(f"required_episodes missing: {req_ep.get('missing_count', '?')} / {req_ep.get('total_required', '?')}")

json.dump(results,
          open('exports/stage3_v65/karakulina_v65_final_validators.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=2)
print("\nSaved: exports/stage3_v65/karakulina_v65_final_validators.json")

json.dump(req_ep,
          open('exports/stage3_v65/karakulina_required_episodes_coverage.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=2)
print("Saved: exports/stage3_v65/karakulina_required_episodes_coverage.json")
