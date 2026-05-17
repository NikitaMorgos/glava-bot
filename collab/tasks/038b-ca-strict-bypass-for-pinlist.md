# Задача 038b: CA v1.3 — bypass strict description для pin-list events

**Статус:** `new`
**Номер:** 038b
**Автор:** Опус (роль архитектор+продакт)
**Дата создания:** 2026-05-17
**Тип:** `промпт` (CA) + минор скрипт
**Batch:** 2-fix
**Связано:** task 038 (CA v1.3 introduced); diagnostic v58: CA over-strict отверг 3 ключевых auto_enrich events

---

## Контекст

CA v1.3 (task 038) ввёл ПРАВИЛА 4-5: «strict description = парафраз source_quote, без новых causal/dates/names». Цель — закрыть Класс 1 (CA confabulation).

**Побочный эффект v58:** CA over-strict — отверг auto_enrich events с описанием которое потенциально дрейфит, **даже если эпизод в pin-list**:
- Огурцы — был event_auto_009 в v56, нет в v58
- Шуба → пианино — был event_auto_008 в v56, нет в v58
- Мельхиоровые ложечки — был event_auto_012 в v56, нет в v58

Все эти эпизоды **в pin-list** (`known_episodes_karakulina.md`) — но CA v1.3 решил «source quote недостаточно strict для description» и **пропустил**.

**Корень:** CA не различает «свободный auto_enrich» (где strict нужен) и «pin-list mandatory» (где источник правды — pin-list, а не sample TR).

---

## Спек

### Что нужно изменить

**1. Промпт CA v1.3 → v1.4** (`prompts/completeness_auditor_v1.3.md` → `v1.4.md`):

Добавить **ПРАВИЛО 6 — Pin-list bypass strict**:

```
### ПРАВИЛО 6 — PIN-LIST EVENTS BYPASS STRICT

Если event/persona/trait из input `pin_list` (поле `is_pin_list_required: true`):
- ПРАВИЛО 4 (strict description) **не применяется** к этому элементу
- description можно делать суммарным парафразом источника (TR1+TR2) — не строго привязан к одному source_quote
- relation_to_subject для pin-list persons — берётся из pin-list `relation` поля, не из CA свободной классификации
- ОБЯЗАН добавить event/persona в auto_enrich (даже если confidence=low) с пометкой `was_in_pin_list: true`

Pin-list — это **продактовое решение** что обязано быть в книге; CA не имеет права отвергать pin-list элемент по strict-критериям. Strict применяется только к свободным auto_enrich (не из pin-list).
```

Также — формализовать структуру pin_list в CA input:
```json
{
  "pin_list": {
    "episodes": [
      {"episode_id": "ep_024", "title": "Огурцы из Молдавии", "markers": [...], "is_pin_list_required": true},
      ...
    ],
    "persons": [
      {"name": "Марфа", "relation": "бабушка", "is_pin_list_required": true},
      ...
    ]
  }
}
```

**2. Скрипт post-CA `validate_pin_list_in_auto_enrich(audit, pin_list) -> report`**:
- Для каждого pin-list episode/persona — проверить попадание в `auto_enrich`
- Если отсутствует → flag `pin_list_event_missing` / `pin_list_person_missing` с severity=error
- Возвращает отчёт `<run>_pin_list_compliance.json`

**3. Расщепление`validate_description_drift` (task 038)**:
- Применяется **только** к events с `was_in_pin_list != true`
- Pin-list events — skip drift check

### Какой результат ожидается

В v59 CA auto_enrich.timeline:
- ✅ event_auto про огурцы (с описанием парафраз TR2)
- ✅ event_auto про шубу→пианино (год 1962 из pin-list)
- ✅ event_auto про ложечки
- ✅ event_auto про шарлотку (если в TR)
- ✅ Все pin-list episodes из `known_episodes_karakulina.md`

В `<run>_pin_list_compliance.json`:
- `pin_list_event_missing.count`: 0
- `pin_list_person_missing.count`: 0 (для Марфы/Мани/Риммы/Зины — см. task 044b)

### Как проверить

1. **Unit-тесты** `tests/test_ca_pinlist_bypass.py`:
   - Event без `was_in_pin_list` + drift в description → flag (как в task 038)
   - Event с `was_in_pin_list: true` + drift в description → PASS (bypass)
   - Pin-list event отсутствует в auto_enrich → flag missing

2. **Integration** на v58 transcripts с pin-list:
   - Огурцы должны попасть в auto_enrich (даже если CA v1.3 их отверг)

3. **Verified-on-run** v59:
   - Открыть fact_map.timeline → grep событий из pin-list (огурцы, шуба, ложечки, шарлотка, карты, грибы, дача продана, церковь Власьево)
   - Открыть pin_list_compliance.json → 0 missing

---

## Ограничения

- [ ] CA strict для свободного auto_enrich (не pin-list) — **остаётся** (Класс 1 закрыт)
- [ ] Pin-list bypass — **только** для элементов с явным `is_pin_list_required: true`
- [ ] Universal: pin-list per subject, без Каракулиноспецифики в промпте
- [ ] Idempotent

---

## Dev Review

**Статус:** ожидает

**[TECH]** — пред-резолв: bypass = пометка `was_in_pin_list: true` в audit output. Scripted validators проверяют флаг.

**[PRODUCT]** — нет.

**Сложность:** `s` (1-3 ч)
**Риск:** `low`

---

## История

| Дата | Статус | Кто |
|---|---|---|
| 2026-05-17 | `new` | Опус |
