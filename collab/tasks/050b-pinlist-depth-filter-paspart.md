# Задача 050b: Pin-list depth filter — исключить ch_01 paspart из проверки

**Статус:** `spec-approved`
**Номер:** 050b
**Автор:** Опус
**Дата создания:** 2026-05-17
**Тип:** `cco-скрипт`
**Batch:** v60 sprint (patch to 050)

---

## Контекст

Task 050 ввёл `validate_pin_list_depth`. В v59 отчёт `pin_list_depth.json` содержит errors для pin-list эпизодов, у которых **best-match параграф находится в ch_01** (паспортичка). 

Например, эпизод «Рождение Татьяны 1956» может иметь маркеры «Татьяна», «1956» — они совпадают с краткой строкой паспортички `{"label": "Дочь", "value": "Татьяна (родилась в 1956 году, Тверь)"}`. Это **1 предложение → error depth < 3**.

Но паспортичка — справочный блок, не нарратив. Depth check должен применяться только к нарративным главам (ch_02, ch_03, ch_04).

## Universality check

1. ✅ Изменение generic
2. ✅ Subject-independent
3. ✅ Алгоритм: фильтрация ch_01
4. ✅ Subject-replacement test ✅

---

## Спек

**В `pipeline_utils.py`, функция `validate_pin_list_depth`:**

В `all_paragraphs` — фильтровать параграфы только из нарративных глав:

```python
NARRATIVE_CHAPTERS = {"ch_02", "ch_03", "ch_04", "epilogue"}
```

Параграфы из ch_01 — **пропустить** при формировании `all_paragraphs`.

---

## Verified-on-run критерий

«pin_list_depth errors ≤3 (только real narrative issues, не paspart)»

Конкретно: открыть `pin_list_depth.json` → `depth_issues` → все issues должны иметь `chapter_id` ∈ {ch_02, ch_03, ch_04, epilogue}.

---

## Dev Review

**[TECH]** — нет флагов. Добавить filter на NARRATIVE_CHAPTERS в существующую функцию.
**[PRODUCT]** — нет.
**Сложность:** `xs`
**Риск:** `low`

---

## История

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-17 | `spec-approved` | Опус |
