"""v64: Run all validators on book_draft and collect revision_hints."""
import json, sys, os, glob
sys.path.insert(0, '/opt/glava')
from pipeline_utils import (
    validate_children_before_birth,
    validate_narrative_stop_phrases,
    validate_narrative_truism,
    validate_personal_historical_voice,
    validate_epilogue_quote_density,
    validate_entity_substitution,
    collect_revision_hints,
)

book_files = sorted(glob.glob('exports/stage2_v64/karakulina_book_FINAL_*.json'), reverse=True)
fm_files = sorted(glob.glob('exports/karakulina_v64/karakulina_fact_map_full_*.json'), reverse=True)
print('Book:', book_files[0] if book_files else 'NOT FOUND')
print('FM:', fm_files[0] if fm_files else 'NOT FOUND')

if not book_files or not fm_files:
    print('ERROR: artifacts not found')
    sys.exit(1)

book_raw = json.load(open(book_files[0], encoding='utf-8'))
book_draft = book_raw.get('book_draft') or book_raw.get('book_final') or book_raw
fm = json.load(open(fm_files[0], encoding='utf-8'))

chrono_cfg = json.load(open('collab/context/chronology_periods_karakulina.json', encoding='utf-8'))
stop_cfg = json.load(open('collab/context/narrative_stop_phrases.json', encoding='utf-8'))
tr_files = sorted(glob.glob('collab/transcripts/*.txt'))
transcripts = [open(f, encoding='utf-8').read() for f in tr_files[:2]]

print('\n=== Running validators ===')

r_chrono = validate_children_before_birth(book_draft, chrono_cfg)
print('chronology: errors=%d, warnings=%d' % (r_chrono['errors_count'], r_chrono['warnings_count']))
for i in r_chrono['issues'][:3]:
    print('  [%s] %s ch=%s year=%s' % (i['severity'], i['type'], i['chapter_id'], i.get('event_year')))

r_truism = validate_narrative_truism(book_draft)
print('narrative_truism: errors=%d, total=%d' % (r_truism['errors_count'], len(r_truism.get('issues', []))))
for i in r_truism.get('issues', [])[:3]:
    print('  [%s] %s ch=%s' % (i.get('severity', '?'), i.get('category', '?'), i.get('chapter_id')))
    print('    snippet: %r' % i.get('snippet', '')[:80])

r_stop = validate_narrative_stop_phrases(book_draft, stop_cfg)
print('stop_phrases: errors=%d, warnings=%d' % (r_stop['errors_count'], r_stop['warnings_count']))
for i in r_stop.get('issues', [])[:8]:
    print('  [%s] %s ch=%s' % (i.get('severity', '?'), i.get('category', '?'), i.get('chapter_id')))

r_voice = validate_personal_historical_voice(book_draft)
print('personal_voice: issues=%d, per_ch=%s' % (len(r_voice.get('issues', [])), r_voice.get('markers_found_per_chapter')))

r_epil = validate_epilogue_quote_density(book_draft)
print('epilogue: ok=%s, quotes=%s' % (r_epil.get('ok'), r_epil.get('quote_count')))

r_subst = validate_entity_substitution(book_draft, fm, transcripts)
print('entity_subst: ok=%s, issues=%d' % (r_subst['ok'], len(r_subst['issues'])))

validator_outputs = {
    'chronology_check': r_chrono,
    'narrative_truism': r_truism,
    'narrative_stop_phrases': r_stop,
    'personal_historical_voice': r_voice,
    'epilogue_quote_density': r_epil,
    'entity_substitution': r_subst,
}
json.dump(validator_outputs, open('exports/stage2_v64/validators_on_draft.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('\nSaved: validators_on_draft.json')

hints = collect_revision_hints(book_draft, validator_outputs)
must_apply = [h for h in hints if h.get('must_apply')]
print('\nrevision_hints: total=%d, must_apply=%d' % (len(hints), len(must_apply)))
for h in hints[:8]:
    print('  [%s] %s/%s ch=%s must_apply=%s' % (h['hint_id'], h['validator'], h['category'], h['chapter_id'], h['must_apply']))
    print('    snippet: %r' % (h.get('snippet', '')[:70] if h.get('snippet') else '(no snippet)',))
    print('    suggestion: %r' % h.get('suggestion', '')[:80])

json.dump(hints, open('exports/stage2_v64/revision_hints.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('\nSaved: revision_hints.json (%d hints)' % len(hints))

if not hints:
    json.dump({"skipped": "no_revision_hints"}, open('exports/stage2_v64/revision_pass_log.json', 'w', encoding='utf-8'))
    print('No hints: revision_pass_log.json written (skipped)')
else:
    print('REVISION PASS REQUIRED: %d hints' % len(hints))
