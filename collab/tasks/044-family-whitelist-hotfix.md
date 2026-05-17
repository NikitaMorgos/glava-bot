# Задача 044: Family whitelist hotfix — manual relation overrides + persona notes preservation

**Статус:** `new`
**Номер:** 044
**Автор:** Опус (роль архитектор+продакт)
**Дата создания:** 2026-05-17
**Тип:** `cco-скрипт`
**Batch:** 2 (после v57 verified)
**Связано:** task 039 (Batch 1 — частично закрыла Класс 3); stocktake 2026-05-17 Класс 2 + Класс 3; pin-list v2

---

## Контекст

В v57 task 039 (bio_data integrity) частично закрыла Класс 3, но осталось 2 проблемы:

**Регрессия 1 — Класс 3 (family attribution mismatch):**
- **Тётя Маша** всё ещё в `bio_data.family` как «Тётя» — CA лейблит `relation_to_subject="тётя"` (потому что рассказчики называют «тётя Маша»), whitelist task 039 это пропускает. Реально она **соседка**, не родственница. TR1: «это в основном **тётя Маша и её соседка** были любителями [грибов]».
- **Баба Аня** в render text_FULL (через build_gate1) как «Свекровь или родственница зятя» — она **свекровь рассказчика (Татьяны)**, не свекровь Валентины. НЕ родственница субъекту.

**Регрессия 2 — Класс 2 (bio_data note volatility):**
- Полина: v56 note «забрала из детдома» → v57 «жила в Старобельске» (другой смысл, потеря акта спасения)
- Татьяна: потерян note «рассказчик интервью»
- Племянники: потеряны notes «сын тёти Поли»
- Племянницы: потеряны notes «дочь тёти Шуры»
- Внук + Внучка склеены в одну строку «Внуки: Никита, Даша»

**Корень:** GW сам переписывает notes между прогонами без обязательной фиксации; `enforce_bio_data_completeness` не сохраняет notes/раздельность из pin-list.

Универсальная проблема для всех subjects. Чисто скриптовое решение.

---

## Спек

### Что нужно изменить / создать

**1. `collab/context/relation_overrides_<subject>.json`** — новый файл per subject:

```json
{
  "subject_id": "karakulina",
  "version": "v1",
  "overrides": [
    {
      "person_name": "тётя Маша",
      "aliases": ["Маша", "Маша соседка"],
      "ca_relation": "тётя",
      "real_relation": "соседка",
      "in_bio_data_family": false,
      "narrative_context": "соседка, любила ходить по грибы и ягоды (TR1)",
      "source_quote": "это в основном тётя Маша и её соседка любителем была"
    },
    {
      "person_name": "Баба Аня",
      "aliases": ["баба Ани"],
      "ca_relation": "свекровь или родственница зятя",
      "real_relation": "свекровь рассказчика (мать Владимира Маргось)",
      "in_bio_data_family": false,
      "narrative_context": "контекст «французская бабушка» comparison в ch_03",
      "source_quote": "сравнить отношения бабы Ани, да, к тебе"
    },
    {
      "person_name": "Нинвана Полсачева",
      "ca_relation": "знакомая",
      "real_relation": "врач, авторитет",
      "in_bio_data_family": false,
      "narrative_context": "врач, постоянный авторитет в вопросах здоровья (ch_03)"
    }
  ]
}
```

**2. `collab/context/persona_notes_<subject>.json`** — обязательные notes:

```json
{
  "subject_id": "karakulina",
  "version": "v1",
  "required_notes": [
    {"label_match": "Полина", "note": "забрала из детдома"},
    {"label_match": "Татьяна", "note": "рассказчик интервью"},
    {"label_match": "тётя Шура", "note": "сестра мужа, жила в Кирсанове Тамбовской области"},
    {"label_match": "Амельченко", "note": "сын тёти Поли"},
    {"label_match": "Толя", "note": "из Белгорода, сын тёти Поли"},
    {"label_match": "Коля", "note": "лётчик, сын тёти Поли"},
    {"label_match": "Витя", "note": "из Энгельса, сын тёти Поли"},
    {"label_match": "Римма", "note": "дочь тёти Шуры"},
    {"label_match": "Зина", "note": "дочь тёти Шуры"}
  ],
  "separate_entries_required": [
    {"label": "Внук", "value": "Никита"},
    {"label": "Внучка", "value": "Даша"}
  ]
}
```

**3. Функция `apply_relation_overrides(fact_map, overrides) -> fact_map`** в `pipeline_utils.py`:
- Перед `filter_bio_data_family_by_relation_whitelist` (existing) применить overrides:
  - Для каждого person в fact_map.persons: если name matches `overrides[].person_name` или aliases → set `relation_to_subject = real_relation` + flag `relation_corrected: true`
- Возвращает modified fact_map

**4. Расширить `filter_bio_data_family_by_relation_whitelist`**:
- Уже existing после task 039. Теперь после `apply_relation_overrides` whitelist отфильтрует тётю Машу (relation="соседка") и Бабу Аню (relation="свекровь рассказчика", не в whitelist).
- Whitelist остаётся прежним (отец/мать/брат/сестра/.../тётя/...) — overrides меняют **input** до whitelist.

**5. Функция `enforce_persona_notes(book, persona_notes_config) -> book`** в `pipeline_utils.py`:
- После `enforce_bio_data_completeness` и `filter_bio_data_family_by_relation_whitelist`:
  - Для каждого `required_notes[]`:
    - Найти в `bio_data.family` запись где value содержит `label_match` (case-insensitive substring)
    - Если note отсутствует или не содержит ключевые слова из required note → установить required note
    - Если в записи уже есть **другой** note, который **противоречит** required (например, Полина: v57 «жила в Старобельске» vs required «забрала из детдома») — **заменить** на required (с логом)
- Для `separate_entries_required[]`:
  - Найти склееные записи (например `{"label": "Внуки", "value": "Никита, Даша"}`)
  - Разделить на 2 отдельные `{"label": "Внук", "value": "Никита"}` + `{"label": "Внучка", "value": "Даша"}`

**6. Интеграция в Stage 3 runner** (`scripts/test_stage3.py`):
- Цепочка post-LE:
  1. `preserve_chapter_structural_fields` (existing Этап 1)
  2. `apply_relation_overrides` (новое) — на fact_map
  3. `enforce_bio_data_completeness` (existing task 027)
  4. `filter_bio_data_family_by_relation_whitelist` (existing task 039) — теперь с corrected relations
  5. `validate_bio_data_required_fields` (existing task 039)
  6. `enforce_persona_notes` (новое — task 044)
  7. `normalize_book_topo` (existing task 040)
- Отчёт `<run>_relation_overrides_applied.json` + `<run>_persona_notes_enforced.json`

### Какой результат ожидается

В v58 `bio_data.family`:
- ✅ Тётя Маши **НЕТ** в family (она соседка → отфильтрована)
- ✅ Бабы Ани **НЕТ** в family (она свекровь рассказчика → отфильтрована)
- ✅ Полина имеет note «забрала из детдома» (не «жила в Старобельске»)
- ✅ Татьяна имеет note «рассказчик интервью»
- ✅ Племянники Амельченко/Толя/Коля/Витя — каждый с note «сын тёти Поли»
- ✅ Племянницы Римма/Зина — каждая с note «дочь тёти Шуры»
- ✅ Раздельные записи «Внук: Никита» + «Внучка: Даша»
- ✅ Ожидаемое количество записей: **20** (vs v57=19, v56=22 с дублями)

### Как проверить

1. **Unit-тесты** `tests/test_relation_overrides.py` + `tests/test_persona_notes.py`:
   - Override: persona "тётя Маша" с CA relation="тётя" → after apply real_relation="соседка"
   - Whitelist: после apply_overrides тётя Маша отфильтрована
   - Note preservation: Полина с v57 note «жила в Старобельске» → after enforce note=«забрала из детдома»
   - Separate entries: «Внуки: Никита, Даша» → 2 раздельные записи

2. **Integration** на v57 артефактах:
   - Загрузить v57 fact_map + book_FINAL_stage3
   - Прогнать: apply_relation_overrides → filter → enforce_persona_notes
   - Проверить bio_data.family: 20 записей, тётя Маша/баба Аня НЕТ, все notes на месте

3. **Verified-on-run** v58:
   - Открыть `karakulina_v58_text_FULL.md` секция «Семья»: тётя Маша и баба Аня отсутствуют; Полина «забрала из детдома»; Никита и Даша раздельно

---

## Ограничения

- [ ] НЕ менять промпт CA / GW / LE — это пост-процессинг
- [ ] Overrides — explicit per persona (не regex/heuristic) — безопаснее
- [ ] Idempotent: повторный вызов не дублирует, не меняет лишнего
- [ ] Override не должен **скрывать** persona — она остаётся в fact_map.persons (для narrative), только меняется relation_to_subject и in_bio_data_family flag

---

## Dev Review

**Статус:** ожидает

**[TECH]** — пред-резолв от Опуса:
- Whitelist остаётся explicit (как в task 039). Overrides — слой **до** whitelist.
- При conflict («забрала из детдома» vs «жила в Старобельске») — required wins. Логируем замену.
- Separate entries — для bio_data.family, **не** для нарратива (там Никита и Даша могут упоминаться как «внуки»).

**[PRODUCT]** — нет (все продактовые решения мной зафиксированы в pin-list v2).

**Оценка сложности:** `s` (1-3 ч)
**Оценка риска:** `low` (data layer post-processing)

---

## Реализация

**Статус:** ожидает

---

## Verified-on-run

**Cursor:** [после v58]
**Claude:** [Опус откроет text_FULL.md и проверит каждый пункт required_notes]

---

## История статусов

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-17 | `new` | Опус |
