# Задача 038c: CA pin-list event strict description — source location preservation (огурцы «из Молдавии», не «из командировок»)

**Статус:** `new`
**Номер:** 038c
**Автор:** Опус (роль архитектор+продакт)
**Дата создания:** 2026-05-18
**Тип:** `промпт` CA (минор) + конфиг
**Sprint:** v63
**Связано:** task 038 (CA v1.3 strict description); task 038b (CA v1.4 pin-list bypass); Class 1 confabulation; recurring огурцы v56 / v60 / v62a — last instance «привозит подарки из командировок»

---

## Контекст

В v62a ch_04 (line 352):

> «Этот эпизод произошёл после того, как Валентина критиковала Владимира за то, что он **не привозит подарки из командировок**.»

Должно быть **«из Молдавии»** (конкретное место в pin-list ep_024 source_quote), не generic «командировок». GW generalised конкретный source location в abstract abstract reason.

**Recurrence history Class 1 на огурцах:**
- v56: «потому что не привозит достаточно подарков» (confabulation причина)
- v60: похожая generalisation
- v62a: «не привозит подарки из командировок» — generalisation «Молдавия» → «командировки»

**Корень:** CA pin-list event description **сохраняет factual content** (что произошло), но **теряет конкретные location/quote markers** из source. GW потом использует description as input и generalises ещё дальше.

**Класс:** Class 1 (CA description drift / GW confabulation) — конкретно **source location preservation**.

---

## Universality check

- [x] Промпт — CA минор prompt patch (1 правило по Правилу 6)
- [x] Subject-specific — n/a (правило generic для CA по любому subject)
- [x] Алгоритм generic — preserve named entities (locations, persons, dates) из source_quote в description
- [x] Subject-replacement test — для Корольковой «привезла платье из Парижа» в pin-list → CA description preserves «из Парижа», GW не generalises ✅

**Trap warning:** конкретно «Молдавия» — это симптом. Класс = «pin-list event source_quote содержит location/named-entity → CA description обязана preserve, не generalise».

---

## Спек

### Что нужно изменить

### 1. CA prompt patch — v1.4 → v1.5 (minor)

Добавить ПРАВИЛО 7 в CA prompt (per Правило 6 архитектора — 1 правило per bump):

```
ПРАВИЛО 7 — NAMED ENTITY PRESERVATION В DESCRIPTION (v1.5)

При формировании auto_event.description для pin-list event:
- Если source_quote содержит **конкретное место** (топоним: страна, город, регион) →
  description ОБЯЗАН содержать тот же топоним (без замены на abstract category)
- Если source_quote содержит **конкретное имя** (person name) →
  description ОБЯЗАН содержать имя (без замены на «военнослужащий», «знакомый» и т.п.)
- Если source_quote содержит **конкретный год** →
  description ОБЯЗАН содержать год
- Если source_quote содержит **characteristic word** рассказчика (необычное слово,
  диалект, авторская формулировка) → description СТАРАЕТСЯ его сохранить
  (не заменять литературным синонимом)

❌ ПЛОХО (location generalised на абстрактную категорию):
  source_quote: «привёз чемодан [продукта] из [конкретная_страна]»
  description: «привёз чемодан [продукта] из командировок»
  ← потеряна география; «командировки» — generic, абстрактнее источника

✅ ХОРОШО (location preserved дословно):
  source_quote: «привёз чемодан [продукта] из [конкретная_страна]»
  description: «привёз чемодан [продукта] из [конкретная_страна]»

❌ ПЛОХО (name + characteristic word потеряны):
  source_quote: «помог [роль_контекста] [имя_близкого] — [characteristic_word]
                 её через [место]»
  description: «помог [generic_роль] преодолеть бюрократию»
  ← потеряны имя, characteristic word, конкретное место

✅ ХОРОШО (entities preserved):
  source_quote: «помог [роль_контекста] [имя_близкого] — [characteristic_word]
                 её через [место]»
  description: «помог [роль_контекста] [имя_близкого] — [characteristic_word]
                её через [место]»

Правило применяется ТОЛЬКО к auto_events для known pin-list episodes
(где episode_id matched). На обычные fact_extraction events — не распространяется.
```

**Примечание к промпту (Курсору):** в финальный текст ПРАВИЛА 7 для CA prompt
вставляются **placeholders** (`[конкретная_страна]`, `[имя_близкого]`,
`[characteristic_word]`), **не** конкретные слова текущего subject.
Subject-replacement test построчно — пройден.

### 2. Scripted post-CA validator (defense in depth)

В `pipeline_utils.py` — `validate_pin_list_event_location_preservation(fact_map, pin_list)`:

Для каждого auto_event matched к pin-list episode:
- Парсить source_quote на **locations** через простой regex + capitalized words check (или через fact_map.locations references)
- Если location в source_quote НЕ в description → flag `location_lost_in_description` warning

Output: `<run>_ca_location_preservation_check.json`

### 3. Test

**`tests/test_ca_named_entity_preservation.py`** — snapshot tests:

```python
def test_ogurtsy_moldova_v62a():
    """v62a огурцы — source_quote 'из Молдавии' must be in description."""
    source_quote = "папаша привёз чемодан огурцов в заграничном чемодане из Молдавии"
    description_v62a = "привёз чемодан огурцов из командировок"  # current bad
    description_fixed = "привёз чемодан огурцов из Молдавии"  # expected

    flags_bad = validate_pin_list_event_location_preservation_for_event(
        source_quote=source_quote, description=description_v62a)
    assert any(f["type"] == "location_lost_in_description" for f in flags_bad)
    assert "Молдавия" in str(flags_bad[0]["lost_locations"])

    flags_good = validate_pin_list_event_location_preservation_for_event(
        source_quote=source_quote, description=description_fixed)
    assert not flags_good


def test_negative_no_location_in_source():
    """Если в source нет location — нечего терять."""
    source_quote = "она была доброй и заботливой"
    description = "характеризовалась добротой"
    flags = validate_pin_list_event_location_preservation_for_event(
        source_quote=source_quote, description=description)
    assert not flags
```

### Какой результат ожидается

В v63:
- CA prompt v1.5 с ПРАВИЛО 7 — fact_map.auto_events для ep_024 description содержит «из Молдавии»
- GW narrative ch_04 огурцы — «привёз из Молдавии» (factual)
- `ca_location_preservation_check.json` — нет ошибок для ep_024 (либо warning если description всё-таки generalised)

### Как проверить

1. **Unit-тесты** (см. выше) PASS
2. **Integration** на v62a CA output:
   - Загрузить v62a `fact_map_full` → auto_events для ep_024 → check description
   - Snapshot pre-fix → flag «Молдавия» lost
   - После CA v1.5 → описание сохраняет «Молдавия»
3. **Verified-on-run** v63:
   - Открыть `karakulina_v63_text_FULL.md` ch_04 огурцы — «из Молдавии» в narrative (не «из командировок»)
   - `karakulina_v63_fact_map.json` auto_event for ep_024 description contains «Молдави» substring

---

## Ограничения

- [ ] **Minor prompt patch** — 1 правило (Правило 6 архитектора)
- [ ] **Scripted defense** добавляется параллельно — defense in depth
- [ ] **Generic** mechanism — не subject-specific
- [ ] **Применяется только к auto_events** для known pin-list episodes (не к обычным fact_extraction events)
- [ ] **CA prompt v1.5** — одно правило (ПРАВИЛО 7), не bundle с другим

---

## Dev Review

**Статус:** ожидает

**[TECH]** — pre-answer от Опуса:
- Location detection в source_quote: simplest path — известные locations из `fact_map.locations` cross-reference + capitalised entities в quote
- CA prompt v1.5 — увеличение размера CA prompt на ~15-20 строк (1 правило + examples). Если CA prompt уже близок к limit'у — flag в Dev Review
- Validator severity = warning (CA prompt — primary defense; script — backup)

**[PRODUCT]** — нет (огурцы Молдавия — pin-list факт, не product decision)

**Сложность:** `xs` (<1 ч CA prompt) + `xs` (validator) = `xs`-`s`
**Риск:** `low` (1 prompt rule + scripted validator, оба defense in depth)

---

## Verified-on-run

**Cursor:** [после v63]
**Опус:** независимо откроет fact_map.json для ep_024 description + ch_04 narrative

---

## История

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-18 | `new` | Опус |
