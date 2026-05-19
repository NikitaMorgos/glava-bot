#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v65: diff audit — authorized vs unauthorized changes."""
import json, sys, os, glob
sys.path.insert(0, '/opt/glava')
sys.stdout.reconfigure(encoding='utf-8')
from pipeline_utils import audit_revision_diff

STAGE2_DIR = 'exports/stage2_v65'
draft_path = os.path.join(STAGE2_DIR, 'karakulina_book_draft.json')
hints_path = os.path.join(STAGE2_DIR, 'revision_hints.json')

book_files = sorted(glob.glob(os.path.join(STAGE2_DIR, 'karakulina_book_FINAL_*.json')), reverse=True)

book_draft_raw = json.load(open(draft_path, encoding='utf-8'))
book_draft = book_draft_raw.get('book_draft') or book_draft_raw.get('book_final') or book_draft_raw

revision_hints = json.load(open(hints_path, encoding='utf-8'))

book_revised_raw = json.load(open(book_files[0], encoding='utf-8'))
book_revised = book_revised_raw.get('book_draft') or book_revised_raw.get('book_final') or book_revised_raw

print("=== Running diff audit ===")
diff_result = audit_revision_diff(book_draft, book_revised, revision_hints)

json.dump(diff_result, open(os.path.join(STAGE2_DIR, 'revision_diff_audit.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(f"Saved: revision_diff_audit.json")

applied = diff_result.get('applied', [])
unauthorized = diff_result.get('unauthorized_changes', [])
print(f"\nDiff audit: hints_count={diff_result.get('hints_count')} applied={len(applied)} skipped={len(diff_result.get('skipped',[]))} unauthorized={len(unauthorized)}")

if applied:
    print("\napplied hints (first 5):")
    for a in applied[:5]:
        print(f"  hint_id={a.get('hint_id')} ch={a.get('chapter_id')}: {a.get('diff_summary','')[:80]}")

THRESHOLD = 5
if len(unauthorized) > THRESHOLD:
    print(f"\nFAIL: unauthorized_changes={len(unauthorized)} > threshold={THRESHOLD}")
    print("PER SPEC: STOP — push artifacts, wait for Opus review")
    for u in unauthorized[:5]:
        print(f"  ch={u.get('chapter_id')}: '{u.get('diff_snippet','')[:80]}'")
    sys.exit(1)
else:
    print(f"\nOK: unauthorized_changes={len(unauthorized)} <= threshold={THRESHOLD}")

# writing_notes rule13 proof
wn = book_revised.get('writing_notes', {})
r13_applied = wn.get('rule13_revision_applied')
print(f"\n=== 049e-2 writing_notes.rule13 proof ===")
print(f"  rule13_revision_applied: type={type(r13_applied).__name__} len={len(r13_applied) if isinstance(r13_applied, list) else 'n/a'}")
print(f"  rule13_hints_received: {wn.get('rule13_hints_received', 'MISSING')}")
print(f"  rule13_errors_applied: {wn.get('rule13_errors_applied', 'MISSING')}")
print(f"  rule13_warnings_applied: {wn.get('rule13_warnings_applied', 'MISSING')}")
print(f"  rule13_revision_failed: {wn.get('rule13_revision_failed', 'MISSING')}")
if isinstance(r13_applied, list) and r13_applied:
    print(f"  First entry: {json.dumps(r13_applied[0], ensure_ascii=False)[:150]}")

print("\n=== Diff audit + rule13 schema: DONE ===")
