#!/usr/bin/env python3
import json
from pathlib import Path

pb = Path('/opt/glava/exports/karakulina_full_20260412_163805/karakulina_book_FINAL_phase_b_20260412_165653.json')
s3 = Path('/opt/glava/exports/karakulina_full_20260412_163805/karakulina_book_FINAL_stage3_20260412_165258.json')

def book_stats(path, label):
    data = json.loads(path.read_text())
    book = data.get('book_final') or data
    chapters = book.get('chapters', [])
    total = 0
    print(f"\n=== {label} ===")
    print(f"Глав: {len(chapters)}")
    for ch in chapters:
        cid = ch.get('id') or ch.get('chapter_id', '?')
        title = ch.get('title', '')[:50]
        content = ch.get('content') or ''
        total += len(content)
        print(f"  {cid}: {title} | {len(content):,} симв")
    print(f"Итого: {total:,} симв")
    return total

t_s3 = book_stats(s3, "Stage3 (до Phase B)")
t_pb = book_stats(pb, "Phase B (финал)")
print(f"\nРост: {t_pb - t_s3:+,} симв ({(t_pb/t_s3-1)*100:+.1f}%)" if t_s3 else "")
