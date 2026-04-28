import json
from pathlib import Path

RUN_DIR = Path('/opt/glava/exports/karakulina_v29_run_20260420_072506')

# Check Stage2 book for historical_notes
s2_path = RUN_DIR / 'karakulina_book_FINAL_20260420_072948.json'
data2 = json.loads(s2_path.read_text(encoding='utf-8'))
book2 = data2.get('book_final') or data2
print('=== Stage 2 book ===')
for ch in book2.get('chapters', []):
    cid = ch.get('id') or ch.get('chapter_id', '?')
    hist = ch.get('historical_notes', [])
    bio = ch.get('bio_data')
    tl = bio.get('timeline', []) if bio else []
    callouts = ch.get('callouts', data2.get('callouts', []))
    print(f"{cid}: hist={len(hist)} bio={'Y' if bio else 'N'} tl={len(tl)}")
    if hist:
        for h in hist[:2]:
            print(f"  hist: {str(h.get('title',''))[:60]}")

# Top-level callouts
top_callouts = data2.get('callouts', [])
print(f"\nTop-level callouts: {len(top_callouts)}")

# Check Phase B book
pb_path = sorted(RUN_DIR.glob('karakulina_v29_book_FINAL_phase_b_*.json'), 
                 key=lambda p: p.stat().st_mtime, reverse=True)[0]
data_pb = json.loads(pb_path.read_text(encoding='utf-8'))
book_pb = data_pb.get('book_final') or data_pb
print(f"\n=== Phase B book ===")
top_callouts_pb = data_pb.get('callouts', [])
print(f"Top-level callouts: {len(top_callouts_pb)}")
for ch in book_pb.get('chapters', []):
    cid = ch.get('id') or ch.get('chapter_id', '?')
    bio = ch.get('bio_data')
    tl = bio.get('timeline', []) if bio else []
    print(f"{cid}: bio={'Y(tl='+str(len(tl))+')' if bio else 'N'} hist={len(ch.get('historical_notes',[]))}")
