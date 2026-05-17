# Задача 044b: CA pin-list **required persons** (фикс для Марфы / Мани / Риммы / Зины)

**Статус:** `new`
**Номер:** 044b
**Автор:** Опус (роль архитектор+продакт)
**Дата создания:** 2026-05-17
**Тип:** конфиг + минор скрипт
**Batch:** 2-fix
**Связано:** task 044 (relation overrides); diagnostic v58: 4 persons отсутствуют в fact_map

---

## Контекст

Diagnostic v58 fact_map.persons (19) — **отсутствуют**:
- ❌ Бабушка Марфа (была person_019 в v56)
- ❌ Тётя Маня / Мария (старшая сестра, разные отцы)
- ❌ Племянница Римма (дочь тёти Шуры)
- ❌ Племянница Зина (дочь тёти Шуры)

Все 4 имеются в TR1 (грep подтверждает). CA не извлёк (либо слишком короткое упоминание, либо `confidence=low` отфильтровал).

**Корень:** pin-list `known_episodes_karakulina.md` v2 раздел «Прямые родственники» имеет этих persons, но **CA не использует pin-list persons как required** (только episodes).

---

## Спек

### Что нужно изменить

**1. Расширить pin-list parser** (`parse_pin_list_from_markdown` в `pipeline_utils.py`):
- Парсить раздел «Прямые родственники Валентины» / «Прямые родственники <subject>» → список required persons:
```json
{
  "required_persons": [
    {"name": "Марфа", "relation": "бабушка", "note": "мать отца субъекта"},
    {"name": "Мария", "aliases": ["тётя Маня"], "relation": "старшая сестра"},
    {"name": "Римма", "relation": "племянница", "note": "дочь тёти Шуры"},
    {"name": "Зина", "relation": "племянница", "note": "дочь тёти Шуры"}
  ]
}
```

**2. Stage 1 runner**:
- Подаёт `required_persons` в CA input (через `pin_list.persons` — см. task 038b)
- CA ОБЯЗАН добавить каждого required_person в `auto_enrich.persons` (с `was_in_pin_list: true`) — даже если в TR упомянут вскользь
- Если в TR упомянуто только имя без подтверждения родства → `confidence: low` + `needs_verification: true`, но в pin-list попадает

**3. `enforce_bio_data_completeness` (task 027) расширить**:
- После CA + LE + `apply_relation_overrides` (task 044) + `filter_bio_data_family_by_relation_whitelist`:
- Для каждого `required_persons[]` — проверить наличие в `bio_data.family`
- Если отсутствует → добавить с `note` из pin-list, `confidence` пометка остаётся

### Какой результат ожидается

В v59 fact_map.persons:
- ✅ Марфа (relation: бабушка, confidence: low, was_in_pin_list: true)
- ✅ Мария / тётя Маня (relation: старшая сестра, was_in_pin_list: true)
- ✅ Римма (relation: племянница, note: дочь тёти Шуры)
- ✅ Зина (relation: племянница, note: дочь тёти Шуры)

В v59 bio_data.family — **минимум 20 записей** включая всех 4.

### Как проверить

1. **Unit-тесты** `tests/test_required_persons_pinlist.py`:
   - Pin-list содержит Марфа → CA добавляет в auto_enrich даже с минимальным TR mention
   - bio_data.family содержит все required_persons после Stage 3
   - Idempotent

2. **Integration** на v58 transcripts:
   - Прогнать Stage 1 с расширенным pin-list
   - fact_map.persons включает Марфу, Маню, Римму, Зину

3. **Verified-on-run** v59:
   - Открыть text_FULL.md секция «Семья» — все 4 persons присутствуют
   - bio_data.family JSON: 20+ записей

---

## Ограничения

- [ ] Pin-list parser **расширяемый** для других subjects (Королькова, Дмитриев)
- [ ] required_persons из subject-specific pin-list, generic парсер
- [ ] Idempotent

---

## Dev Review

**Статус:** ожидает

**[TECH]** — пред-резолв: confidence=low допускается для force-add persons; UI/render показывает с пометкой «(требует уточнения)» опционально.

**[PRODUCT]** — нет.

**Сложность:** `xs` (<1 ч)
**Риск:** `low`

---

## История

| Дата | Статус | Кто |
|---|---|---|
| 2026-05-17 | `new` | Опус |
