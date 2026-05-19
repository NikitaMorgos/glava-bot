# v65c — Точечный fix (дотянуть до PASS Ворот 1)

**Status:** `in_progress`  
**Sprint:** v65c  
**Parent:** v65 (Stage 3 completed)  
**Budget:** $1-2 (один revision pass GW v2.24 + Stage 3)

---

## Контекст

v65 Stage 3 завершён. `text_FULL.md = 24 111 chars`. Опус Verify выявил 3 content blocker'а и 4 validator pattern bug'а.  
Validator bugs → v66. Content blockers → v65c точечный fix.

## Content blockers (3 реальных)

| # | Blocker | Location | Fix |
|---|---------|----------|-----|
| 1 | "улицу Капошвара" вместо "площадь Капошвара" | ch_02, ch_03 | entity substitution, 3 mentions |
| 2 | Баба Аня отсутствует в нарративе | ch_03 | добавить как «французская бабушка» comparison |
| 3 | "В 1990-е годы семья продала дачу" — неверный год | ch_02, ch_04 | pin-list ep_029 year_direction=before_1990s |

## Approach

**Один дополнительный revision pass** GW v2.24 на `karakulina_book_FINAL_1779175986_revised.json` с 4 точечными hints:

- c_001: entity_substitution — Капошвара улица → площадь (must_apply=true)
- c_002: narrative_required_persons — Баба Аня в ch_03 (chapter-level, snippet=null)
- c_003: pin_list_year_direction_drift — дача "1990-е" → "до 1990-х" / без года
- c_004: pin_list_depth — развернуть ep_003/ep_011/ep_016/ep_024 до ≥3 sentences (optional)

audit_revision_diff threshold повышен до 30 (chapter-level hint c_002 → много paragraph changes).

---

## Targets v65c

- Total chars build_gate1 ≥ 20 000 (уже 24 111 — не регрессировать)
- Капошвара = "площадь" (3 mentions)
- Баба Аня в ch_03 как «французская бабушка» comparison
- Дача: "до 1990-х" либо без year attribution (НЕ "в 1990-е")
- Pin-list depth errors ≤ 2 (с 4 допустимо снизить)
- Chronology errors = 0 (не regress)
- writing_notes.rule13_revision_applied list preserved post-LE

---

## НЕ ТРОГАТЬ

- Stage 1+2 (existing OK)
- GW v2.24 prompt (не бамп до v2.25)
- Validator pattern bugs (v66)
- audit_revision_diff fix (v66 backlog)
- Любые новые validators или правила

---

## Artifacts

Ветка: `runs/karakulina-v65-artifacts` (поверх commit `8d3dda7`)

| Файл | Описание |
|------|---------|
| `karakulina_book_FINAL_v65c_revised.json` | После revision pass |
| `karakulina_book_FINAL_stage3_v65c.json` | После Stage 3 |
| `karakulina_v65c_text_FULL.md` | build_gate1 output |
| `revision_diff_audit_v65c.json` | diff audit результат |
| `karakulina_v65c_VERIFIED_ON_RUN.md` | отчёт |
