import json, re
from pathlib import Path

RUN_DIR = Path('/opt/glava/exports/karakulina_v29_run_20260420_072506')

# Check Stage2 book structure more deeply
s2_path = RUN_DIR / 'karakulina_book_FINAL_20260420_072948.json'
data2 = json.loads(s2_path.read_text(encoding='utf-8'))
book2 = data2.get('book_final') or data2

# Print ALL keys
print("=== Stage2 book top-level keys:", list(data2.keys()))
print("=== chapter keys:", list(book2['chapters'][0].keys()))

print("\n=== ch_01 bio_data keys:", list(book2['chapters'][0].get('bio_data', {}).keys()))
bio = book2['chapters'][0].get('bio_data', {})
print("  personal:", bio.get('personal', ''))
print("  timeline:", bio.get('timeline', []))
print("  family count:", len(bio.get('family', [])))

# Check ch_02 content for historical-like blocks
ch02 = next(c for c in book2['chapters'] if (c.get('id') or c.get('chapter_id')) == 'ch_02')
content2 = ch02.get('content', '')
print(f"\n=== ch_02 content ({len(content2)} chars): first 200 chars:")
print(content2[:200])
print("...")
# Look for historical markers
hist_matches = re.findall(r'(ИСТОРИЧЕСКАЯ СПРАВКА|historical_note|hist_block|\[ИСТ\]|\*\*Историческая справка\*\*)', content2, re.I)
print(f"Historical markers in content: {hist_matches[:5]}")

# Check if paragraphs[] exists
for ch in book2['chapters']:
    cid = ch.get('id') or ch.get('chapter_id')
    paras = ch.get('paragraphs', [])
    if paras:
        print(f"\n{cid} paragraphs[]: {len(paras)}")
        for p in paras[:3]:
            print(f"  {p.get('id','?')}: type={p.get('type','?')} text={str(p.get('text',''))[:50]}")
