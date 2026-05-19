#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""049g: verify + apply preserve_writing_notes in stage3 output."""
import json, sys, os, glob
sys.path.insert(0, '/opt/glava')
sys.stdout.reconfigure(encoding='utf-8')
from pipeline_utils import preserve_root_level_metadata

STAGE3_DIR = 'exports/stage3_v65'
STAGE2_DIR = 'exports/stage2_v65'

book_files = sorted(glob.glob(os.path.join(STAGE3_DIR, 'karakulina_book_FINAL_stage3_*.json')), reverse=True)
if not book_files:
    print("ERROR: stage3 output not found"); sys.exit(1)

book_s3_raw = json.load(open(book_files[0], encoding='utf-8'))
book_s3 = book_s3_raw.get('book_draft') or book_s3_raw.get('book_final') or book_s3_raw

# Source writing_notes from last stage2 revised (skip enriched/draft)
stage2_files = sorted(glob.glob(os.path.join(STAGE2_DIR, 'karakulina_book_FINAL_*.json')), reverse=True)
stage2_files = [f for f in stage2_files if '_enriched' not in f and 'draft' not in f]
book_s2_raw = json.load(open(stage2_files[0], encoding='utf-8'))
book_s2 = book_s2_raw.get('book_draft') or book_s2_raw.get('book_final') or book_s2_raw

print("=== 049g: preserve_writing_notes ===")
wn_before = book_s3.get('writing_notes')
print(f"  writing_notes in stage3 output (before preserve): {bool(wn_before)} — {str(wn_before)[:100]}")

preserved = preserve_root_level_metadata(book_s3, book_s2)
wn_after = preserved.get('writing_notes', {})
print(f"  writing_notes after preserve_root_level_metadata: keys={list(wn_after.keys())[:8]}")

r13 = wn_after.get('rule13_revision_applied')
print(f"  rule13_revision_applied preserved: type={type(r13).__name__} value={json.dumps(r13, ensure_ascii=False)[:150] if r13 else 'None'}")

if not isinstance(r13, list):
    print(f"  WARN: rule13_revision_applied not a list in stage3 output")
else:
    print(f"  OK: rule13_revision_applied is list in stage3 output")

# Always apply preserve to ensure writing_notes are present
json.dump(preserved, open(book_files[0], 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(f"\nSaved preserved stage3: {book_files[0]}")
print("\n=== 049g preserve_writing_notes: APPLIED ===")
