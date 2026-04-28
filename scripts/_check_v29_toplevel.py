import json
from pathlib import Path

RUN_DIR = Path('/opt/glava/exports/karakulina_v29_run_20260420_072506')
s2_path = RUN_DIR / 'karakulina_book_FINAL_20260420_072948.json'
data = json.loads(s2_path.read_text(encoding='utf-8'))
book = data.get('book_final') or data

print("=== Top-level historical_notes:", len(data.get('historical_notes', [])))
for h in data.get('historical_notes', [])[:5]:
    print(f"  [{h.get('id','?')}] chapter={h.get('chapter_id','?')} title={str(h.get('title',''))[:50]}")
    print(f"    content: {str(h.get('content',''))[:80]}")

print("\n=== chapter.timeline (ch_01):")
ch01 = next(c for c in book['chapters'] if (c.get('id') or c.get('chapter_id')) == 'ch_01')
print("  chapter keys:", list(ch01.keys()))
print("  chapter.timeline:", ch01.get('timeline', 'MISSING'))
print("  bio_data.timeline:", ch01.get('bio_data', {}).get('timeline', 'MISSING'))

# Phase B book
pb_path = sorted(RUN_DIR.glob('karakulina_v29_book_FINAL_phase_b_*.json'))[0]
data_pb = json.loads(pb_path.read_text(encoding='utf-8'))
book_pb = data_pb.get('book_final') or data_pb
print("\n=== Phase B top-level historical_notes:", len(data_pb.get('historical_notes', [])))
for h in data_pb.get('historical_notes', [])[:3]:
    print(f"  [{h.get('id','?')}] ch={h.get('chapter_id','?')} {str(h.get('title',''))[:50]}")
print("\n=== Phase B ch_01.timeline:", next(
    (c.get('timeline') for c in book_pb['chapters'] if (c.get('id') or c.get('chapter_id')) == 'ch_01'), 
    'ch_01 not found'))
