"""v64: Stage 2 revision pass — call GW v2.23 with revision_hints (ПРАВИЛО 13)."""
import json, sys, os, glob
from datetime import datetime
sys.path.insert(0, '/opt/glava')
from pipeline_utils import (
    load_config, load_prompt, parse_pin_list_from_markdown, audit_revision_diff
)
import anthropic

# Load artifacts
book_files = sorted(glob.glob('exports/stage2_v64/karakulina_book_FINAL_*.json'), reverse=True)
fm_files = sorted(glob.glob('exports/karakulina_v64/karakulina_fact_map_full_*.json'), reverse=True)
hints_path = 'exports/stage2_v64/revision_hints.json'

print('Book draft:', book_files[0])
print('FM:', fm_files[0])

book_raw = json.load(open(book_files[0], encoding='utf-8'))
book_draft = book_raw.get('book_draft') or book_raw.get('book_final') or book_raw
fm = json.load(open(fm_files[0], encoding='utf-8'))
revision_hints = json.load(open(hints_path, encoding='utf-8'))
print('Revision hints: %d total, %d must_apply' % (
    len(revision_hints), len([h for h in revision_hints if h.get('must_apply')])
))

if not revision_hints:
    print('No hints — skipping revision pass')
    json.dump({"skipped": "no_revision_hints"}, open('exports/stage2_v64/revision_pass_log.json', 'w', encoding='utf-8'))
    sys.exit(0)

# Load config and GW prompt
cfg = load_config()
gw_cfg = cfg['ghostwriter']
model = gw_cfg['model']
max_tokens = gw_cfg['max_tokens']
temperature = gw_cfg.get('temperature', 0.5)
system_prompt = load_prompt(gw_cfg['prompt_file'])

print('GW: %s | %s' % (gw_cfg['prompt_file'], model))

# Load pin_list and transcripts
pin_list = parse_pin_list_from_markdown('collab/context/known_episodes_karakulina.md')
tr_files = sorted(glob.glob('collab/transcripts/*.txt'))
transcripts = []
for f in tr_files[:2]:
    transcripts.append({'filename': os.path.basename(f), 'text': open(f, encoding='utf-8').read()})

# Build ПРАВИЛО 13 revision user message
user_message = {
    'phase': 'B',
    'call_type': 'revision',
    'project_id': 'karakulina',
    'subject': {'name': 'Каракулина Валентина Ивановна'},
    'fact_map': fm,
    'transcripts': transcripts,
    'current_book': book_draft,
    'revision_scope': {
        'type': 'rule13_revision_hints',
        'affected_chapters': list(set(h.get('chapter_id') for h in revision_hints if h.get('chapter_id'))),
        'instructions': (
            'Выполни revision по ПРАВИЛО 13. '
            'Исправь ТОЛЬКО flagged sentences из revision_hints. '
            'Все остальные главы и параграфы — НЕ МЕНЯТЬ (ПРАВИЛО 0 SCOPE LOCK).'
        )
    },
    'revision_hints': revision_hints,
    'pin_list': pin_list,
}

print('\n=== Running GW revision pass (ПРАВИЛО 13) ===')
print('Hints to apply:')
for h in revision_hints:
    print('  [%s] %s/%s ch=%s must_apply=%s' % (
        h['hint_id'], h['validator'], h['category'], h['chapter_id'], h['must_apply']
    ))
    print('    suggestion: %s' % h.get('suggestion', '')[:100])

client = anthropic.Anthropic()

start = datetime.now()
raw_parts = []
with client.messages.stream(
    model=model,
    max_tokens=max_tokens,
    temperature=temperature,
    system=system_prompt,
    messages=[{'role': 'user', 'content': json.dumps(user_message, ensure_ascii=False)}]
) as stream:
    for text in stream.text_stream:
        raw_parts.append(text)
        print(text, end='', flush=True)

elapsed = (datetime.now() - start).total_seconds()
raw_response = ''.join(raw_parts)
print('\n\n[GW REVISION] Done in %.1fs | %d chars' % (elapsed, len(raw_response)))

# Parse response
import re
json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
if json_match:
    try:
        book_revised = json.loads(json_match.group())
        print('[GW REVISION] Parsed JSON OK')
    except json.JSONDecodeError as e:
        print('[GW REVISION] JSON parse error: %s' % e)
        # Save raw for debugging
        open('exports/stage2_v64/revision_raw_response.txt', 'w', encoding='utf-8').write(raw_response)
        sys.exit(1)
else:
    print('[GW REVISION] No JSON found in response')
    open('exports/stage2_v64/revision_raw_response.txt', 'w', encoding='utf-8').write(raw_response)
    sys.exit(1)

# Save revised book
ts = datetime.now().strftime('%Y%m%d_%H%M%S')
revised_path = 'exports/stage2_v64/karakulina_book_REVISED_%s.json' % ts
json.dump(book_revised, open(revised_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('Saved: %s' % revised_path)

# Show writing_notes for rule13 proof
writing_notes = book_revised.get('writing_notes', {})
print('\n=== writing_notes (ПРАВИЛО 13 proof) ===')
for k, v in writing_notes.items():
    if 'rule13' in k:
        print('  %s: %s' % (k, v))

# Diff audit
print('\n=== Diff audit ===')
diff = audit_revision_diff(book_draft, book_revised, revision_hints)
print('hints_count: %d' % diff.get('hints_count', 0))
print('applied: %d' % len(diff.get('applied', [])))
print('skipped: %d' % len(diff.get('skipped', [])))
print('unauthorized_changes: %d' % len(diff.get('unauthorized_changes', [])))
json.dump(diff, open('exports/stage2_v64/revision_diff_audit.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('Saved: revision_diff_audit.json')

# Check stop condition
if writing_notes.get('rule13_revision_failed'):
    print('\nFAIL: rule13_revision_failed=true — STOP per spec')
    sys.exit(1)
if len(diff.get('unauthorized_changes', [])) > 5:
    print('\nFAIL: unauthorized_changes=%d > threshold=5 — STOP per spec' % len(diff.get('unauthorized_changes', [])))
    sys.exit(1)

print('\n=== Revision pass COMPLETE ===')
print('Revised book: %s' % revised_path)
