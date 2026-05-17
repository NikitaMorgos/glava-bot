# Задача 051: Класс 15 — Temporal place names (Калинин → Тверь)

**Статус:** `spec-approved`
**Номер:** 051
**Автор:** Опус
**Дата создания:** 2026-05-17
**Тип:** `cco-скрипт` + промпт GW ПРАВИЛО 9 + конфиг
**Batch:** v60 sprint (новый класс)

---

## Контекст

Город Тверь до 1991 года назывался Калинин. Татьяна Каракулина родилась в 1956 в **Калинине**. В v59 GW пишет «родилась в Твери» в паспортичке и нарративе — это **фактическая ошибка** (Никита flagged).

**Класс 15 — Temporal place names:** топонимы, изменившиеся со временем. Правило: использовать название, актуальное для **того периода**, о котором речь.

## Universality check

1. ✅ ПРАВИЛО 9 — universal categorical без Каракулиноспецифики: «для событий до [year_limit] используй [old_name], после — [new_name]»
2. ✅ Конфиг `temporal_place_names_karakulina.json` — subject-specific даты и пары
3. ✅ Алгоритм generic — читает конфиг + book
4. ✅ Subject-replacement test: для Корольковой — свой конфиг ✅

---

## Спек

### 1. Новый конфиг `collab/context/temporal_place_names_karakulina.json`

```json
{
  "temporal_place_names": [
    {
      "old_name": "Калинин",
      "new_name": "Тверь",
      "old_name_variants": ["Калинин", "Калинина", "Калинине", "Калинином"],
      "new_name_variants": ["Тверь", "Твери", "Тверью"],
      "transition_year": 1991,
      "note": "Тверь переименована обратно из Калинина в 1990/1991"
    }
  ]
}
```

### 2. Новые функции в `pipeline_utils.py`

```python
def validate_temporal_place_names(book, fact_map, temporal_config):
    """Проверяет корректность временных топонимов в книге."""
    
def enforce_temporal_place_names(book, fact_map, temporal_config):
    """Заменяет неверные топонимы на корректные для данного периода."""
```

Алгоритм:
1. Для каждого абзаца — определить год события (из surrounding context / date mentions)
2. Если абзац содержит `new_name` и год < `transition_year` → заменить на `old_name`
3. Если абзац содержит `old_name` и год ≥ `transition_year` → заменить на `new_name`
4. Paspart (ch_01 bio_data) — использовать год рождения субъекта для определения топонима

### 3. GW v2.21 — ПРАВИЛО 9

```
ПРАВИЛО 9: ИСТОРИЧЕСКИЕ НАЗВАНИЯ МЕСТ
Для каждого события используй название города/региона, актуальное для периода события.
Список переименований доступен в temporal_place_names config.
Если событие до [transition_year] — используй [old_name].
Если событие после [transition_year] — используй [new_name].
Для года рождения [субъекта] — используй [old_name] если родился(ась) до transition_year.
```

### 4. Интеграция в Stage 3 runner

После `normalize_book_topo` — вызов `enforce_temporal_place_names`.
Отчёт: `temporal_place_naming.json`.

---

## Verified-on-run критерий

«paspart Татьяны имеет «родилась в 1956 году в Калинине» (не Твери); narrative ch_02 1950-е использует Калинин»

---

## Dev Review

**[TECH]** — нет флагов. Новые функции + конфиг + ПРАВИЛО 9 GW v2.21.
**[PRODUCT]** — нет.
**Сложность:** `s`
**Риск:** `medium` (новые функции, тесты нужны)

---

## История

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-17 | `spec-approved` | Опус |
