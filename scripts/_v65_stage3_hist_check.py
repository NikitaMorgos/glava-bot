#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v65 Stage 3: check historical_notes distribution on revised book; enrich if needed."""
import json, sys, os, glob, time
sys.path.insert(0, '/opt/glava')
sys.stdout.reconfigure(encoding='utf-8')
from pipeline_utils import (
    enrich_historical_notes_inline,
    _count_inline_historical_notes,
    validate_historical_notes_distribution,
)

STAGE2_DIR = 'exports/stage2_v65'

# Find revised book (priority: _revised > _enriched > plain FINAL, skip draft)
candidates = sorted([
    f for f in glob.glob(os.path.join(STAGE2_DIR, 'karakulina_book_FINAL_*.json'))
    if 'draft' not in f
], reverse=True)

# Sort by priority: revised first
revised_files = [f for f in candidates if '_revised' in f]
enriched_files = [f for f in candidates if '_enriched' in f and '_revised' not in f]
plain_files = [f for f in candidates if '_revised' not in f and '_enriched' not in f]

book_file = (revised_files or enriched_files or plain_files)[0]
print(f"Input book: {book_file}")

book_raw = json.load(open(book_file, encoding='utf-8'))
book = book_raw.get('book_draft') or book_raw.get('book_final') or book_raw

# Load configs
hist_dist_cfg_path = 'collab/context/historical_notes_distribution_config.json'
hist_dist_cfg = json.load(open(hist_dist_cfg_path, encoding='utf-8')) if os.path.exists(hist_dist_cfg_path) else {}
enrich_cfg_path = 'collab/context/historical_notes_enrichment_config.json'
enrich_cfg = json.load(open(enrich_cfg_path, encoding='utf-8')) if os.path.exists(enrich_cfg_path) else {"min_inline_notes": 5}

# Check current distribution
inline_count = _count_inline_historical_notes(book)
field_count = len(book.get('historical_notes') or [])
print(f"Current: inline={inline_count}, field={field_count}")

r_dist = validate_historical_notes_distribution(book, hist_dist_cfg)
print(f"Distribution check: errors={r_dist['errors_count']}, warnings={r_dist['warnings_count']}")
for i in r_dist.get('issues', []):
    print(f"  [{i['severity']}] ch={i.get('chapter_id')} found={i.get('found')}/need={i.get('needed')}")

MIN_INLINE = enrich_cfg.get('min_inline_notes', 5)

if r_dist['warnings_count'] == 0 and inline_count >= MIN_INLINE:
    print(f"\nOK: distribution clean + inline_count={inline_count} >= {MIN_INLINE} — no enrichment needed")
    # Save symlink-style copy for Stage 3 input
    stage3_input_path = os.path.join(STAGE2_DIR, 'karakulina_book_stage3_input.json')
    import shutil
    shutil.copy2(book_file, stage3_input_path)
    print(f"Copied as stage3 input: {stage3_input_path}")
else:
    print(f"\nEnrichment needed: distribution_warnings={r_dist['warnings_count']}, inline={inline_count} < target {MIN_INLINE}")
    enriched_book = enrich_historical_notes_inline(book, enrich_cfg)
    inline_after = _count_inline_historical_notes(enriched_book)
    print(f"After enrichment: inline={inline_after}")

    ts = int(time.time())
    enriched_path = os.path.join(STAGE2_DIR, f'karakulina_book_FINAL_{ts}_enriched.json')
    json.dump(enriched_book, open(enriched_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f"Saved enriched: {enriched_path}")

    stage3_input_path = os.path.join(STAGE2_DIR, 'karakulina_book_stage3_input.json')
    import shutil
    shutil.copy2(enriched_path, stage3_input_path)
    print(f"Copied as stage3 input: {stage3_input_path}")

print(f"\nStage 3 input ready: {stage3_input_path}")
