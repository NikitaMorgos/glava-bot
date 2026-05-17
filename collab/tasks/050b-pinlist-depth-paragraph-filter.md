# Задача 050b: Pin-list depth detector — фильтровать paspart строки (paragraph только в narrative)

**Статус:** `new`
**Номер:** 050b
**Автор:** Опус (роль архитектор+продакт)
**Дата создания:** 2026-05-17
**Тип:** `cco-скрипт`
**Batch:** v60 sprint
**Связано:** task 050 (pin-list depth); diagnostic v59: 8 errors, большинство — paspart строки (не narrative)

---

## Контекст

В v59 `pin_list_depth.json` 8 errors. Анализ показывает что **большинство** — paspart строки ch_01, не narrative paragraphs:

| episode_id | snippet (что детектор счёл paragraph) | Реальная проблема |
|---|---|---|
| ep_002 (фельдшерская школа) | «**1938–1940** — Кировоградская фельдшерско-акушерская школа, специальность акушерки» (paspart) | в narrative ch_02 раздел «Учёба и первая работа» — **2 параграфа**, достаточно |
| ep_018 (Ударник) | «**1965** — звание «Ударник коммунистического труда»» (paspart) | в narrative ch_02 раздел «Общественное признание» — **3 параграфа** |
| ep_021 (Маргось) | «**Зять:** Маргось Владимир, первый муж Татьяны (женился в 1977 году)» (paspart) | в narrative ch_02 «Семейные перемены» — **3 параграфа** |
| ep_023 (Дмитрий 1978) | «**Муж:** Каракулин Дмитрий, военный (умер в 1978 году)» (paspart) | в narrative ch_02 — упомянуто |
| ep_027 (пенсия 1994) | «В августе 1994 года Валентина ушла на пенсию» — это narrative, но 1 предложение | реально коротко |
| ep_028 (Кужба 1996) | narrative 2 предл. — реально требует расширения |
| ep_030 (перелом 2005) | «**2005. Последние годы**» (paspart) | в narrative — упомянуто |

**Корень:** `validate_pin_list_depth` ищет первое вхождение маркеров в **любом** content (включая paspart), даже если в narrative ch_02-04 эпизод развёрнут.

## Universality check

- [x] Промпт — n/a
- [x] Subject-specific — n/a (логика generic)
- [x] Алгоритм generic — поиск paragraph в narrative scope (ch_02/ch_03/ch_04, не ch_01/epilogue paspart)
- [x] Subject-replacement test — для Корольковой логика та же ✅

---

## Спек

### Что нужно изменить

**`validate_pin_list_depth` в `pipeline_utils.py`:**

1. Расширить scope filter — искать paragraph для episode **только в narrative chapters**:
   - `narrative_chapter_ids = ["ch_02", "ch_03", "ch_04"]` (опционально config per subject schema)
   - НЕ искать в `ch_01` (паспортичка) или `epilogue`

2. Если эпизод **не найден** в narrative scope, но найден в ch_01/epilogue — **отдельный flag** `episode_only_in_paspart` (warning), не error:
   - Указывает что эпизод существует только в паспортичке/эпилоге, нет narrative
   - Решение по severity — на product level

3. Если эпизод найден в narrative:
   - Подсчитать sentences в paragraph
   - Сравнить с `min_sentences`
   - Если < min → error (как сейчас)

### Какой результат ожидается

В v60 `pin_list_depth.json`:
- Только real depth violations в narrative (3-4 episodes)
- Paspart строки не считаются ложно

### Как проверить

1. **Unit-тесты** `tests/test_pin_list_depth_scope.py`:
   - Episode упомянут только в paspart → warning, не error
   - Episode упомянут в narrative с N≥min → PASS
   - Episode упомянут в narrative с N<min → error
   - Episode в paspart + narrative — учитывается narrative count

2. **Integration на v59 book_FINAL_stage3:**
   - Из 8 errors v59 → ожидаемо 3 (пенсия 1994, Кужба 1996, ...) после filter

3. **Verified-on-run** v60:
   - `pin_list_depth.json` errors ≤3 (только real narrative depth issues)

---

## Ограничения

- [ ] `narrative_chapter_ids` — может быть subject-specific config (для других biography forms)
- [ ] Idempotent
- [ ] Universal

---

## Dev Review

**Статус:** ожидает
**[TECH]** — narrative_chapter_ids — конфигурируемо per subject (default ["ch_02","ch_03","ch_04"])
**[PRODUCT]** — нет
**Сложность:** `xs` (<1 ч)
**Риск:** `low`

---

## История

| Дата | Статус | Кто |
|---|---|---|
| 2026-05-17 | `new` | Опус |
