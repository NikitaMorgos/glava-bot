# Задача 045c: Chapter sections anchors — extension Класса 10 на ch_03 / ch_04

**Статус:** `new`
**Номер:** 045c
**Автор:** Опус (роль архитектор+продакт)
**Дата создания:** 2026-05-17
**Тип:** конфиг + `cco-скрипт`
**Batch:** v60 sprint
**Связано:** task 045/045b (timeline anchors в ch_01); Никитин feedback v59 «из Портрета человека пропало гостеприимство и кулинарные таланты»

---

## Контекст

В v57 ch_03 «Портрет человека» имел разделы: Характер / Труд / Этика / Порядок и чистота / Красота и вкус к прекрасному / Принципиальность / Гостеприимство и кулинарные таланты / Строгость

В v59 ch_03 содержит: Стойкость / Труд / Советская этика / Порядок и красота / Честность / Требовательность и забота

❌ **Пропало**: «Гостеприимство и кулинарные таланты», «Красота и вкус к прекрасному» (слилось с «Порядок»)

**Корень:** ch_03 не имеет structural anchors (как ch_01 bio_data.timeline). GW свободно выбирает разделы → между прогонами **стохастика**.

Универсально — каждая глава портрета должна иметь required sections (как timeline для биографии).

## Universality check

- [x] Промпт — n/a (анкеры в конфиге)
- [x] Subject-specific — chapter_sections_anchors per subject в JSON конфиге
- [x] Алгоритм generic — extend task 045b на любую главу
- [x] Subject-replacement test — для Корольковой свои anchors ch_03 ✅

---

## Спек

### Что нужно изменить

**1. `collab/context/chapter_sections_anchors_<subject>.json`** — новый файл:

```json
{
  "subject_id": "karakulina",
  "chapters": {
    "ch_03": {
      "min_sections": 5,
      "max_sections": 8,
      "anchors": [
        {
          "anchor_id": "character",
          "title_keywords": ["характер", "стойкость", "выкованный"],
          "required": true
        },
        {
          "anchor_id": "labor_love",
          "title_keywords": ["труд", "работа", "забота через дело"],
          "required": true
        },
        {
          "anchor_id": "ethics_beliefs",
          "title_keywords": ["этика", "убеждения", "коммунист", "принципы"],
          "required": true
        },
        {
          "anchor_id": "order_cleanliness",
          "title_keywords": ["порядок", "чистота", "аккуратност"],
          "required": true
        },
        {
          "anchor_id": "beauty_aesthetics",
          "title_keywords": ["красота", "вкус", "прекрасн", "элеганц"],
          "required": false
        },
        {
          "anchor_id": "hospitality_cooking",
          "title_keywords": ["гостеприимств", "хлебосольств", "кулинар", "готовила", "блюда"],
          "required": true
        },
        {
          "anchor_id": "strictness_demanding",
          "title_keywords": ["строгость", "требовательн", "сварлив"],
          "required": false
        }
      ]
    },
    "ch_04": {
      "min_episodes": 6,
      "max_episodes": 10,
      "anchors": []  // ch_04 — list of episodes, не sections
    }
  }
}
```

**2. Функция `validate_chapter_sections_anchors(book, anchors_config) -> report`** в `pipeline_utils.py`:

Алгоритм (analogous to task 045b timeline anchors):
1. Для каждой главы в `anchors_config.chapters`:
   - Парсить `chapter.content` markdown — извлечь `## headers`
   - Для каждой anchor — поиск title match по `title_keywords`
   - Если required anchor отсутствует → flag `anchor_missing`
   - Если actual sections < min или > max → flag `section_count_out_of_range`

2. Возвращает report.

**3. Функция `enforce_chapter_sections_anchors(book, anchors_config) -> book`** (опционально):

- НЕ auto-create секции (риск выдумывания контента)
- Только flag для human review (или GW iterate)

**4. Минорный GW v2.20 промпт-патч ПРАВИЛО 11 (universal):**

```
### ПРАВИЛО 11 — CHAPTER SECTIONS ANCHORS (universal)

Для ch_03 (портрет человека) — обязательно include sections из fact_map.chapter_sections_anchors.ch_03 с `required: true`. 

Минимум 5 разделов, максимум 8. Каждый раздел — отдельный аспект характера/быта/убеждений субъекта.

Для ch_04 (интересные факты) — список эпизодов из fact_map.pin_list.bytovye, минимум 6 максимум 10.
```

### Какой результат ожидается

В v60 ch_03 имеет 5-7 sections включая обязательные:
- ✅ Стойкость/характер
- ✅ Труд
- ✅ Этика/убеждения
- ✅ Порядок/чистота
- ✅ **Гостеприимство и кулинария** (восстановлено)
- ⚠️ Красота/эстетика (если material есть)
- ⚠️ Принципиальность

### Как проверить

1. **Unit-тесты** `tests/test_chapter_sections_anchors.py`:
   - 7 anchors all found → PASS
   - 3 required anchors missing → 3 flags
   - section count out of range → flag

2. **Integration** на v57 ch_03 (где gostepreemstvo было) + v58c/v59 (где нет):
   - v57 → all required PASS
   - v58c/v59 → flag `anchor_missing: hospitality_cooking`

3. **Verified-on-run** v60:
   - chapter_sections_anchors.json — все required PASS
   - text_FULL ch_03 содержит «Гостеприимство и кулинария» раздел

---

## Ограничения

- [ ] НЕ auto-create секции (только flag)
- [ ] Anchors per subject (Каракулина имеет hospitality_cooking как required, Королькова может иметь другое)
- [ ] Idempotent
- [ ] Universal mechanism

---

## Dev Review

**Статус:** ожидает
**[TECH]** — chapter_sections_anchors_<subject>.json — новый конфиг, параллельно timeline_anchors_<subject>.json
**[PRODUCT]** — нет
**Сложность:** `s` (1-3 ч)
**Риск:** `low`

---

## История

| Дата | Статус | Кто |
|---|---|---|
| 2026-05-17 | `new` | Опус |
