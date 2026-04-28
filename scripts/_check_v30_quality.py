import json, re
path = '/opt/glava/collab/runs/karakulina_v30_20260420_122027/book_FINAL_phase_b_v30.json'
d = json.load(open(path))
book = d.get('book_final') or d
chs = book.get('chapters', [])
print('Chapters:', [c.get('id') or c.get('chapter_id') for c in chs])

ch01 = next((c for c in chs if (c.get('id') or c.get('chapter_id')) == 'ch_01'), {})
bio = ch01.get('bio_data') or {}
print('bio_data keys:', list(bio.keys()))
for k in ('personal', 'education', 'military', 'awards', 'family'):
    print(f'  {k}: {len(bio.get(k, []))} items')
tl = ch01.get('timeline') or bio.get('timeline') or []
print(f'timeline: {len(tl)} stages')

hn = d.get('historical_notes', [])
print(f'\nhistorical_notes: {len(hn)} items')
for h in hn:
    print(f"  [{h.get('id')}] title={repr(h.get('title','')[:60])}")

ch02 = next((c for c in chs if (c.get('id') or c.get('chapter_id')) == 'ch_02'), {})
c2 = ch02.get('content', '')
triple = re.findall(r'\*{3}.{10,200}\*{3}', c2)
print(f'\ntriple-asterisk in ch02.content: {len(triple)}')
vyk = 'выков' in c2.lower()
sym = 'символ' in c2.lower() and 'выков' in c2.lower()
print(f'выков in ch02.content: {vyk}')
print(f'выков+символ combo: {sym}')

# Check consecutive hist notes in layout proximity
# just count how many hist notes exist and their year_reference
for h in hn:
    print(f"  yr={h.get('year_reference','?')} | {str(h.get('content',''))[:80]}")
