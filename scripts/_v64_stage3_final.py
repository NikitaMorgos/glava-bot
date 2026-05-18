"""v64: Stage 3 and final validation (post-revision pass)."""
import json, sys, os, glob, subprocess, shutil
from datetime import datetime
sys.path.insert(0, '/opt/glava')

# Load .env
if not os.environ.get('OPENAI_API_KEY'):
    try:
        with open('/opt/glava/.env', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    os.environ.setdefault(k.strip(), v.strip())
        print('Loaded .env')
    except FileNotFoundError:
        pass

from pipeline_utils import (
    enrich_historical_notes_inline,
    _count_inline_historical_notes,
    validate_children_before_birth,
    validate_narrative_stop_phrases,
    validate_narrative_truism,
    validate_personal_historical_voice,
    validate_epilogue_quote_density,
    validate_bio_data_family_format,
)

ARTIFACTS_DIR = 'collab/runs/karakulina-v64-artifacts'

# Load revised book
revised_files = sorted(glob.glob('exports/stage2_v64/karakulina_book_REVISED_*.json'), reverse=True)
fm_files = sorted(glob.glob('exports/karakulina_v64/karakulina_fact_map_full_*.json'), reverse=True)

print('Revised book:', revised_files[0] if revised_files else 'NOT FOUND')
print('FM:', fm_files[0] if fm_files else 'NOT FOUND')

if not revised_files or not fm_files:
    print('ERROR: artifacts not found')
    sys.exit(1)

book_raw = json.load(open(revised_files[0], encoding='utf-8'))
book_revised = book_raw.get('book_draft') or book_raw.get('book_final') or book_raw
fm_path = fm_files[0]

print('\n=== 046d: historical_notes enrichment ===')
enrich_cfg = json.load(open('collab/context/historical_notes_enrichment_config.json', encoding='utf-8'))
before_count = _count_inline_historical_notes(book_revised)
print('inline notes before enrichment: %d' % before_count)

enriched_book = enrich_historical_notes_inline(book_revised, enrich_cfg)
after_count = _count_inline_historical_notes(enriched_book)
print('inline notes after enrichment: %d' % after_count)
field_notes = len(enriched_book.get('historical_notes') or [])
print('field historical_notes: %d' % field_notes)

# Save enriched book for Stage 3
ts = datetime.now().strftime('%Y%m%d_%H%M%S')
enriched_path = 'exports/stage2_v64/karakulina_book_FINAL_%s_enriched.json' % ts
json.dump(enriched_book, open(enriched_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('Saved enriched: %s' % enriched_path)

# Stage 3
print('\n=== STAGE 3 (LE + Proofreader + validators) ===')
stage3_dir = 'exports/stage3_v64'
os.makedirs(stage3_dir, exist_ok=True)

ret = subprocess.call([
    'python', 'scripts/test_stage3.py',
    '--book-draft', enriched_path,
    '--fact-map', fm_path,
    '--output-dir', stage3_dir,
    '--prefix', 'karakulina',
    '--no-strict-gates',
])
print('Stage3 exit code: %d' % ret)

# Build gate1 full text
book_final_s3_files = sorted(glob.glob(os.path.join(stage3_dir, 'karakulina_book_FINAL_stage3_*.json')), reverse=True)
if not book_final_s3_files:
    print('ERROR: stage3 book not found')
    sys.exit(1)

print('\n=== build_gate1_full_text ===')
text_out = os.path.join(stage3_dir, 'karakulina_v64_text_FULL.md')
ret = subprocess.call([
    'python', 'scripts/build_gate1_full_text.py',
    '--book-final', book_final_s3_files[0],
    '--fact-map', fm_path,
    '--output', text_out,
    '--reports-dir', stage3_dir,
    '--prefix', 'karakulina',
    '--pin-list', 'collab/context/known_episodes_karakulina.md',
])
print('build_gate1 exit code: %d' % ret)

# Final validators
print('\n=== FINAL VALIDATORS ===')
book_final_raw = json.load(open(book_final_s3_files[0], encoding='utf-8'))
book_final = book_final_raw.get('book_draft') or book_final_raw.get('book_final') or book_final_raw

chrono_cfg = json.load(open('collab/context/chronology_periods_karakulina.json', encoding='utf-8'))
stop_cfg = json.load(open('collab/context/narrative_stop_phrases.json', encoding='utf-8'))

r_chrono = validate_children_before_birth(book_final, chrono_cfg)
r_truism = validate_narrative_truism(book_final)
r_stop = validate_narrative_stop_phrases(book_final, stop_cfg)
r_voice = validate_personal_historical_voice(book_final)
r_epil = validate_epilogue_quote_density(book_final)

print('[A] chronology: errors=%d, warnings=%d' % (r_chrono['errors_count'], r_chrono['warnings_count']))
for i in r_chrono['issues'][:3]:
    print('  [%s] %s ch=%s year=%s' % (i['severity'], i['type'], i['chapter_id'], i.get('event_year')))

print('[B] narrative_truism (Class17): errors=%d, total=%d' % (r_truism['errors_count'], len(r_truism.get('issues', []))))
print('[C] stop_phrases (Class1/11): errors=%d, warnings=%d' % (r_stop['errors_count'], r_stop['warnings_count']))
class1_11 = [i for i in r_stop.get('issues', []) if any(c in i.get('category','') for c in ('class1','class11'))]
print('  Class1/11 issues: %d' % len(class1_11))
print('[D] personal_historical_voice (Class18): issues=%d' % len(r_voice.get('issues', [])))
print('  per_ch: %s' % r_voice.get('markers_found_per_chapter'))
print('[E] historical_notes: inline=%d, field=%d' % (_count_inline_historical_notes(book_final), len(book_final.get('historical_notes') or [])))
print('[F] epilogue: ok=%s, quotes=%s' % (r_epil.get('ok'), r_epil.get('quote_count')))

# Check Мария + баба Аня
for ch in book_final.get('chapters', []):
    if ch.get('id') == 'ch_01':
        bio = ch.get('bio_data', {})
        family = bio.get('family', [])
        maria_found = any('Мария' in str(e) or 'Мар' in str(e.get('name','') if isinstance(e,dict) else e) for e in family)
        print('[G] Мария in bio_data.family: %s' % ('YES' if maria_found else 'MISSING'))
        break

# Check баба Аня in narrative
full_text = ''
for ch in book_final.get('chapters', []):
    if ch.get('id') == 'ch_03':
        full_text = ch.get('content') or ''
baba_anya = 'баба Аня' in full_text or 'бабой Аней' in full_text or 'бабе Ане' in full_text or 'Аней' in full_text
print('[H] баба Аня in ch_03: %s' % ('YES' if baba_anya else 'MISSING'))

# Save final validators report
final_validators = {
    'chronology': r_chrono,
    'narrative_truism': r_truism,
    'stop_phrases': r_stop,
    'personal_historical_voice': r_voice,
    'epilogue': r_epil,
}
json.dump(final_validators, open(os.path.join(stage3_dir, 'karakulina_v64_final_validators.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('\nSaved: karakulina_v64_final_validators.json')

# Collect artifacts
print('\n=== Collecting artifacts to %s ===' % ARTIFACTS_DIR)
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

def cp(pattern, dest):
    files = sorted(glob.glob(pattern), reverse=True)
    for f in files[:2]:
        shutil.copy2(f, dest)
        print('  copied: %s' % os.path.basename(f))

cp('exports/karakulina_v64/karakulina_fact_map_full_*.json', ARTIFACTS_DIR)
cp('exports/stage2_v64/karakulina_book_draft.json', ARTIFACTS_DIR)
cp('exports/stage2_v64/karakulina_book_FINAL_*.json', ARTIFACTS_DIR)
cp('exports/stage2_v64/karakulina_book_REVISED_*.json', ARTIFACTS_DIR)
cp('exports/stage2_v64/karakulina_stage2_run_manifest_*.json', ARTIFACTS_DIR)
cp('exports/stage2_v64/validators_on_draft.json', ARTIFACTS_DIR)
cp('exports/stage2_v64/revision_hints.json', ARTIFACTS_DIR)
cp('exports/stage2_v64/revision_diff_audit.json', ARTIFACTS_DIR)
cp('exports/stage3_v64/karakulina_book_FINAL_stage3_*.json', ARTIFACTS_DIR)
cp('exports/stage3_v64/karakulina_v64_text_FULL.md', ARTIFACTS_DIR)
cp('exports/stage3_v64/karakulina_v64_final_validators.json', ARTIFACTS_DIR)
cp('exports/stage3_v64/karakulina_stage3_run_manifest_*.json', ARTIFACTS_DIR)
cp('exports/stage3_v64/karakulina_style_checks_*.json', ARTIFACTS_DIR)
cp('exports/stage3_v64/karakulina_chronology_check_*.json', ARTIFACTS_DIR)
cp('exports/stage3_v64/karakulina_pin_list_depth_*.json', ARTIFACTS_DIR)
cp('exports/stage3_v64/karakulina_discourse_markers_*.json', ARTIFACTS_DIR)

print('\n=== v64 pipeline COMPLETE ===')
print('Artifacts: %s' % ARTIFACTS_DIR)
