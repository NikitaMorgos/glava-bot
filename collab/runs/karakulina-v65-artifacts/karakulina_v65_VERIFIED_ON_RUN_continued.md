# v65 Pipeline — Verified-on-Run Continued (Stage 3)

**Date:** 2026-05-19  
**Code branch:** feat/v65-bugfix-sprint  
**Artifacts:** runs/karakulina-v65-artifacts

---

## Stage 2 Manifest

| Field | Value |
|-------|-------|
| ghostwriter_version | v2.24 |
| completeness_auditor_version | v1.5 |
| final_verdict | pass |

---

## Revision Pass (GW v2.24 + ПРАВИЛО 13)

| Metric | Value |
|--------|-------|
| hints_count | 18 |
| applied | 16 |
| skipped | 2 |
| unauthorized_changes | 23 (false positive — see v66 backlog) |
| rule13_revision_failed | False |

writing_notes.rule13_revision_applied: **type=list, count=16**  
→ 049e-2 schema fix VERIFIED ✅

writing_notes preserved post-LE:  **YES ✅**  
→ 049g preserve_root_level_metadata VERIFIED ✅

---

## Char Counts (sum of chapter content, NOT file_size)

| Chapter | Chars | Target | Status |
|---------|-------|--------|--------|
| ch_01 (bio_data rendered) | 3219 | ~3 000 | ✅ |
| ch_02 | 7734 | ≥ 7 000 | ✅ |
| ch_03 | 4763 | ≥ 4 000 | ✅ |
| ch_04 | 2912 | ≥ 2 500 | ✅ |
| epilogue | 1077 | 800–1500 | ✅ |
| **Narrative (02–epi)** | **16486** | **≥ 15 000** | **✅** |
| **Total** | **19705** | **≥ 20 000** | **❌** |

Historical notes: inline=7 (✅ ≥5), field=7 (✅ ≥3)

---

## Final Validators (Stage 3 output)

| Validator | Errors | Warnings | Status |
|-----------|--------|----------|--------|
| chronology (048e FP fix) | 0 | 0 | ✅ |
| narrative_truism Class 17 | 0 | 0 | ✅ |
| stop_phrases Class 1/11 | 0 | 0 | ✅ |
| personal_historical_voice | 0 | 3 | ✅ |
| hist_notes_dist (046f) | 0 | 0 | ✅ |
| descendants_early (048f) | 0 | 0 | ✅ |
| cross_paragraph_dup (048g) | 0 | 0 | ✅ |
| required_episodes (044i) | 3 missing / 19 total | — | ❌ |

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
| 049g LE preserve writing_notes | ✅ VERIFIED |
| 049e-2 rule13_revision_applied list | ✅ list of 16 dicts |
| 048e chronology FP fix | ✅ errors=0 |
| 048f Class 12 extend | ✅ errors=0 |
| 043f-3 Class 11 snapshot v7 | ✅ errors=0 |
| 048g Class 19 cross-paragraph | ✅ errors=0 |
| 044i pin-list v7 required_in_narrative | 16/19 covered |
| 046f hist_notes per-chapter dist | ✅ |
| 044i-2 characteristic words universality | ✅ 0 body matches |
| 049h GW v2.24 Правило 2 | ✅ verified |
| v65-meta-build_gate1 | ✅ required vs optional breakdown |
| dist gate Total chars | ❌ 19705 chars |
| writing_notes.rule13 list proof | ✅ see above |
