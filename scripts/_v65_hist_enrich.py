#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""046d: historical_notes enrichment (post-revision)."""
import json, sys, os, glob, time
sys.path.insert(0, '/opt/glava')
sys.stdout.reconfigure(encoding='utf-8')
from pipeline_utils import enrich_historical_notes_inline, _count_inline_historical_notes

STAGE2_DIR = 'exports/stage2_v65'

book_files = sorted(glob.glob(os.path.join(STAGE2_DIR, 'karakulina_book_FINAL_*.json')), reverse=True)
# Skip enriched/draft files
book_files = [f for f in book_files if '_enriched' not in f and 'draft' not in f]
book_raw = json.load(open(book_files[0], encoding='utf-8'))
book = book_raw.get('book_draft') or book_raw.get('book_final') or book_raw

enrich_cfg_path = 'collab/context/historical_notes_enrichment_config.json'
if not os.path.exists(enrich_cfg_path):
    print(f"WARNING: {enrich_cfg_path} not found — using defaults")
    enrich_cfg = {"min_inline_notes": 5}
else:
    enrich_cfg = json.load(open(enrich_cfg_path, encoding='utf-8'))

print("=== 046d: historical_notes enrichment ===")
before_count = _count_inline_historical_notes(book)
print(f"  inline historical notes before enrichment: {before_count}")

enriched_book = enrich_historical_notes_inline(book, enrich_cfg)
after_count = _count_inline_historical_notes(enriched_book)
print(f"  inline historical notes after enrichment: {after_count}")

MIN_INLINE = enrich_cfg.get('min_inline_notes', 5)
if after_count < MIN_INLINE:
    print(f"  WARNING: {after_count} inline notes < target {MIN_INLINE}")
else:
    print(f"  OK: {after_count} inline notes >= target {MIN_INLINE}")

ts = int(time.time())
enriched_path = os.path.join(STAGE2_DIR, f'karakulina_book_FINAL_{ts}_enriched.json')
json.dump(enriched_book, open(enriched_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(f"\nSaved enriched book: {enriched_path}")
