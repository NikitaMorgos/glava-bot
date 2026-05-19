# v65 sprint: bugfix v64 implementation + Никитин feedback v64

**Статус:** `new`
**Sprint ID:** v65
**Автор:** Опус
**Дата создания:** 2026-05-19
**Триггер:** v64 verified (НЕ PASS) — revision loop архитектурно работает, но 4 bugs реализации orchestrator + 5 классов багов из Никитин live review v64
**Связано:** stocktake-2026-05-18-v60-v63.md; dev-review-protocol.md v2 (Правила 7+8, усиление 3); v64 verified report

---

## Pre-sprint checklist (Правила 3+4+7+8 — обновлено 2026-05-19)

- [x] **Stocktake актуален** — `stocktake-2026-05-18-v60-v63.md` свежий (v64 — следующая волна после stocktake; следующий stocktake обязателен после v66 либо если ≥3 verified-on-run без stocktake)
- [x] **Critical reading артефактов** v64 выполнено — открыты text_FULL.md, validators_on_draft.json, revision_hints.json, revision_diff_audit.json, book_REVISED, final_validators
- [x] **Universality построчно** для всех spec'ов — для task 049h grep команда обязательна перед commit'ом v2.24
- [x] **Каждая защита подключена к лечению** — orchestrator 049f-2 extend coverage всех валидаторов; новые валидаторы 048g/046f/048f — через revision hint
- [x] **Прогоны раздельные где требуется** (Правило 7) — v65 = combined OK потому что все 14 tasks — **узкие bugfixes** existing implementation. GW v2.24 = 2 hot-fixes existing rules (schema + universality), не новые правила
- [x] **Класс багов, не симптом** — каждый task на класс (Class 12 extend, Class 19 NEW, recurring patterns с семантическим hint)
- [x] **Скрипт-first** — 11 scripted из 14, 1 GW prompt (hot-fix существующих правил), 1 docs, 1 build_gate1 enhancement

---

## Контекст

После v64 — **архитектура revision loop работает** (GW v2.23 ПРАВИЛО 13 физически применяется), но **реализация partial** (4 bugs orchestrator). Плюс Никитин live review v64 идентифицировал:
- Class 12 в новой форме (потомки Полины в ранних годах)
- Class 11 recurring (новая форма)
- Class 19 NEW (cross-paragraph дубль)
- Class 5 regression (грибы, дача, тётя Маша)
- factual error (улица vs площадь Капошвара)
- Class 9 distribution (мало hist_notes в портрете)
- Universality recurring моя ошибка (выковыривал в GW prompt)

v65 = **bugfix sprint** (не новая архитектура). Цель — закрыть **gaps реализации v64** + новые классы.

---

## Универсальность принципов команды (verification по всему sprint)

- ✅ **Лес/деревья:** v65 не точечно — закрываем класс «orchestrator coverage» (4 валидатора отсутствуют), класс «scope too narrow в validator» (chronology FP), класс «universality recurring» (procedural grep команда)
- ✅ **Универсальность:** все 14 tasks generic + per-subject configs. GW v2.24 ПРАВИЛО 2 — placeholders, characteristic_words через input
- ✅ **Класс багов, не симптом:** Class 12 extend (descendants in early context — generic), Class 19 NEW (cross-paragraph generic), Class 11 recurring snapshot
- ✅ **Скрипт-first:** 11 scripted / 1 prompt hotfix / 1 docs / 1 build_gate1
- ✅ **Логирование:** dev-review-protocol v2 + auto-memory + handoff + run_registry после прогона
- ✅ **Медленные шаги:** 2 hot-fixes в GW v2.24, не новые правила; combined v65 OK для bugfixes (per Правило 7)
- ✅ **Не экономим на тестовых прогонах:** v65 — 1 прогон $4-6 (revision loop). НЕ скупимся.

---

## 14 tasks

### A. Архитектурный bugfix v64 implementation (4 tasks)

| # | Task | Тип | Mitigates |
|---|------|-----|-----------|
| 1 | **049f-2** orchestrator coverage extend | cco-скрипт | bug v64: только 6 из 10+ валидаторов подключены; warnings отфильтрованы |
| 2 | **049g** LE preserve writing_notes | cco-скрипт | bug v64: LE удаляет writing_notes, diff_audit видит applied=[] |
| 3 | **049e-2** GW v2.23 → v2.24 schema fix | GW prompt hot-fix | bug v64: GW вернул `revision_applied: string`, spec требовал `rule13_revision_applied: list` |
| 4 | **048e** chronology FP fix | cco-скрипт | bug v64: chronology validator 5 errors, 4 FP на factual summary в ch_01/epilogue |

### B. Никитин feedback v64 — классы багов (6 tasks)

| # | Task | Тип | Mitigates |
|---|------|-----|-----------|
| 5 | **048f** Class 12 extend «потомки в раннем контексте» | cco-скрипт + config | Толя/Коля/Витя upомянуты в 1933 — generic class |
| 6 | **043f-3** Class 11 recurring snapshot v64 + lesson | конфиг + snapshot | Pattern эволюция «—особенно по X, Y и другим Z» |
| 7 | **048g** Class 19 NEW cross-paragraph duplication | cco-скрипт + snapshot | Дословный повтор абзаца Власьево/крещения |
| 8 | **044i** pin-list v6 → v7 (required_in_narrative + Капошвара) | pin-list edit + parser + validator | Грибы/тётя Маша/дача missing; Капошвара улица→площадь |
| 9 | **046f** hist_notes per-chapter distribution | cco-скрипт + config | Мало hist_notes в портрете (Class 9 distribution) |
| 10 | **044i-2** characteristic words universality verify | verification report | Niki «выковыривал» — закрытие через task 049h |

### C. Universality + GW v2.24 (1 task)

| # | Task | Тип | Mitigates |
|---|------|-----|-----------|
| 11 | **049h** GW Правило 2 universality fix (combined в v2.24) | GW prompt hot-fix + Stage 2 input wire | Hardcoded «выковыривал» etc → placeholders + pin-list characteristic_words input |

### D. Build_gate1 enhancement (1 task)

| # | Task | Тип | Mitigates |
|---|------|-----|-----------|
| 12 | **v65-meta-build_gate1** pin-list coverage breakdown | scripted reporting | Niki «что это значит full 14/67?» → required vs optional clear |

### Sprint plan + handoff

| # | Task | Тип |
|---|------|-----|
| 13 | **v65-bugfix-sprint.md** | sprint plan (этот документ) |
| 14 | **handoff-cursor-2026-05-19-v65.md** | handoff Курсору |

---

## Версионирование v65

- **GW v2.23 → v2.24** (2 hot-fixes existing rules — ПРАВИЛО 13 schema + ПРАВИЛО 2 universality; **НЕ новые правила** per Правило 6)
- **CA v1.5** — без изменений
- **pin-list `known_episodes_karakulina.md` v6 → v7** (`required_in_narrative` markers + Капошвара verify)
- **dev-review-protocol.md v2** (Правила 7+8, усиление 3, pre-sprint checklist)
- **Configs:**
  - `narrative_stop_phrases.json: v6 → v7` (Class 11 extension)
  - `chronology_check_config.json: v1` (новый: skip_chapters, sentence_birth_self_declaration_skip)
  - `chronology_periods_karakulina.json: v1 → v2` (descendants relation patterns)
  - `cross_paragraph_duplication_config.json: v1` (новый, generic)
  - `historical_notes_distribution_config.json: v1` (новый, generic per-chapter thresholds)
- **gate1_product_checklist.md v2** (без изменений, уже distribution gate с v64)
- **auto-memory:** +2 файла (principle_no_test_run_economy.md + principle_class_semantic_not_regex.md)

---

## Drivers объёма (для distribution gate target 20K Total)

v64 narrative — 18 242 Total, distribution: ~15K narrative + 3K paspart + ~1.2K historical_notes.

Цель v65 — приблизиться к **15K narrative + 3K paspart + 2K historical_notes = 20K Total**:

| Драйвер | Эффект |
|---------|--------|
| **049f-2 + 049e-2 + 049g revision loop полный** | Все валидаторы → hints → GW переписывает. Главный driver depth. ch_02 должен подрасти (pin_list_depth 0 errors после revision) |
| **046f distribution** | Распределение hist_notes по главам → ch_03/ch_04 enrichment +200-400 chars каждая |
| **044i required_episodes** | Грибы/ягоды + дача + тётя Маша вернутся в narrative → +400-600 chars |
| **048g cross-paragraph duplication remove** | −300-500 chars (один paragraph удалится) — приемлемо, освободит место для нового content |
| **048e + 048f chronology FP fix + Class 12 extend** | НЕ объёмные, но снижают noise hints orchestrator'a |
| **049h ПРАВИЛО 2 universality** | Не объёмный, но фиксит когда подключим Корольковой |

**Net ожидаемый эффект:** +500-1000 chars narrative → ~16K, + ~800 hist_notes = ~3K. Total ~22K = PASS distribution gate.

---

## Risk + mitigation v65

**Risk A: Множество узких bugfixes одновременно → один из них ломает что-то.**

Mitigation:
- Snapshot tests для каждого изменения
- Diff audit между v64 и v65 на ключевых validators outputs
- Если PASS падает по другой causa — diagnostic (combined sprint risk per Правило 7 — но bugfixes acceptable trade-off)

**Risk B: Revision loop стал работать (049f-2 wired all) → hints count резко растёт → GW не справляется.**

Mitigation:
- Warnings filtered в must_apply=false → GW решает
- Max 1 revision pass (как в v64)
- Если revision_failed=true → STOP, Опус review

**Risk C: 049h GW prompt change может уронить characteristic words в narrative (pin-list input ещё не verified для wire).**

Mitigation:
- Wire тестируется в task 049h tests
- Если в v65 narrative нет «выковыривал» — pin-list input не работает → backlog v66 wire fix
- В худшем случае v65 deтериорирует voice (вернёмся к v66)

**Risk D: 048f Class 12 extend warning level → GW игнорирует.**

Mitigation:
- В revision pass warnings передаются (049f-2) → GW решает
- Если игнорирует часто → backlog v66 severity escalation

---

## Стратегия v65 verify

1. **Stage 1** split-extract (TR1+TR2) с pin-list v7
2. **Stage 2 first pass** GW v2.24 → `book_draft.json`
3. **Все ~12 validators** на book_draft (chronology, pin_list_depth, discourse_markers, narrative_stop_phrases v7, anti_facts, epilogue_stop_phrases, personal_historical_voice, epilogue_quote_density, **narrative_truism** (Class 17 v64), **descendants_in_early_context** (Class 12 v65), **cross_paragraph_duplication** (Class 19 v65), **historical_notes_distribution** (v65), **required_episodes_coverage** (v65))
4. **Orchestrator 049f-2** соберёт hints от всех (10+ источников, warnings включены) → передаст GW Stage 2 revision pass
5. **Stage 2 revision pass** GW v2.24 → `book_after_revision.json` со схемой `rule13_revision_applied: [list]`
6. **Schema validation** + diff_audit
7. **046d historical_notes enrichment** post-revision (если <5 inline либо distribution неравномерное)
8. **Stage 3 + LE preserve writing_notes (049g)** + post-processing
9. **build_gate1** с новым pin-list coverage breakdown
10. **Final validators** (full coverage) → reports JSON

Создай `scripts/_run_v65_full.sh` (extend `_run_v64_full.sh`).

---

## Targets для v65

Distribution gate:
- Total ≥ 20 000 chars
- Narrative ≥ 15 000
- Paspart ~ 3 000
- Historical_notes ≥ 2 000 chars (≥5 inline + ≥3 field) с **per-chapter distribution** (ch_02≥3, ch_03≥2, ch_04≥1)

Validators clean после revision pass:
- chronology errors = 0 (после 048e FP fix, real errors закрыты revision)
- pin_list_depth errors = 0
- narrative_truism Class 17 errors = 0
- Class 1/11/12 extend errors = 0
- cross_paragraph_duplication Class 19 errors = 0
- epilogue_stop_phrases errors = 0
- required_episodes_coverage missing = 0 (грибы, дача, тётя Маша есть)

Goals:
- discourse markers: ch_02 ≥8 / ch_03 ≥5 / ch_04 ≥3
- personal_historical_voice: ch_02 ≥3 / ch_03 ≥2 / ch_04 ≥1

Content:
- Мария в bio_data.family ✅
- Баба Аня в narrative ch_03 ✅
- Грибы/ягоды + тётя Маша в narrative ✅
- Продажа дачи в narrative (без «1990-е») ✅
- Капошвара = площадь (не улица) ✅
- Полина без потомков в context 1933 ✅
- Нет дубля Власьево/крещения ✅

Architecture:
- writing_notes.rule13_revision_applied — **list** of dicts (schema fix)
- writing_notes preserved в book_FINAL_stage3 ✅
- revision_diff_audit applied != [] ✅
- revision_failed = false
- Stage 2 manifest: ghostwriter_version=v2.24

Universality:
- grep по subject-specific terms в `prompts/03_ghostwriter_v2.24.md` body = 0 ✅
- characteristic_words из pin-list input используются в narrative

---

## Что НЕ делаем в v65 (явный список)

- ❌ Новые GW правила (только 2 hot-fix existing — ПРАВИЛО 13 schema + ПРАВИЛО 2 universality)
- ❌ ch_03 «Гостеприимство и кулинария» раздел — отложено в v66 (ПРАВИЛО 14 GW prompt-bump)
- ❌ Editor agent / GW prompt refactor task 037 — backlog v66+ если v65 не закрывает classes
- ❌ Auto-enforce delete для Class 17/19 — warning, revision pass решает
- ❌ Subject-specific patterns в Class 18 — только generic в v65
- ❌ Подключение Корольковой — после RP-1
- ❌ Этап 2 Proofreader scripted — после Ворот 1 PASS
- ❌ Bundle новых правил в v2.24 — только bug fixes

---

## Открытые вопросы

1. **Если v65 PASS** — tag RP-1 + следующий sprint = либо v66 (ch_03 sections) либо Королькова task 053. Никитин call.
2. **Если v65 НЕ PASS** — diagnostic + v65b (узкий) либо radical (task 037 GW refactor)
3. **Universality grep команда** — добавить в pre-commit hook? Сейчас manual в pre-sprint checklist. Backlog v66 — автоматизировать в CI.

---

## История

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-19 | `new` | Опус |
