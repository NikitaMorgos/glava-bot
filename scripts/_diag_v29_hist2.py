import json, re
from pathlib import Path

book_path = Path('/opt/glava/collab/runs/karakulina_v29_20260420_080739/book_FINAL_phase_b_v29.json')
data = json.loads(book_path.read_text(encoding='utf-8'))
book = data.get('book_final') or data

# 1. Top-level historical_notes
top_hist = data.get('historical_notes', [])
print(f"=== top-level historical_notes: {len(top_hist)} ===")
for h in top_hist:
    title = h.get('title', '')
    content = h.get('content', '') or h.get('text', '')
    chapter_id = h.get('chapter_id', '')
    print(f"  [{h.get('id','?')}] ch={chapter_id} title='{title[:50]}'")
    print(f"    content: '{str(content)[:100]}'")

# 2. ch_02 content - look for **bold** historical text
ch02 = next((c for c in book.get('chapters', []) if (c.get('id') or c.get('chapter_id')) == 'ch_02'), {})
content2 = ch02.get('content', '')
print(f"\n=== ch_02 content ({len(content2)} chars) ===")

# Find **bold** patterns
bold_matches = re.findall(r'\*\*[^*]{10,200}\*\*', content2)
print(f"**bold** patterns found: {len(bold_matches)}")
for m in bold_matches[:10]:
    print(f"  {m[:100]}")

# Find ## headers
header_matches = re.findall(r'^#{1,3}\s+.+', content2, re.MULTILINE)
print(f"\n## headers in ch_02.content:")
for h in header_matches:
    print(f"  {h[:80]}")

# Print paragraphs containing historical-looking text
paragraphs = content2.split('\n\n')
print(f"\nTotal paragraphs in ch_02: {len(paragraphs)}")
for i, p in enumerate(paragraphs):
    if '1933' in p or '1941' in p or 'голод' in p.lower() or 'историческ' in p.lower():
        print(f"\n  p[{i}] ({len(p)} chars): {p[:150]}")
