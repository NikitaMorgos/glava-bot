import json, re
from pathlib import Path

book_path = Path('/opt/glava/collab/runs/karakulina_v29_20260420_080739/book_FINAL_phase_b_v29.json')
data = json.loads(book_path.read_text(encoding='utf-8'))
book = data.get('book_final') or data

print("=== ch_01 full structure ===")
ch01 = next((c for c in book.get('chapters', []) if (c.get('id') or c.get('chapter_id')) == 'ch_01'), {})
print("keys:", list(ch01.keys()))

bio = ch01.get('bio_data') or {}
print("\nbio_data keys:", list(bio.keys()))
for key in ('personal', 'education', 'military', 'awards', 'family'):
    items = bio.get(key, [])
    print(f"  {key}: {len(items)} items")
    for it in items[:3]:
        print(f"    {it}")

tl = ch01.get('timeline') or bio.get('timeline') or []
print(f"\ntimeline ({len(tl)} stages):")
for t in tl[:4]:
    print(f"  {t.get('period','?')}: {t.get('title','?')[:50]}")

print("\n=== top-level historical_notes ===")
for h in data.get('historical_notes', []):
    print(f"  [{h.get('id')}] title='{h.get('title','')}' content={len(str(h.get('content','') or h.get('text','')))} chars")

print("\n=== ch_02.content bold/hist patterns ===")
ch02 = next((c for c in book.get('chapters', []) if (c.get('id') or c.get('chapter_id')) == 'ch_02'), {})
c2 = ch02.get('content', '')
for m in re.finditer(r'\*{2,3}[^*]{10,200}\*{2,3}', c2):
    stars = m.group(0)[:3].count('*')
    print(f"  ({'triple' if stars>=3 else 'double'}) {m.group(0)[:100]}")
