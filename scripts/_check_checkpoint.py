import json, sys
from pathlib import Path

ckpt_path = Path('/opt/glava/checkpoints/karakulina/proofreader.json')
d = json.loads(ckpt_path.read_text(encoding='utf-8'))
print('version:', d.get('version'))
print('keys:', list(d.keys())[:6])

book = d.get('book_final') or d
chs = book.get('chapters', [])
print('chapters:', [c.get('id') or c.get('chapter_id') for c in chs])

ch01 = next((c for c in chs if (c.get('id') or c.get('chapter_id')) == 'ch_01'), {})
tl = ch01.get('timeline') or []
print('ch01 timeline len:', len(tl))
if tl:
    for t in tl[:3]:
        print(f"  {t.get('period','?')}: {t.get('title','?')[:50]}")
print('ch01 bio_data keys:', list((ch01.get('bio_data') or {}).keys()))

# Check top-level historical_notes
top_hist = d.get('historical_notes', [])
print('\ntop-level historical_notes:', len(top_hist))
for h in top_hist[:3]:
    print(f"  [{h.get('id','?')}] ch={h.get('chapter_id','?')} title={str(h.get('title',''))[:50]}")
    print(f"    content: {str(h.get('content',''))[:80]}")
