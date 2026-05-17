# Задача 044c: Баба Аня — явное удаление из bio_data.family

**Статус:** `spec-approved`
**Номер:** 044c
**Автор:** Опус
**Дата создания:** 2026-05-17
**Тип:** `cco-скрипт`
**Batch:** v60 sprint (patch to 044)

---

## Контекст

Task 044 ввёл `relation_overrides_karakulina.json` с `in_bio_data_family: false` для Бабы Ани. Однако в v59 она **всё ещё появляется в bio_data.family** в паспортичке.

**Корень:** `apply_relation_overrides` меняет `relation_to_subject` Бабы Ани на «свекровь рассказчика (мать Владимира Маргось)». Затем `filter_bio_data_family_by_relation_whitelist` проверяет содержит ли relation строку «свекровь» — и ДА, содержит! Поэтому Баба Аня **остаётся** в family.

**Исправление:** при `in_bio_data_family: false` — явно удалять из book.bio_data.family, независимо от whitelist.

## Universality check

1. ✅ Промпт не меняется
2. ✅ `in_bio_data_family: false` в JSON конфиге per subject
3. ✅ Алгоритм generic — читает config, применяет флаг
4. ✅ Subject-replacement test: для Корольковой — свои overrides.json ✅

---

## Спек

**Изменение в `pipeline_utils.py`, функция `apply_relation_overrides`:**

После установки corrected relation — дополнительно проверить `in_bio_data_family`. Если `false` — найти запись в `book.bio_data.family` по имени/aliases и **удалить**.

Также: если person уже удалён из fact_map.persons через override — обновить `in_bio_data_family` флаг в person record.

**Сигнатура остаётся прежней:** `apply_relation_overrides(fact_map, overrides_config) -> tuple`

Новый возврат: `(fact_map, bio_family_removals)` где bio_family_removals — список удалённых записей.

Интеграция в test_stage3.py: после вызова `apply_relation_overrides` — применить removals к `book_after_le.chapters[ch_01].bio_data.family`.

---

## Verified-on-run критерий

«bio_data.family — баба Аня отсутствует (только narrative ch_03 как контекст)»

---

## Dev Review

**[TECH]** — нет флагов. Добавление явного удаления в существующую функцию.
**[PRODUCT]** — нет.
**Сложность:** `xs`
**Риск:** `low`

---

## История

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-17 | `spec-approved` | Опус |
