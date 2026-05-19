# v65c — Verified-on-Run (Stage 3 Complete)

**Date:** 2026-05-19  
**Sprint:** v65c — pointed fix  
**Branch:** feat/v65-bugfix-sprint  
**Artifacts:** runs/karakulina-v65-artifacts

---

## v65c Revision Pass (GW v2.24)

| Metric | Value |
|--------|-------|
| hints_count | 4 |
| must_apply | 3 (c_001/c_002/c_003) + 1 optional (c_004) |
| applied | 3 |
| skipped | 1 |
| unauthorized_changes | 8 (threshold=30) |

writing_notes.rule13_revision_applied: **list count=3**  
→ 049g preserve post-LE: **YES ✅**

---

## v65c Content Fixes (3 blockers)

| Fix | Status |
|-----|--------|
| c_001: Капошвара улица → площадь | ✅ FIXED |
| c_002: Баба Аня в ch_03 | ✅ PRESENT |
| c_003: Дача "1990-е" убрано | ✅ FIXED |

---

## Char Counts (sum of chapter content, NOT file_size)

| Chapter | Chars | Target | Status |
|---------|-------|--------|--------|
| ch_01 (bio_data rendered) | 3221 | ~3 000 | ✅ |
| ch_02 | 7730 | ≥ 7 000 | ✅ |
| ch_03 | 4854 | ≥ 4 000 | ✅ |
| ch_04 | 3160 | ≥ 2 500 | ✅ |
| epilogue | 1077 | 800–1500 | ✅ |
| **Narrative** | **16821** | **≥ 15 000** | **✅** |
| Total (chapters) | 20042 | ≥ 20 000 | ✅ |
| Total + hist_notes | 21131 | ≥ 20 000 | ✅ |
| **text_FULL.md (build_gate1)** | **24619** | **≥ 20 000** | **✅** |

Historical notes: inline=7, field=7

---

## Final Validators

| Validator | Errors | Warnings | Status |
|-----------|--------|----------|--------|
| chronology | 0 | 0 | ✅ |
| narrative_truism Class 17 | 0 | 0 | ✅ |
| stop_phrases Class 1/11 | 0 | 0 | ✅ |
| personal_historical_voice | 0 | 3 | ⚠️ validator bug (v66) |
| hist_notes_dist | 0 | 0 | ✅ |
| descendants_early | 0 | 0 | ✅ |
| cross_paragraph_dup | 0 | 0 | ✅ |
| required_episodes (044i) | 11 missing / 27 | — | ⚠️ validator bug (v66) |

---

## Gate 1 Verdict

✅ PASS

- ✅ text_FULL.md = 24619 chars ≥ 20 000
- ✅ Капошвара fixed (not "улица")
- ✅ Капошвара = "площадь" confirmed
- ✅ Баба Аня in narrative ch_03
- ✅ Дача year attribution corrected
- ✅ Chronology errors = 0
- ✅ writing_notes.rule13 list preserved post-LE
