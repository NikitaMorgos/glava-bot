# Задача 045: bio_data.timeline structural anchor — фиксация скелета биографии

**Статус:** `new`
**Номер:** 045
**Автор:** Опус (роль архитектор+продакт)
**Дата создания:** 2026-05-17
**Тип:** `cco-скрипт`
**Batch:** 2 (после v57 verified)
**Связано:** stocktake 2026-05-17 **Класс 10** (новый, обнаружен v57); pin-list v2 раздел «bio_data.timeline anchors»

---

## Контекст

**Класс 10 — bio_data.timeline structural regression** (новый класс v57):

В v56 `bio_data.timeline` имел **7 разделённых периодов**:
1. 1920–1933. Детство и сиротство
2. 1938–1940. Медицинское образование
3. 1941–1945. Война и военная служба
4. 1946–1961. Замужество и жизнь за границей
5. 1962–1978. Жизнь в Химинституте
6. 1978–1996. Вдовство и работа
7. 1996–2005. Последние годы

В v57 — **6 периодов**, склейка «1938–1945. Учёба и война» (учёба превратилась в подабзац войны, потеря деталей фельдшерско-акушерской школы как самостоятельного этапа жизни).

Дашин/Никитин feedback: «деградация по сравнению с v56, надо как-то откатываться к ней».

**Корень:** GW сам решает структуру `bio_data.timeline` (количество периодов, разделители) без жёстких anchors. Стохастика между прогонами.

Это **Класс 10**, универсально для всех subjects: каждая биография имеет свой набор anchor-периодов, которые **должны** быть разделены. Чисто скриптовое решение.

---

## Спек

### Что нужно изменить / создать

**1. `collab/context/timeline_anchors_<subject>.json`** — новый файл per subject:

```json
{
  "subject_id": "karakulina",
  "version": "v1",
  "min_periods": 7,
  "anchors": [
    {
      "anchor_id": "childhood",
      "title_keywords": ["детство", "сиротство", "Мариевка"],
      "year_range": "1920-1933",
      "required_events": ["голод 1933", "детдом", "Полина"],
      "merge_forbidden_with": []
    },
    {
      "anchor_id": "education",
      "title_keywords": ["образование", "учёба", "акушерск", "Кировоград"],
      "year_range": "1938-1940",
      "required_events": ["фельдшерско-акушерская школа"],
      "merge_forbidden_with": ["war"]
    },
    {
      "anchor_id": "war",
      "title_keywords": ["война", "военная служба", "госпиталь", "фронт"],
      "year_range": "1941-1945",
      "required_events": ["призыв 23 июня 1941", "медаль 1943", "Красная Звезда 1945"],
      "merge_forbidden_with": ["education"]
    },
    {
      "anchor_id": "family_early",
      "title_keywords": ["замужество", "Германия", "Венгрия"],
      "year_range": "1946-1961",
      "required_events": ["Дмитрий 1946", "Валерий 1948", "Татьяна 1956", "Венгрия 1958-62"]
    },
    {
      "anchor_id": "khim_institute",
      "title_keywords": ["Химинститут", "поликлиник"],
      "year_range": "1962-1978",
      "required_events": ["переезд 1962", "Ударник 1965", "брак Татьяны 1977"]
    },
    {
      "anchor_id": "widowhood",
      "title_keywords": ["вдовство", "пенси", "одна"],
      "year_range": "1978-1996",
      "required_events": ["смерть Дмитрия 1978", "пенсия 1994"]
    },
    {
      "anchor_id": "last_years",
      "title_keywords": ["последние", "Капошвар", "переезд"],
      "year_range": "1996-2005",
      "required_events": ["Кужба 1996", "перелом 2005"]
    }
  ]
}
```

**2. Функция `validate_timeline_anchors(book, anchors_config) -> report`** в `pipeline_utils.py`:
- Прочитать `bio_data.timeline` (или Структурированный блок «Основные периоды жизни» в ch_01.content если timeline пустой)
- Для каждого anchor:
  - Поиск period match: title содержит `title_keywords[≥1]` ИЛИ year_range пересекается
  - Проверка `required_events`: ≥ половина events найдены в period.text (grep по их keywords)
  - Если anchor не найден → flag `anchor_missing`
  - Если найдены merge (два anchors попадают в один period) → flag `anchor_merge`
- Возвращает `{anchors_found: [...], anchors_missing: [...], merges: [...]}`
- Идемпотентно

**3. Функция `enforce_timeline_anchors(book, anchors_config, fact_map) -> book`** в `pipeline_utils.py`:
- Если `validate_timeline_anchors` возвращает issues:
  - **НЕ auto-generate periods** (риск выдумывания контента)
  - **Auto-split** только если period title содержит **оба** anchor titles (например «Учёба и война») И в period.text есть содержание для обоих:
    - Разделить period на 2: один с education year_range, другой с war
    - Скопировать содержание соответственно (по keyword-matching)
  - Если auto-split невозможен (нет содержания одного из anchors) → flag для human review, не патчить
- Сохранить отчёт `<run>_timeline_anchors_<ts>.json`

**4. Интеграция в Stage 3 runner**:
- После `enforce_persona_notes` (task 044):
  - `validate_timeline_anchors`
  - `enforce_timeline_anchors` (если есть merges или missing с возможностью auto-split)
- Если remaining issues после enforce → НЕ failure, но логируем для verified-on-run

### Какой результат ожидается

В v58 `bio_data.timeline` имеет **7 разделённых периодов** (или ≥7). 

Конкретно: «Учёба» (1938-1940) — отдельный period с фельдшерско-акушерской школой; «Война» (1941-1945) — отдельный period с госпиталем, фронтами, наградами.

В отчёте `<run>_timeline_anchors_v58.json`:
- `anchors_found`: 7/7
- `anchors_missing`: []
- `merges`: []

### Как проверить

1. **Unit-тесты** `tests/test_timeline_anchors.py`:
   - 7 разделённых periods → all found, no merges
   - «Учёба и война» склейка → merge detected, auto-split if both contents present
   - Missing period (нет образования вообще) → flagged, no auto-create
   - Idempotent

2. **Integration** на v56 (где было 7) и v57 (где 6):
   - v56 → 7/7 found, 0 merges
   - v57 → 6 found, 1 merge («Учёба и война» merge), auto-split should work

3. **Verified-on-run** v58:
   - Открыть `karakulina_v58_text_FULL.md` секция «Основные периоды жизни»
   - Подсчитать `**N-N. Название**` блоки — должно быть 7

---

## Ограничения

- [ ] НЕ выдумывать контент периодов (auto-create запрещён)
- [ ] Auto-split только если оба anchor contents явно присутствуют в склеенном period
- [ ] НЕ менять промпт GW — это пост-процессинг (если потребуется промпт-патч — отдельной задачей)
- [ ] Idempotent

---

## Dev Review

**Статус:** ожидает

**[TECH]** — пред-резолв:
- Title `bio_data.timeline` в book_FINAL_stage3 — это **массив объектов** или **markdown в ch_01.content**? Проверить — task 039 показала что в v56 `chapters[ch_01].bio_data.timeline` имел поле, но build_gate1 рендерил из markdown. Если структура расходится — синхронизировать.
- Auto-split — нетривиальная операция. Если оба contents в одном period не получается разделить — flag, не autopatch.

**[PRODUCT]** — нет (anchors per subject — мой draft, можно расширить если Никита захочет 8-й anchor).

**Оценка сложности:** `m` (3-8 ч; основная сложность в auto-split logic)
**Оценка риска:** `medium` (трогает структуру bio_data — может задеть Stage 4 рендер)

---

## Реализация

**Статус:** ожидает

---

## Verified-on-run

**Cursor:** [после v58]
**Claude:** [Опус подсчитает периоды в text_FULL.md секция «Основные периоды жизни»]

---

## История статусов

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-17 | `new` | Опус |
