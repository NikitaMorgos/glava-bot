# Задача 049b: GW v2.20 — verify промпт реально активирован в Stage 2

**Статус:** `new`
**Номер:** 049b
**Автор:** Опус (роль архитектор+продакт)
**Дата создания:** 2026-05-17
**Тип:** verify implementation + минор fix
**Batch:** v60 sprint
**Связано:** task 049 (discourse markers preservation); task 050 (pin-list event depth); diagnostic v59: discourse markers ch_02=2 (threshold 8), pin-list depth 8 errors — Курсор сказал «нужен новый GW pass v60»

---

## Контекст

В v59 discourse markers ch_02=2 (vs threshold 8), pin-list depth 8 errors. Курсор объяснил: «GW v2.20 ПРАВИЛО 6/8 добавлено, но для эффекта нужен новый GW pass v60».

**Подозрение:** в v59 Stage 2 использовался **старый промпт GW v2.19**, а не v2.20. Курсор добавил правила в `prompts/ghostwriter_v2.20.md`, но `pipeline_config.json` или Stage 2 runner всё ещё указывают на `v2.19`.

Если так — это **bug реализации**, не реальная неэффективность ПРАВИЛ 6/8.

## Universality check

- [x] Промпт — verify uses correct version (universal mechanism)
- [x] Subject-specific — n/a
- [x] Алгоритм — generic Stage 2 prompt loading
- [x] Subject-replacement test — порядок prompts version loading одинаков для всех subjects ✅

---

## Спек

### Что нужно проверить и исправить

**1. Verify в `pipeline_config.json` (или соответствующий config):**
- Ghostwriter: версия = `v2.20` (не v2.19)
- Path к промпту: `prompts/ghostwriter_v2.20.md`
- Аналогично — Completeness Auditor: `v1.4` (не v1.3)

**2. Verify в Stage 2 runner (`scripts/test_stage2_pipeline.py`):**
- Загрузка промпта реально из `v2.20` файла
- Файл `prompts/ghostwriter_v2.20.md` существует и содержит:
  - Все ПРАВИЛА 1-5 из v2.18
  - ПРАВИЛО 6 (discourse markers, task 049)
  - ПРАВИЛО 7 (subject_age, task 049)
  - ПРАВИЛО 8 (pin-list event min depth, task 050)
  - ЗАПРЕТ 12 (родился/умерла, task 043)
  - ЗАПРЕТ 13 (epilogue antitriggers categorical, task 043b)
  - ЗАПРЕТ 14 (Класс 11 awkward formulation, task 043b)
  - ЗАПРЕТ 15 (narrative anti-trigger categories, task 043b)

**3. Если v2.20 уже активирован но ПРАВИЛА не сработали:**
- Возможна слабая формулировка — усилить **примерами generic** (с placeholders, без subject-конкретики)
- ПРАВИЛО 6 — добавить **минимум 5-8 markers** per chapter с пометкой **критичность**: «без discourse markers текст становится сухим отчётом, а не семейными воспоминаниями»
- ПРАВИЛО 8 — добавить **detection if event mentioned but < N sentences** → flag в revision_log

**4. Manifest Stage 2 logged:**
- В `<run>_stage2_run_manifest.json` зафиксировать `ghostwriter_version: "v2.20"`, `prompt_path`, `prompt_hash` для трейсабилити

### Какой результат ожидается

В v60 Stage 2 manifest:
- `ghostwriter_version: "v2.20"`
- `completeness_auditor_version: "v1.4"`

В v60 нарративе:
- ch_02 discourse markers ≥ 6 (стремимся к 8, минимум 5)
- pin-list depth — большинство episodes ≥ 3 sentences

### Как проверить

1. **Verify** в commit'е task 049b: cat `prompts/ghostwriter_v2.20.md` — все ПРАВИЛА 6-8 + ЗАПРЕТЫ 12-15 присутствуют
2. **Verify** в Stage 2 manifest — версия v2.20
3. **Integration** на v59 inputs (CA output + fact_map): прогнать Stage 2 с v2.20 → discourse markers count выше; pin-list depth errors ниже

---

## Ограничения

- [ ] Universal: версия промпта не зависит от subject
- [ ] ПРАВИЛА 6-8 — generic, без Каракулиноспецифики

---

## Dev Review

**Статус:** ожидает
**[TECH]** — verify-first задача, не code change в основном
**[PRODUCT]** — нет
**Сложность:** `xs` (<1 ч verify) + `s` (1-3 ч если усиливать промпт)
**Риск:** `low`

---

## История

| Дата | Статус | Кто |
|---|---|---|
| 2026-05-17 | `new` | Опус |
