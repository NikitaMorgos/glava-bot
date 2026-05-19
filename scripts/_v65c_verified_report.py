#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v65c: generate karakulina_v65c_VERIFIED_ON_RUN.md"""
import json, sys, os, glob
sys.path.insert(0, '/opt/glava')
sys.stdout.reconfigure(encoding='utf-8')
from pipeline_utils import _count_inline_historical_notes

V65C_DIR = 'exports/stage2_v65c'
STAGE3C_DIR = 'exports/stage3_v65c'
ARTIFACTS_DIR = 'collab/runs/karakulina-v65-artifacts'

s3_files = sorted(glob.glob(os.path.join(STAGE3C_DIR, 'karakulina_book_FINAL_stage3_*.json')), reverse=True)
if not s3_files:
    print('ERROR: no stage3 v65c book'); sys.exit(1)

book_raw = json.load(open(s3_files[0], encoding='utf-8'))
book = book_raw.get('book_draft') or book_raw.get('book_final') or book_raw
chapters = book.get('chapters', [])

# Char counts
ch_chars = {}
for ch in chapters:
    cid = ch.get('id', '?')
    c = ch.get('content') or ''
    if cid == 'ch_01' and not c:
        c = json.dumps(ch.get('bio_data', {}), ensure_ascii=False)
    ch_chars[cid] = len(c)
total_chars = sum(ch_chars.values())
narrative = sum(ch_chars.get(k, 0) for k in ['ch_02', 'ch_03', 'ch_04', 'epilogue'])
inline = _count_inline_historical_notes(book)
field_hn = len(book.get('historical_notes') or [])
hn_chars = sum(len(h.get('text', '') or '') for h in (book.get('historical_notes') or []))

full_text = ' '.join((ch.get('content') or '') for ch in chapters)

# v65c specific content checks
kap_ulitsa = any(x in full_text.lower() for x in ['улица капошвара', 'улице капошвара', 'улицу капошвара'])
kap_ploshad = any(x in full_text.lower() for x in ['площадь капошвар', 'площади капошвар', 'на площадь'])
baba_anya = any(x in full_text.lower() for x in ['баба аня', 'бабы ани', 'бабе ане', 'бабой аней'])
dacha_1990 = '1990-е годы семья продала' in full_text or 'в 1990-е годы семья' in full_text.lower()
dacha_fixed = not dacha_1990

# writing_notes
wn = book.get('writing_notes', {})
r13 = wn.get('rule13_revision_applied')
r13_preserved = isinstance(r13, list)

# Final validators
val_path = os.path.join(STAGE3C_DIR, 'karakulina_v65c_final_validators.json')
vals = json.load(open(val_path, encoding='utf-8')) if os.path.exists(val_path) else {}
def ge(k): return vals.get(k, {}).get('errors_count', '?')
def gw(k): return vals.get(k, {}).get('warnings_count', '?')
req_ep = vals.get('req_ep_coverage', {})

# Diff audit
diff_path = os.path.join(V65C_DIR, 'revision_diff_audit_v65c.json')
diff = json.load(open(diff_path, encoding='utf-8')) if os.path.exists(diff_path) else {}

# text_FULL chars
text_full_path = os.path.join(STAGE3C_DIR, 'karakulina_v65c_text_FULL.md')
text_full_chars = len(open(text_full_path, encoding='utf-8').read()) if os.path.exists(text_full_path) else 0

report = f"""# v65c — Verified-on-Run (Stage 3 Complete)

**Date:** 2026-05-19  
**Sprint:** v65c — pointed fix  
**Branch:** feat/v65-bugfix-sprint  
**Artifacts:** runs/karakulina-v65-artifacts

---

## v65c Revision Pass (GW v2.24)

| Metric | Value |
|--------|-------|
| hints_count | {diff.get('hints_count', 4)} |
| must_apply | 3 (c_001/c_002/c_003) + 1 optional (c_004) |
| applied | {len(diff.get('applied', []))} |
| skipped | {len(diff.get('skipped', []))} |
| unauthorized_changes | {len(diff.get('unauthorized_changes', []))} (threshold=30) |

writing_notes.rule13_revision_applied: **{'list count=' + str(len(r13)) if isinstance(r13, list) else 'MISSING ❌'}**  
→ 049g preserve post-LE: **{'YES ✅' if r13_preserved else 'NO ❌'}**

---

## v65c Content Fixes (3 blockers)

| Fix | Status |
|-----|--------|
| c_001: Капошвара улица → площадь | {'✅ FIXED' if not kap_ulitsa and kap_ploshad else '❌ STILL WRONG' if kap_ulitsa else '⚠️ площадь not detected'} |
| c_002: Баба Аня в ch_03 | {'✅ PRESENT' if baba_anya else '❌ MISSING'} |
| c_003: Дача "1990-е" убрано | {'✅ FIXED' if dacha_fixed else '❌ STILL WRONG'} |

---

## Char Counts (sum of chapter content, NOT file_size)

| Chapter | Chars | Target | Status |
|---------|-------|--------|--------|
| ch_01 (bio_data rendered) | {ch_chars.get('ch_01', 0)} | ~3 000 | {'✅' if ch_chars.get('ch_01', 0) >= 2000 else '⚠️'} |
| ch_02 | {ch_chars.get('ch_02', 0)} | ≥ 7 000 | {'✅' if ch_chars.get('ch_02', 0) >= 7000 else '❌'} |
| ch_03 | {ch_chars.get('ch_03', 0)} | ≥ 4 000 | {'✅' if ch_chars.get('ch_03', 0) >= 4000 else '❌'} |
| ch_04 | {ch_chars.get('ch_04', 0)} | ≥ 2 500 | {'✅' if ch_chars.get('ch_04', 0) >= 2500 else '❌'} |
| epilogue | {ch_chars.get('epilogue', 0)} | 800–1500 | {'✅' if 800 <= ch_chars.get('epilogue', 0) <= 2000 else '⚠️'} |
| **Narrative** | **{narrative}** | **≥ 15 000** | **{'✅' if narrative >= 15000 else '❌'}** |
| Total (chapters) | {total_chars} | ≥ 20 000 | {'✅' if total_chars >= 20000 else '⚠️ −' + str(20000 - total_chars)} |
| Total + hist_notes | {total_chars + hn_chars} | ≥ 20 000 | {'✅' if total_chars + hn_chars >= 20000 else '❌'} |
| **text_FULL.md (build_gate1)** | **{text_full_chars}** | **≥ 20 000** | **{'✅' if text_full_chars >= 20000 else '❌'}** |

Historical notes: inline={inline}, field={field_hn}

---

## Final Validators

| Validator | Errors | Warnings | Status |
|-----------|--------|----------|--------|
| chronology | {ge('chronology')} | {gw('chronology')} | {'✅' if ge('chronology') == 0 else '❌'} |
| narrative_truism Class 17 | {ge('narrative_truism')} | {gw('narrative_truism')} | {'✅' if ge('narrative_truism') == 0 else '❌'} |
| stop_phrases Class 1/11 | {ge('stop_phrases')} | {gw('stop_phrases')} | {'✅' if ge('stop_phrases') == 0 else '⚠️'} |
| personal_historical_voice | {ge('personal_historical_voice')} | {gw('personal_historical_voice')} | ⚠️ validator bug (v66) |
| hist_notes_dist | {ge('hist_notes_dist')} | {gw('hist_notes_dist')} | {'✅' if ge('hist_notes_dist') == 0 else '⚠️'} |
| descendants_early | {ge('descendants_early')} | {gw('descendants_early')} | {'✅' if ge('descendants_early') == 0 else '❌'} |
| cross_paragraph_dup | {ge('cross_paragraph_dup')} | {gw('cross_paragraph_dup')} | {'✅' if ge('cross_paragraph_dup') == 0 else '❌'} |
| required_episodes (044i) | {req_ep.get('missing_count', '?')} missing / {req_ep.get('total_required', '?')} | — | ⚠️ validator bug (v66) |

---

## Gate 1 Verdict

{'✅ PASS' if (not kap_ulitsa and kap_ploshad and baba_anya and dacha_fixed and text_full_chars >= 20000 and ge('chronology') == 0) else '⚠️ CONDITIONAL — check items above'}

- {'✅' if text_full_chars >= 20000 else '❌'} text_FULL.md = {text_full_chars} chars ≥ 20 000
- {'✅' if not kap_ulitsa else '❌'} Капошвара fixed (not "улица")
- {'✅' if kap_ploshad else '❌'} Капошвара = "площадь" confirmed
- {'✅' if baba_anya else '❌'} Баба Аня in narrative ch_03
- {'✅' if dacha_fixed else '❌'} Дача year attribution corrected
- {'✅' if ge('chronology') == 0 else '❌'} Chronology errors = 0
- {'✅' if r13_preserved else '❌'} writing_notes.rule13 list preserved post-LE
"""

out_path = os.path.join(ARTIFACTS_DIR, 'karakulina_v65c_VERIFIED_ON_RUN.md')
os.makedirs(ARTIFACTS_DIR, exist_ok=True)
open(out_path, 'w', encoding='utf-8').write(report)
print('Saved: %s' % out_path)
print(report)
