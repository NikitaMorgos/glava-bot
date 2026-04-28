import json, glob

fc3 = sorted(glob.glob('/opt/glava/exports/karakulina_v32_run_*/karakulina_fc_report_iter3_*.json'))[-1]
r = json.load(open(fc3, encoding='utf-8'))
print(f"FC iter3 keys: {list(r.keys())}")
print(f"verdict: {r.get('verdict')}")
print(f"errors: {len(r.get('errors', []))}")
print(f"warnings: {len(r.get('warnings', []))}")
print()
for w in r.get('warnings', []):
    print("WARNING:", json.dumps(w, ensure_ascii=False)[:200])
print()
print("stats:", json.dumps(r.get('stats', {}), ensure_ascii=False)[:300])
print()

# Check if this FC got ch_01 at all
full = json.dumps(r, ensure_ascii=False)
print(f"'ch_01' in report: {'ch_01' in full}")
print(f"'timeline' in report: {'timeline' in full}")
print(f"'historical_notes' in report: {'historical_notes' in full}")
print(f"'раздражал' in report: {'раздражал' in full}")

# Check affected_chapters if any
ac = r.get('affected_chapters', [])
print(f"\naffected_chapters in report: {ac}")

# Check what chapters were checked
checks = r.get('chapter_checks', {})
print(f"chapter_checks keys: {list(checks.keys())}")

# Now check the actual book at iter3
book_path = sorted(glob.glob('/opt/glava/exports/karakulina_v32_run_*/karakulina_book_draft_v4_*.json'))
if book_path:
    book = json.load(open(book_path[-1], encoding='utf-8'))
    chapters = book.get('chapters', [])
    for ch in chapters:
        cid = ch.get('id', '?')
        timeline = ch.get('timeline', ch.get('bio_data', {}).get('timeline', []) if ch.get('bio_data') else [])
        hn = ch.get('historical_notes', [])
        content_len = len(ch.get('content') or '')
        print(f"\n{cid}: content={content_len} chars, timeline={len(timeline) if isinstance(timeline,list) else '?'}, hist_notes={len(hn)}")
        if hn:
            for h in hn[:2]:
                print(f"  hist_note: title='{h.get('title','')}' content_len={len(h.get('content',''))}")
else:
    print("\nNo book_draft_v4 found")
