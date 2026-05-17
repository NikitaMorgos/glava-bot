# Задача 041: Pin-list events для GW (Stage 2) + diff-валидация между прогонами

**Статус:** `new` (полный spec после v57; ранее outline)
**Номер:** 041
**Автор:** Опус (роль архитектор+продакт)
**Дата создания:** 2026-05-17
**Тип:** `промпт` (GW) + `cco-скрипт` (diff-валидация + pin-coverage)
**Batch:** 2 (после v57 verified)
**Связано:** task 035 (CA pin-list для Stage 1); stocktake 2026-05-17 **Класс 5** (Episode regression); pin-list v2

---

## Контекст

task 035 закрыл CA pin-list для Stage 1 (эпизоды появляются в fact_map). Но **GW (Stage 2) не получает pin-list** и не имеет обязательства развёрнуто рассказать каждый эпизод. Результат — стохастика между прогонами:

**Потеряно в v57 относительно v56:**
- Огурцы: v56 развёрнутый эпизод (чемодан, испортились, Татьяна выкинула) → v57 свёрнут до фразы «огурцы, а не груши»
- Карты и домино — потеряно
- Грибы/ягоды + тётя Маша-соседка — потеряно
- Шарлотка — потеряно
- «Французская бабушка» / Баба Аня сравнение — потеряно
- Дороговизна 90-х — потеряно
- Продажа дачи — потеряно
- Хрущевское сокращение армии 1962 (historical_note) — потеряно
- Историческая реплика «Химинститут — типичный научный посёлок 1960-х» — потеряно
- Разные отцы у Валентины и сестёр — потеряно
- ДК «Синтетик», Татьяна водила Никиту на аэробику — потеряно
- Почерк с отрицательным наклоном — потеряно

**Это Класс 5** — universally применимо: каждая биография имеет pin-list эпизодов которые должны быть в книге.

---

## Спек

### Что нужно изменить / создать

**1. Pin-list v2 уже создан** (`collab/context/known_episodes_karakulina.md` v2) — содержит:
- `episodes` (30 хронологических + 1a/1b/13a/14a/28a)
- `bytovye` (20 бытовых)
- `traits` (12 характеристик)
- `characteristic_words` (6 слов)
- `historical_notes_anchors` (11 точек)
- `bio_data.timeline_anchors` (используется в task 045)
- `relation_overrides` (используется в task 044)
- `epilogue_antitriggers` (используется в task 043)

**2. Структура pin-list передаётся в GW input** (Stage 2):

В `scripts/test_stage2_pipeline.py` добавить шаг:
- Прочитать `known_episodes_<subject>.md` → парсить таблицы → формировать структурированный pin-list:

```python
pin_list_for_gw = {
    "episodes": [
        {"episode_id": "ep_001", "title": "Голод 1933 + детдом + Полина", "year": 1933,
         "markers": ["голод", "1933", "детдом", "Полина", "Старобельск"],
         "must_include": ["мать умерла", "брат умер", "отец ушёл на заработки"]},
        # ... остальные 30+ эпизодов
    ],
    "bytovye": [...],
    "traits": [...],
    "characteristic_words": ["выковыривал", "зарубиться", "зажиточные", "движуха", "рукастый", "бабульно"]
}
```

**3. Промпт Ghostwriter v2.19** (`prompts/ghostwriter_v2.18.md` → `v2.19.md`):

Новый раздел (после правил стиля):

```
## PIN_LIST_EVENTS — обязательные эпизоды

Тебе предоставлен `pin_list.episodes` — список ключевых эпизодов биографии, которые ОБЯЗАНЫ присутствовать в книге развёрнуто (≥3 предложения каждый, с конкретикой), кроме случаев когда:
- эпизод явно противоречит другому факту (тогда в revision_log пометь `conflict: <ep_id>`)
- эпизод недостаточно подтверждён source (тогда `low_confidence: <ep_id>`)

Для каждого эпизода в pin_list.episodes:
- Найди соответствующее событие/факт в fact_map.timeline
- Развёрнуто опиши в одной из глав (хронологические — обычно в ch_02; бытовые — в ch_03/ch_04)
- Используй слова рассказчика (характерные слова из pin_list.characteristic_words если контекст подходит)
- НЕ свёртывай в одну фразу. Если эпизод про огурцы — это минимум 3 предложения: что привёз, что случилось, реакция семьи.

В revision_log добавь массив `pin_list_coverage`:
- `[{episode_id: "ep_024", chapter_id: "ch_04", coverage: "full|partial|skipped", reason: "..."}]`

Для **антитриггеров** (например, причина огурцов «потому что не привозит подарки» — НЕ в источнике):
- НЕ повторяй causal connection описанную в антитриггерах
- Если CA description содержит такую связку — игнорируй её, используй только source_quote
```

**4. Скрипт `validate_pin_list_coverage(book, pin_list) -> report`** в `pipeline_utils.py`:

Алгоритм:
1. Для каждого `pin_list.episodes[]`:
   - Грепнуть `markers` в `book.chapters[].content` + paragraphs
   - count_markers_found
   - Если `count_markers_found >= ceil(len(markers)*0.6)` → `coverage: "full"`
   - Если `count_markers_found >= 1` → `coverage: "partial"`
   - Иначе → `coverage: "skipped"`
   - Для `must_include` — отдельная проверка: если есть в must_include но не нашлось → flag
2. Аналогично для `bytovye`, `traits`, `characteristic_words`
3. Возвращает `{episodes: [{ep_id, coverage, chapter_id, snippet}], summary: {full: N, partial: M, skipped: K}}`

**5. Скрипт `diff_episodes_between_versions(book_v_N, book_v_N_minus_1, pin_list) -> report`**:

Алгоритм:
1. Прогнать `validate_pin_list_coverage` на обоих versions
2. Сравнить:
   - Эпизоды которые были `full` в v_(N-1) но стали `partial`/`skipped` в v_N → flag `regression`
   - Эпизоды которые были `skipped` в v_(N-1) но стали `full` в v_N → log `improvement`
3. Если `regression.count >= 3` → flag `verdict: regression_detected`

**6. Интеграция в Stage 2 + Stage 3 runners**:
- В Stage 2 runner: после GW финального revision — `validate_pin_list_coverage(book, pin_list)` → `<run>_pin_coverage.json`
- В Stage 3 runner: после LE + integrity scripts — `diff_episodes_between_versions(v_N, v_baseline=v56)` → `<run>_episode_diff.json`
- Baseline для diff фиксируется в `pipeline_config.json` (initially v56)

### Какой результат ожидается

В v58 `<run>_pin_coverage.json`:
- Эпизоды full: ≥25/31
- Эпизоды partial: ≤4
- Эпизоды skipped: ≤2

В `<run>_episode_diff.json` (vs v56):
- regression count: 0 (огурцы развёрнуты обратно, дача и т.п.)
- improvement count: ≥5 (новые из pin-list v2: операция желудок, хрущевское, разные отцы, ...)

Конкретно ожидаемые улучшения в v58 нарративе:
- Огурцы развёрнуты в ch_04 (полный эпизод чемодана)
- Карты и домино — отдельное упоминание в ch_04
- Грибы/ягоды + тётя Маша-соседка — в ch_04 как бытовая деталь
- Шарлотка в кулинарном перечне ch_04
- Сравнение «французской бабушки» с бабой Аней — в ch_03
- Дороговизна 90-х — в ch_03 «характер» или ch_02
- Продажа дачи — в ch_02 ближе к концу
- Хрущевское сокращение армии — historical_note в ch_02 1962
- «Химинститут — типичный научный посёлок» — historical_note в ch_02
- Разные отцы — в ch_01 (раздел Семья note) и/или в ch_02 (контекст детства)
- ДК Синтетик аэробика — в ch_04
- Почерк с отрицательным наклоном — в ch_04

### Как проверить

1. **Unit-тесты** `tests/test_pin_list_coverage.py`:
   - episode markers found ≥60% → coverage="full"
   - episode markers found 1-59% → "partial"
   - episode markers found 0 → "skipped"
   - must_include not satisfied → flag
   - Idempotent

2. **Unit-тесты** `tests/test_episode_diff.py`:
   - v56=full, v57=partial → regression flag
   - v56=skipped, v58=full → improvement log
   - ≥3 regressions → verdict failure

3. **Integration**:
   - Прогнать `validate_pin_list_coverage` на v56 + v57:
     - v56: огурцы=full, карты=full, грибы=full
     - v57: огурцы=partial, карты=skipped, грибы=skipped → diff показывает 3 regressions ✅ correct
   - Прогнать diff v56 vs v57 → должно показать 5-7 regressions (что мы и видим)

4. **Verified-on-run** v58:
   - Открыть `<run>_pin_coverage.json` — full ≥25, skipped ≤2
   - Открыть text_FULL.md, проверить наличие 12 конкретных эпизодов выше

---

## Ограничения

- [ ] Pin-list — `collab/context/known_episodes_<subject>.md` — источник правды. Парсер должен быть устойчив к markdown структуре.
- [ ] GW v2.19 — расширение, сохраняет v2.18 (5 стилистических фиксов, ЗАПРЕТ 8-10)
- [ ] Diff baseline — параметризуемый (initial v56, обновится после v58 sign-off)
- [ ] НЕ блокировать pipeline на regression — только flag (Batch 3 решит hard-fail)
- [ ] Pin-list **per subject** — для Корольковой будет свой pin-list (не hardcode Каракулиной)
- [ ] Idempotent

---

## Dev Review

**Статус:** ожидает

**[TECH]** — пред-резолв:
- Промпт GW v2.19 + pin-list блок — может пересечь лимит 2000 строк (task 037). Если +pin-list блок > 100 строк → task 037 trigger (промпт refactor). Курсор оценивает на этапе implementation.
- Парсер markdown pin-list — нужен для парсинга `known_episodes_karakulina.md` таблиц. Альтернатива: переписать pin-list в JSON (`known_episodes_karakulina.json`). **Решение**: оставить markdown для human-readability, написать парсер таблиц (5-10 строк Python).
- Diff baseline хранится в `pipeline_config.json` ключ `pin_list_diff_baseline_version: "v56"`.

**[PRODUCT]** — нет.

**Оценка сложности:** `m`-`l` (8+ ч если включая GW v2.19 промпт; parser ~2 ч, validate_coverage ~2 ч, diff ~2 ч, integration ~2 ч)
**Оценка риска:** `medium` (промпт GW меняется — нужна верификация что v2.18 правила сохранились)

---

## Реализация

**Статус:** ожидает

---

## Verified-on-run

**Cursor:** [после v58]
**Claude:** [Опус откроет text_FULL.md + pin_coverage report + episode_diff report]

---

## История статусов

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-17 | `outline` | Опус |
| 2026-05-17 | `new` (полный spec) | Опус (роль архитектор+продакт) |
