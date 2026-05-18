# Задача 044c: Relation overrides — apply to final book (bug fix)

**Статус:** `new`
**Номер:** 044c
**Автор:** Опус (роль архитектор+продакт)
**Дата создания:** 2026-05-17
**Тип:** `cco-скрипт`
**Batch:** v60 sprint
**Связано:** task 044/044b; diagnostic v59: relation_overrides_applied показывает 3 corrections с `in_bio_data_family: false`, но баба Аня **присутствует** в final bio_data.family как «Свекровь»

---

## Контекст

В v59 `relation_overrides_applied_20260517_175649.json`:
```json
{
  "corrections": [
    {"person_name": "тётя Маша", "real_relation": "соседка", "in_bio_data_family": false},
    {"person_name": "Нинвана Полсачева", "real_relation": "врач, авторитет", "in_bio_data_family": false},
    {"person_name": "баба Аня", "real_relation": "свекровь рассказчика", "in_bio_data_family": false}
  ]
}
```

Но в `book_FINAL_stage3.bio_data.family`:
- ✅ Тётя Маша — отсутствует (override сработал)
- ✅ Нинвана — отсутствует (override сработал)
- ❌ **Баба Аня — присутствует** как `{"label": "Свекровь", "value": "баба Аня, мать зятя Владимира Маргося"}`

**Корень:** override был **applied к fact_map**, но **enforce_bio_data_completeness** позже (или через другой pathway) добавил бабу Аню обратно в family. Где-то добавление **обходит** override flag.

Гипотеза: `required_persons` из pin-list parser (task 044b) — если pin-list содержит бабу Аню как «свекровь рассказчика», она force-добавляется в family, **игнорируя** override `in_bio_data_family: false`.

## Universality check

- [x] Промпт — n/a (скриптовый fix)
- [x] Конфиги per subject — relation_overrides и pin-list per subject уже сделаны
- [x] Алгоритм generic — fix применим для всех subjects
- [x] Subject-replacement test — для Корольковой свекровь её зятя НЕ должна попасть в её family ✅

---

## Спек

### Что нужно изменить

**1. Дебаг где override игнорируется** в `pipeline_utils.py`:
- В `apply_relation_overrides` (или `enforce_bio_data_completeness`) проверить порядок:
  - Override flag `in_bio_data_family: false` должен **остановить** добавление persona в `bio_data.family`
  - Если **уже** добавлена — должна быть удалена

**2. Возможные пути fix (выбрать):**

**Вариант A (preferred):** Расширить `filter_bio_data_family_by_relation_whitelist`:
- После whitelist filter — дополнительно фильтровать по `relation_overrides` где `in_bio_data_family: false`
- Любая persona в bio_data.family с name match'ем в overrides И flag false → удалить

**Вариант B:** Изменить `apply_relation_overrides`:
- Если persona имеет flag `in_bio_data_family: false` — добавить в fact_map.persons поле `skip_in_bio_data: true`
- `enforce_bio_data_completeness` и `required_persons` логика — пропускать persons с `skip_in_bio_data`

**3. Дополнительно — `relation_overrides_<subject>.json` schema** уточнить:

```json
{
  "subject_id": "karakulina",
  "overrides": [
    {
      "person_name": "баба Аня",
      "real_relation": "свекровь рассказчика (мать Владимира Маргося)",
      "in_bio_data_family": false,
      "in_bio_data_contributors": false,   // на всякий случай для task 052
      "narrative_context": "контекст «французская бабушка» comparison в ch_03"
    }
  ]
}
```

### Какой результат ожидается

В v60 bio_data.family:
- ❌ Баба Аня **отсутствует** (не «Свекровь»)
- Final family count: 23 (вместо v59=24)

В narrative — баба Аня остаётся в ch_03 как контекст «французская бабушка» comparison.

### Как проверить

1. **Unit-тест** `tests/test_relation_overrides_apply.py`:
   - Persona с `in_bio_data_family: false` + name в pin-list `required_persons` → НЕ в bio_data.family
   - Тётя Маша / Нинвана / Баба Аня все три → НЕ в family

2. **Integration** на v59 fact_map+book:
   - Re-run filter — баба Аня должна быть удалена

3. **Verified-on-run** v60:
   - `bio_data.family` без бабы Ани
   - В нарративе ch_03 «французская бабушка» сравнение сохраняется

---

## Ограничения

- [ ] НЕ удалять persona из fact_map.persons — она остаётся для narrative (только flag in_bio_data_family)
- [ ] Idempotent
- [ ] Universal

---

## Dev Review

**Статус:** ожидает
**[TECH]** — `required_persons` логика task 044b может перетирать override; обе функции должны кооперировать
**[PRODUCT]** — нет
**Сложность:** `xs` (<1 ч)
**Риск:** `low`

---

## История

| Дата | Статус | Кто |
|---|---|---|
| 2026-05-17 | `new` | Опус |
