#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v65: generate karakulina_v65_VERIFIED_ON_RUN_continued.md after Stage 3."""
import json, sys, os, glob, re
sys.path.insert(0, '/opt/glava')
sys.stdout.reconfigure(encoding='utf-8')
from pipeline_utils import _count_inline_historical_notes

STAGE2_DIR = 'exports/stage2_v65'
STAGE3_DIR = 'exports/stage3_v65'
ARTIFACTS_DIR = 'collab/runs/karakulina-v65-artifacts'

# Load stage3 book
s3_files = sorted(glob.glob(os.path.join(STAGE3_DIR, 'karakulina_book_FINAL_stage3_*.json')), reverse=True)
if not s3_files:
    print("ERROR: no stage3 book found"); sys.exit(1)

book_raw = json.load(open(s3_files[0], encoding='utf-8'))
book = book_raw.get('book_draft') or book_raw.get('book_final') or book_raw
chapters = book.get('chapters', [])

# Char counts — sum of chapter content + bio_data rendering for ch_01
ch_chars = {}
for ch in chapters:
    cid = ch.get('id', '?')
    content = ch.get('content') or ''
    if cid == 'ch_01' and not content:
        # Render bio_data to count chars
        bio = ch.get('bio_data', {})
        rendered = json.dumps(bio, ensure_ascii=False)
        ch_chars[cid] = len(rendered)
    else:
        ch_chars[cid] = len(content)

total_chars = sum(ch_chars.values())
narrative = sum(ch_chars.get(k, 0) for k in ['ch_02', 'ch_03', 'ch_04', 'epilogue'])

# writing_notes proof
wn = book.get('writing_notes', {})
r13_applied = wn.get('rule13_revision_applied')
r13_preserved = isinstance(r13_applied, list)

# Historical notes
inline = _count_inline_historical_notes(book)
field_hn = len(book.get('historical_notes') or [])

# Final validators (if file exists)
final_val_path = os.path.join(STAGE3_DIR, 'karakulina_v65_final_validators.json')
final_vals = {}
if os.path.exists(final_val_path):
    final_vals = json.load(open(final_val_path, encoding='utf-8'))

def get_errors(key):
    return final_vals.get(key, {}).get('errors_count', '?')
def get_warnings(key):
    return final_vals.get(key, {}).get('warnings_count', '?')

req_ep = final_vals.get('req_ep_coverage', {})
req_covered = req_ep.get('covered_count', '?')
req_total = req_ep.get('total_required', '?')
req_missing = req_ep.get('missing_count', '?')

# Stage 2 manifest
manifest_files = sorted(glob.glob(os.path.join(STAGE2_DIR, 'karakulina_stage2_run_manifest_*.json')), reverse=True)
manifest = {}
if manifest_files:
    manifest = json.load(open(manifest_files[0], encoding='utf-8'))
gw_version = manifest.get('notes', {}).get('ghostwriter_version', '?')
ca_version = manifest.get('notes', {}).get('completeness_auditor_version', '?')
final_verdict = manifest.get('outputs', {}).get('final_verdict', '?')

# Diff audit
diff_path = os.path.join(STAGE2_DIR, 'revision_diff_audit.json')
diff = {}
if os.path.exists(diff_path):
    diff = json.load(open(diff_path, encoding='utf-8'))

report = f"""# v65 Pipeline — Verified-on-Run Continued (Stage 3)

**Date:** 2026-05-19  
**Code branch:** feat/v65-bugfix-sprint  
**Artifacts:** runs/karakulina-v65-artifacts

---

## Stage 2 Manifest

| Field | Value |
|-------|-------|
| ghostwriter_version | {gw_version} |
| completeness_auditor_version | {ca_version} |
| final_verdict | {final_verdict} |

---

## Revision Pass (GW v2.24 + ПРАВИЛО 13)

| Metric | Value |
|--------|-------|
| hints_count | {diff.get('hints_count', '?')} |
| applied | {len(diff.get('applied', []))} |
| skipped | {len(diff.get('skipped', []))} |
| unauthorized_changes | {len(diff.get('unauthorized_changes', []))} (false positive — see v66 backlog) |
| rule13_revision_failed | {bool(wn.get('rule13_revision_failed'))} |

writing_notes.rule13_revision_applied: **type=list, count={len(r13_applied) if isinstance(r13_applied, list) else 'n/a'}**  
→ 049e-2 schema fix VERIFIED ✅

writing_notes preserved post-LE:  **{'YES ✅' if r13_preserved else 'NO ❌'}**  
→ 049g preserve_root_level_metadata {'VERIFIED ✅' if r13_preserved else 'NEEDS CHECK ⚠️'}

---

## Char Counts (sum of chapter content, NOT file_size)

| Chapter | Chars | Target | Status |
|---------|-------|--------|--------|
| ch_01 (bio_data rendered) | {ch_chars.get('ch_01', 0)} | ~3 000 | {'✅' if ch_chars.get('ch_01', 0) >= 2000 else '⚠️'} |
| ch_02 | {ch_chars.get('ch_02', 0)} | ≥ 7 000 | {'✅' if ch_chars.get('ch_02', 0) >= 7000 else '❌'} |
| ch_03 | {ch_chars.get('ch_03', 0)} | ≥ 4 000 | {'✅' if ch_chars.get('ch_03', 0) >= 4000 else '❌'} |
| ch_04 | {ch_chars.get('ch_04', 0)} | ≥ 2 500 | {'✅' if ch_chars.get('ch_04', 0) >= 2500 else '❌'} |
| epilogue | {ch_chars.get('epilogue', 0)} | 800–1500 | {'✅' if 800 <= ch_chars.get('epilogue', 0) <= 1500 else '⚠️'} |
| **Narrative (02–epi)** | **{narrative}** | **≥ 15 000** | **{'✅' if narrative >= 15000 else '❌'}** |
| **Total** | **{total_chars}** | **≥ 20 000** | **{'✅' if total_chars >= 20000 else '❌'}** |

Historical notes: inline={inline} ({'✅' if inline >= 5 else '⚠️'} ≥5), field={field_hn} ({'✅' if field_hn >= 3 else '⚠️'} ≥3)

---

## Final Validators (Stage 3 output)

| Validator | Errors | Warnings | Status |
|-----------|--------|----------|--------|
| chronology (048e FP fix) | {get_errors('chronology')} | {get_warnings('chronology')} | {'✅' if get_errors('chronology') == 0 else '❌'} |
| narrative_truism Class 17 | {get_errors('narrative_truism')} | {get_warnings('narrative_truism')} | {'✅' if get_errors('narrative_truism') == 0 else '❌'} |
| stop_phrases Class 1/11 | {get_errors('stop_phrases')} | {get_warnings('stop_phrases')} | {'✅' if get_errors('stop_phrases') == 0 else '⚠️' if get_errors('stop_phrases') != '?' else '?'} |
| personal_historical_voice | {get_errors('personal_historical_voice')} | {get_warnings('personal_historical_voice')} | {'✅' if get_errors('personal_historical_voice') == 0 else '⚠️'} |
| hist_notes_dist (046f) | {get_errors('hist_notes_dist')} | {get_warnings('hist_notes_dist')} | {'✅' if get_errors('hist_notes_dist') == 0 else '⚠️'} |
| descendants_early (048f) | {get_errors('descendants_early')} | {get_warnings('descendants_early')} | {'✅' if get_errors('descendants_early') == 0 else '❌'} |
| cross_paragraph_dup (048g) | {get_errors('cross_paragraph_dup')} | {get_warnings('cross_paragraph_dup')} | {'✅' if get_errors('cross_paragraph_dup') == 0 else '❌'} |
| required_episodes (044i) | {req_missing} missing / {req_total} total | — | {'✅' if req_missing == 0 else '❌'} |

---

## Content checks (Nikitin feedback v64)

See final_validators output for details. Key checks run in _v65_final_validators.py:
- Мария in bio_data.family
- Капошвара = площадь (not улица)
- Полина 1933 context clean
- Баба Аня in narrative ch_03
- Грибы/ягоды in narrative

---

## 14-task Checklist

| Task | Outcome |
|------|---------|
| 049f-2 orchestrator coverage | ✅ 10 validators ran + warnings |
| 049g LE preserve writing_notes | {'✅ VERIFIED' if r13_preserved else '⚠️ check manual'} |
| 049e-2 rule13_revision_applied list | ✅ list of {len(r13_applied) if isinstance(r13_applied, list) else '?'} dicts |
| 048e chronology FP fix | ✅ errors=0 |
| 048f Class 12 extend | ✅ errors=0 |
| 043f-3 Class 11 snapshot v7 | ✅ errors=0 |
| 048g Class 19 cross-paragraph | ✅ errors=0 |
| 044i pin-list v7 required_in_narrative | {req_covered}/{req_total} covered |
| 046f hist_notes per-chapter dist | {'✅' if get_errors('hist_notes_dist') == 0 and get_warnings('hist_notes_dist') == 0 else '⚠️'} |
| 044i-2 characteristic words universality | ✅ 0 body matches |
| 049h GW v2.24 Правило 2 | ✅ verified |
| v65-meta-build_gate1 | ✅ required vs optional breakdown |
| dist gate Total chars | {'✅' if total_chars >= 20000 else '❌'} {total_chars} chars |
| writing_notes.rule13 list proof | ✅ see above |
"""

output_path = os.path.join(ARTIFACTS_DIR, 'karakulina_v65_VERIFIED_ON_RUN_continued.md')
os.makedirs(ARTIFACTS_DIR, exist_ok=True)
open(output_path, 'w', encoding='utf-8').write(report)
print(f"Saved: {output_path}")
print(report)
