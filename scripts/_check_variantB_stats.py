#!/usr/bin/env python3
import json
from pathlib import Path

RUN = Path('/opt/glava/exports/karakulina_full_20260413_075342')

s3 = Path('/opt/glava/exports/karakulina_book_FINAL_stage3_20260413_082302.json')
pb = RUN / 'karakulina_book_FINAL_phase_b_20260413_084014.json'

def stats(p, label):
    d = json.loads(p.read_text())
    b = d.get('book_final') or d
    chs = b.get('chapters', [])
    total = sum(len(c.get('content') or '') for c in chs)
    print(f"\n=== {label} ===")
    print(f"Глав: {len(chs)}, итого: {total:,} симв")
    for c in chs:
        cid = c.get('id') or c.get('chapter_id', '?')
        title = c.get('title', '')[:40]
        chars = len(c.get('content') or '')
        print(f"  {cid}: {title} | {chars:,}")
    return total

t1 = stats(s3, 'Stage3 — основа (только TR1)')
t2 = stats(pb, 'Phase B — финал (TR2 добавлен)')
diff = t2 - t1
pct = (t2 / t1 - 1) * 100 if t1 else 0
print(f"\nРост от Phase B: {diff:+,} симв ({pct:+.1f}%)")
