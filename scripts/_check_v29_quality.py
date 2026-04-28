import json
from pathlib import Path

EXPORTS = Path('/opt/glava/exports')
RUN_DIR = EXPORTS / 'karakulina_v29_run_20260420_072506'

# Find the Phase B book
book_path = sorted(RUN_DIR.glob('karakulina_v29_book_FINAL_phase_b_*.json'), 
                   key=lambda p: p.stat().st_mtime, reverse=True)[0]
data = json.loads(book_path.read_text(encoding='utf-8'))
book = data.get('book_final') or data
chapters = book.get('chapters', [])

print(f"Book: {book_path.name}")
print(f"Total chars: {sum(len(c.get('content','')) for c in chapters):,}")

for ch in chapters:
    cid = ch.get('id') or ch.get('chapter_id', '?')
    content = ch.get('content') or ''
    bio = ch.get('bio_data')
    hist = ch.get('historical_notes', [])
    callouts = ch.get('callouts', [])
    tl = ch.get('timeline') or (bio.get('timeline') if bio else None) or []
    print(f"\n--- {cid} ---")
    print(f"  content: {len(content):,} chars")
    print(f"  bio_data: {'YES' if bio else 'NO'}")
    if bio:
        print(f"    sections: {list(bio.keys())}")
        family = bio.get('family', [])
        print(f"    family members: {len(family)}")
        tl2 = bio.get('timeline', [])
        print(f"    timeline in bio_data: {len(tl2)} stages")
        if tl2:
            for t in tl2[:4]:
                print(f"      {t.get('period','?')}: {t.get('title','?')[:50]}")
    print(f"  standalone timeline: {len(tl) if not (bio and bio.get('timeline')) else 'in bio_data'}")
    print(f"  historical_notes: {len(hist)}")
    if hist:
        for h in hist[:3]:
            print(f"    [{h.get('id','?')}] {str(h.get('title',''))[:60]}")
    print(f"  callouts: {len(callouts)}")
