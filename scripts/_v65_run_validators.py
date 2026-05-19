#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v65 validators + revision hints collection — runs on VPS after Stage 2 first pass."""
import json, sys, os, glob
sys.path.insert(0, '/opt/glava')
sys.stdout.reconfigure(encoding='utf-8')

from pipeline_utils import (
    validate_children_before_birth,
    validate_chronological_consistency,
    validate_narrative_stop_phrases,
    validate_epilogue_quote_density,
    validate_entity_substitution,
    validate_bio_data_family_format,
    validate_narrative_truism,
    validate_personal_historical_voice,
    validate_descendants_in_early_context,
    validate_cross_paragraph_duplication,
    validate_historical_notes_distribution,
    validate_required_episodes_coverage,
    collect_revision_hints,
    parse_pin_list_from_markdown,
)

STAGE2_DIR = 'exports/stage2_v65'
FM_DIR = 'exports/karakulina_v65'

book_files = sorted(glob.glob(os.path.join(STAGE2_DIR, 'karakulina_book_FINAL_*.json')), reverse=True)
fm_files = sorted(glob.glob(os.path.join(FM_DIR, 'karakulina_fact_map_full_*.json')), reverse=True)
if not book_files or not fm_files:
    print("ERROR: book or fact_map not found"); sys.exit(1)

book_draft_raw = json.load(open(book_files[0], encoding='utf-8'))
book_draft = book_draft_raw.get('book_draft') or book_draft_raw.get('book_final') or book_draft_raw
fm = json.load(open(fm_files[0], encoding='utf-8'))

stop_cfg = json.load(open('collab/context/narrative_stop_phrases.json', encoding='utf-8'))
chrono_cfg = json.load(open('collab/context/chronology_check_config.json', encoding='utf-8'))
dupl_cfg = json.load(open('collab/context/cross_paragraph_duplication_config.json', encoding='utf-8'))
hist_dist_cfg = json.load(open('collab/context/historical_notes_distribution_config.json', encoding='utf-8'))

pin_list_data = parse_pin_list_from_markdown('collab/context/known_episodes_karakulina.md')
print(f"[PIN-LIST] episodes={len(pin_list_data.get('episodes', []))}, bytovye={len(pin_list_data.get('bytovye', []))}")

tr_files = sorted(glob.glob('collab/transcripts/*.txt'))
transcripts = [open(f, encoding='utf-8').read() for f in tr_files[:2]]

print('\n=== v65 validators on book_draft ===\n')

r_chrono = validate_chronological_consistency(book_draft, fm, chrono_cfg)
print(f"[1] chronology: errors={r_chrono['errors_count']}, warnings={r_chrono['warnings_count']}")
for i in r_chrono['issues'][:3]:
    print(f"  [{i['severity']}] person={i.get('person_name')} ch={i['chapter_id']}")

r_truism = validate_narrative_truism(book_draft)
print(f"[2] narrative_truism: errors={r_truism['errors_count']}, warnings={r_truism['warnings_count']}")
for i in r_truism.get('issues', [])[:3]:
    print(f"  [{i.get('severity')}] {i.get('category')} ch={i.get('chapter_id')}: {str(i.get('snippet',''))[:60]}")

r_stop = validate_narrative_stop_phrases(book_draft, stop_cfg)
print(f"[3] stop_phrases: errors={r_stop['errors_count']}, warnings={r_stop['warnings_count']}")
for i in r_stop.get('issues', [])[:5]:
    print(f"  [{i.get('severity')}] {i.get('category')} ch={i.get('chapter_id')}: {str(i.get('snippet',''))[:60]}")

r_voice = validate_personal_historical_voice(book_draft)
print(f"[4] personal_historical_voice: markers_per_ch={r_voice.get('markers_found_per_chapter')}")
for i in r_voice.get('issues', [])[:3]:
    print(f"  [{i.get('severity')}] ch={i.get('chapter_id')} found={i.get('found')}/need={i.get('needed')}")

r_epil = validate_epilogue_quote_density(book_draft)
print(f"[5] epilogue_quote_density: ok={r_epil.get('ok')}, quotes={r_epil.get('quote_count')}")

r_subst = validate_entity_substitution(book_draft, fm, transcripts)
print(f"[6] entity_substitution: ok={r_subst['ok']}, issues={len(r_subst['issues'])}")

r_desc = validate_descendants_in_early_context(book_draft, fm)
print(f"[7] descendants_early: errors={r_desc['errors_count']}, warnings={r_desc['warnings_count']}")
for i in r_desc.get('issues', [])[:3]:
    print(f"  [{i['severity']}] {i['person_name']} ch={i['chapter_id']} year={i['event_year_in_paragraph']} min={i['inferred_min_birth']}")
    print(f"    snippet: {str(i.get('snippet',''))[:80]}")

r_dupl = validate_cross_paragraph_duplication(book_draft, dupl_cfg)
print(f"[8] cross_paragraph_dup: errors={r_dupl['errors_count']}, warnings={r_dupl['warnings_count']}")
for i in r_dupl.get('issues', [])[:3]:
    print(f"  [{i['severity']}] sim={i.get('similarity',0):.2f}: {str(i.get('para_a_snippet',''))[:60]}")

r_hist_dist = validate_historical_notes_distribution(book_draft, hist_dist_cfg)
print(f"[9] hist_notes_dist: errors={r_hist_dist['errors_count']}, warnings={r_hist_dist['warnings_count']}")
for i in r_hist_dist.get('issues', [])[:3]:
    print(f"  [{i['severity']}] ch={i.get('chapter_id')} found={i.get('found')}/need={i.get('needed')}")

pin_episodes = pin_list_data.get('episodes', []) + pin_list_data.get('bytovye', [])
r_req_ep = validate_required_episodes_coverage(book_draft, pin_episodes)
print(f"[10] required_episodes: total={r_req_ep.get('total_required')}, covered={r_req_ep.get('covered_count')}, missing={r_req_ep.get('missing_count')}")
for ep in [e for e in r_req_ep.get('required_episodes', []) if not e.get('found')][:5]:
    print(f"  MISSING: {ep['episode_id']} '{str(ep.get('title',''))[:50]}'")

# Combine all validator outputs
validator_outputs = {
    'chronology_check': r_chrono,
    'narrative_truism': r_truism,
    'narrative_stop_phrases': r_stop,
    'personal_historical_voice': r_voice,
    'epilogue_quote_density': r_epil,
    'entity_substitution': r_subst,
    'descendants_in_early_context': r_desc,
    'cross_paragraph_duplication': r_dupl,
    'historical_notes_distribution': r_hist_dist,
    'required_episodes_coverage': r_req_ep,
}
json.dump(validator_outputs, open(os.path.join(STAGE2_DIR, 'validators_on_draft.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(f"\nSaved: {STAGE2_DIR}/validators_on_draft.json")

revision_hints = collect_revision_hints(book_draft, validator_outputs)
print(f"\n=== 049f-2: collect_revision_hints: {len(revision_hints)} total hints ===")
must_apply = [h for h in revision_hints if h.get('must_apply')]
warn_hints = [h for h in revision_hints if not h.get('must_apply')]
print(f"  must_apply (error): {len(must_apply)}")
print(f"  warning hints: {len(warn_hints)}")
for h in revision_hints[:7]:
    print(f"  [{h['hint_id']}] {h['validator']}/{h['category']} ch={h['chapter_id']} must_apply={h['must_apply']}")
    print(f"    snippet: {str(h.get('snippet',''))[:70]}")

json.dump(revision_hints, open(os.path.join(STAGE2_DIR, 'revision_hints.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(f"\nSaved: {STAGE2_DIR}/revision_hints.json ({len(revision_hints)} hints)")

if not revision_hints:
    with open(os.path.join(STAGE2_DIR, 'revision_pass_log.json'), 'w') as f:
        json.dump({'skipped': 'no_revision_hints', 'reason': 'all validators clean on first pass'}, f)
    print("Saved: revision_pass_log.json (no hints)")
    print("\n=== REVISION SKIPPED: all validators clean ===")
else:
    print(f"\n=== REVISION PASS REQUIRED: {len(revision_hints)} hints → Stage 2 revision pass ===")
