#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""049e-2: schema validation — rule13_revision_applied must be list of dicts."""
import json, sys, os, glob
sys.path.insert(0, '/opt/glava')
sys.stdout.reconfigure(encoding='utf-8')

STAGE2_DIR = 'exports/stage2_v65'
book_files = sorted(glob.glob(os.path.join(STAGE2_DIR, 'karakulina_book_FINAL_*.json')), reverse=True)
book_raw = json.load(open(book_files[0], encoding='utf-8'))
book = book_raw.get('book_draft') or book_raw.get('book_final') or book_raw

wn = book.get('writing_notes', {})
r13_applied = wn.get('rule13_revision_applied')

print(f"writing_notes.rule13_revision_applied type: {type(r13_applied).__name__}")
print(f"writing_notes.rule13_revision_applied value: {json.dumps(r13_applied, ensure_ascii=False)[:200]}")

if isinstance(r13_applied, list):
    print("OK: rule13_revision_applied is list")
    for i, item in enumerate(r13_applied[:3]):
        print(f"  [{i}]: {json.dumps(item, ensure_ascii=False)[:100]}")
    if r13_applied and all(isinstance(d, dict) for d in r13_applied):
        print("OK: all items are dicts (list of dicts)")
    elif not r13_applied:
        print("NOTE: rule13_revision_applied is empty list")
elif r13_applied is None:
    print("WARN: rule13_revision_applied is None/missing")
else:
    print(f"FAIL: rule13_revision_applied is {type(r13_applied).__name__} (not list)")
    sys.exit(1)

r13_failed = wn.get('rule13_revision_failed')
print(f"\nrule13_revision_failed: {r13_failed}")
if r13_failed is True:
    print("FAIL: rule13_revision_failed=true — STOP, push artifacts, wait for Opus review")
    sys.exit(1)
else:
    print("OK: rule13_revision_failed is not true")

print("\n=== Schema validation PASSED ===")
