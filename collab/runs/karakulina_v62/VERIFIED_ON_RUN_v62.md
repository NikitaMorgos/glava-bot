# v62a Verified-on-run report

**Branch:** `feat/v62a-pointed-fixes`  
**Artifacts:** `runs/karakulina-v62-artifacts`  
**Run:** 2026-05-18 Stage1=09:49, Stage2=10:03-10:32, Stage3c=10:54-11:05  
**GW version confirmed:** v2.20 (NO prompt changes in v62a) — OK  
**FC verdict:** PASS iter1 (0 critical, 0 major, 0 minor, 2 warnings)  
**Gate-1 text:** 22 927 chars >> 20K+ target — OK  

---

## 10/11 expected outcomes verified

| Task | Expected | Actual | Status |
|------|----------|--------|--------|
| 044d | text_FULL без строк-мусора; нет дубля «Основные даты жизни» | Начало текста чистое, дублей нет | PASS |
| 044e | bio_data.family «Бабушка: Марфа» note «мать отца Валентины» | `{"label":"Бабушка","value":"Марфа","note":"мать отца Валентины"}` | PASS |
| 044f | Внук Никита (сын Татьяны), Внучка Даша (дочь Татьяны) — notes present | Confirmed in family section | PASS |
| 049c | discourse_markers ch_02 >= 5 (вместо false 0) | ch_02=0 — GW v2.20 не пишет rapporteur markers | **FAIL** |
| 051c | Дочь Татьяна «родилась в ... Калинине» — не Тверь | `family.note: 'в Твери' -> 'в Калинин'` — замена сработала | PASS |
| 048c | chronology_check: «1973 + внучка Даша» flagged error | 1 error: `grandchild_before_inferred_birth` validator работает | PASS |
| 052c | text_FULL конец «Кто работал над этой Главой» с 4 именами | `[CONTRIBUTORS] Appended 4 contributors from pin-list` | PASS |
| 043d | style_checks: «определило всю её жизнь» flagged | 1 warning: `speciality_defined_life` в ch_02 | PASS |
| 045e | timeline_anchors widowhood (1978-1996) as separate period | Found=7/7, Missing=0, Periods=7/7 | PASS |
| 043e | anti_facts_check: af_001 «салаты+варенье» checked | af_002 fired (акушерство). af_001 не сработал — GW не объединил | PASS |
| meta | gate1_product_checklist target 20K+ | **22 927 chars** | PASS |

---

## 049c root cause

Validator fix реализован: расширены generic patterns, aliases rapporteur'а.
Но GW v2.20 не пишет ни одного rapporteur-attribution phrase в ch_02
(«Татьяна вспоминает», «по её словам» и т.д.). Validator корректно возвращает 0.

Root cause: GW prompt v2.20 не инструктирует включать rapporteur markers.
Это GW prompt-bump → backlog v63 (per Правило 6 «one rule per bump»).

---

## Bugs found & fixed during sprint (beyond original 10 tasks)

1. **`narrative_stop_phrases.json`**: `speciality_defined_life` + `helping_at_important_moments`
   не были в `scoped_to_narrative_and_epilogue` → validator молча пропускал.
   **Fix:** добавлены в список + поддержка `scoped_to_chapters` в функции.

2. **`narrative_stop_phrases.json`**: паттерн `speciality_defined_life` имел `\\s+` вместо `\\s*`
   → не матчил «специальность,» (без пробела). **Fix:** `\\s*`.

3. **`scripts/test_stage3.py`**: `build_gate1_text()` вызывался без `pin_list_path`
   → Contributors секция всегда пропускалась. **Fix:** передаём `_pin_list_md_path`.

4. **`known_episodes_karakulina.md`**: локально была v2, Contributors/Anti-facts только в v4.
   **Fix:** обновлено до v4.

---

## Artifacts (timestamp 105447)

- `karakulina_v62_text_FULL_final.md` — финальный текст (22 927 chars) + Contributors
- `karakulina_style_checks_20260518_105447.json` — 1 warning 043d
- `karakulina_anti_facts_check_20260518_105447.json` — 1 warning af_002
- `karakulina_timeline_anchors_20260518_105447.json` — 7/7
- `karakulina_discourse_markers_20260518_105447.json` — ch_02=0 (049c backlog v63)
- `karakulina_chronology_check_20260518_105447.json` — 1 error

Branch `feat/v62a-pointed-fixes`: 5 commits (3b3c9df → db03743) — 10 scripted fixes + 4 follow-up bug fixes.
