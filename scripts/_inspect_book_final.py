import json
from pathlib import Path

ROOT = Path('/opt/glava')
d = json.load(open(ROOT / 'exports/karakulina_proofreader_report_20260329_065332.json'))

print('TOP KEYS:', list(d.keys()))
print()
chapters = d.get('chapters', [])
print(f'chapters: {len(chapters)}')
for ch in chapters:
    print(f"  - id={ch.get('id')} title={ch.get('title')} content_len={len(ch.get('content',''))} chars")
    sub = ch.get('sub_chapters', ch.get('sections', []))
    for s in sub:
        print(f"      sub: {s.get('title','?')} {len(s.get('content',''))} chars")

print()
for key in d.keys():
    if key != 'chapters':
        val = d[key]
        if isinstance(val, list):
            print(f'{key}: list of {len(val)}')
        elif isinstance(val, dict):
            print(f'{key}: dict keys={list(val.keys())[:5]}')
        else:
            print(f'{key}: {str(val)[:80]}')
