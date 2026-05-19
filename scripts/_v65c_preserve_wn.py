#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v65c: preserve writing_notes.rule13_revision_applied after Stage 3."""
import json, sys, os, glob
sys.path.insert(0, '/opt/glava')
sys.stdout.reconfigure(encoding='utf-8')
from pipeline_utils import preserve_root_level_metadata

V65C_DIR = 'exports/stage2_v65c'
STAGE3C_DIR = 'exports/stage3_v65c'

# Source: v65c revised book
source_path = os.path.join(V65C_DIR, 'karakulina_book_FINAL_v65c_revised.json')
if not os.path.exists(source_path):
    print('ERROR: v65c revised book not found'); sys.exit(1)

# Stage3 output
s3_files = sorted(glob.glob(os.path.join(STAGE3C_DIR, 'karakulina_book_FINAL_stage3_*.json')), reverse=True)
if not s3_files:
    print('ERROR: no stage3_v65c output found'); sys.exit(1)

print('=== 049g: preserve_writing_notes (v65c) ===')
book_s2 = json.load(open(source_path, encoding='utf-8'))
book_s2 = book_s2.get('book_draft') or book_s2.get('book_final') or book_s2

book_s3_raw = json.load(open(s3_files[0], encoding='utf-8'))
book_s3 = book_s3_raw.get('book_draft') or book_s3_raw.get('book_final') or book_s3_raw

wn_before = book_s3.get('writing_notes', {})
print('  writing_notes in stage3 (before): %s' % bool(wn_before))

book_s3 = preserve_root_level_metadata(book_s3, book_s2)

wn_after = book_s3.get('writing_notes', {})
r13 = wn_after.get('rule13_revision_applied')
print('  rule13_revision_applied: type=%s' % type(r13).__name__)
if isinstance(r13, list):
    print('  OK: list count=%d' % len(r13))
else:
    print('  WARN: not a list')

# Save back to stage3 output
json.dump(book_s3_raw.__class__(book_s3) if hasattr(book_s3_raw, '__class__') else book_s3,
          open(s3_files[0], 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

# Actually: s3_raw might be wrapped - write correctly
result = dict(book_s3_raw)
# Replace the book content
for k in ['book_draft', 'book_final']:
    if k in result:
        result[k] = book_s3
        break
else:
    result = book_s3
json.dump(result, open(s3_files[0], 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('Saved: %s' % s3_files[0])
print('=== 049g preserve_writing_notes v65c: APPLIED ===')
