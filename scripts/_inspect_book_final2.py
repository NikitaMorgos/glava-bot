import json
from pathlib import Path

ROOT = Path('/opt/glava')
d = json.load(open(ROOT / 'exports/karakulina_proofreader_report_20260329_065332.json'))

# Структура ch_01 и ch_02
for ch_id in ('ch_01', 'ch_02'):
    ch = next(c for c in d['chapters'] if c['id'] == ch_id)
    print(f"\n=== {ch_id}: {ch['title']} ===")
    content = ch.get('content', '')
    print(content[:600])
    print('...')
    # Sub-sections?
    for k in ch.keys():
        if k not in ('id', 'title', 'content'):
            print(f'  extra field: {k} = {str(ch[k])[:100]}')

print('\n=== callouts sample ===')
for co in d.get('callouts', [])[:2]:
    print(json.dumps(co, ensure_ascii=False)[:200])

print('\n=== historical_notes sample ===')
for hn in d.get('historical_notes', [])[:2]:
    print(json.dumps(hn, ensure_ascii=False)[:200])
