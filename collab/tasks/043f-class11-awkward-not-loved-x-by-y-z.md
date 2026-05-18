# Задача 043f: Class 11 awkward — pattern «не любил X (особенно)? по Y и Z» (повторение v59/v60/v61/v62a)

**Статус:** `new`
**Номер:** 043f
**Автор:** Опус (роль архитектор+продакт)
**Дата создания:** 2026-05-18
**Тип:** конфиг + минор скрипт
**Sprint:** v63
**Связано:** task 043 (Class 11 awkward formulation, ЗАПРЕТ 14 in GW v2.19); task 043b (lemmatize stop-phrases); recurring pattern v59 → v60 → v61 → v62a; **lesson v62a: recurring patterns без unit-test'а возвращаются**

---

## Контекст

В v62a ch_02 (line 229) обнаружена **очередная** instance того же класса:

```
Отношения Валентины с зятем не сложились — Владимир не любил советов,
особенно по электричеству и поездкам.
```

Pattern: «**не любил X (особенно)? по Y и Z**» — formulation listing (Class 11).

**Recurrence history:**
- v59: «не любил советов по электричеству или поездкам»
- v60: похожий pattern (точная строка не зафиксирована — см. v60 verified)
- v61: «не любил советов, особенно по электричеству и поездкам» (близко к v62a)
- v62a: same — pattern survived через `\bне\s+любил\s+\w+\s+по\s+\w+\s+(или|и)\s+\w+` шаблон

**Корень:** task 043 GW ЗАПРЕТ 14 (X-по-Y listing) — **prompt-level only**, без scripted validation. GW periodically «забывает» правило. **Recurring patterns без unit-test'а возвращаются** (lesson v62a).

**Класс:** Class 11 (awkward formulation, прямое перечисление вместо обобщения с примерами).

**Архитектурное решение:** добавить **scripted validator** для recurring pattern + unit-test с конкретным example из v62a.

---

## Universality check

- [x] Промпт — n/a, scripted
- [x] Subject-specific — n/a, pattern generic
- [x] Алгоритм generic — regex lemmatize-aware, поймает analogous patterns у любого subject
- [x] Subject-replacement test — для Корольковой «не любил подарков, особенно по дням рождения и Новому году» — flag ✅

**Trap warning:** конкретные «электричество и поездки» — это симптом. Класс = «не любил X (особенно)? по Y и Z/W» с perepiseanием частных категорий. Spec строится на классе.

---

## Спек

### Что нужно изменить

### 1. Конфиг extend `narrative_stop_phrases.json`

Добавить categorical pattern + lemmatize-aware:

```json
{
  "category": "class11_not_loved_x_by_y_and_z",
  "pattern": "\\bне\\s+(люб\\w+|выноси\\w+|терпе\\w+|перевари\\w+)\\s+(\\w+\\w+\\s*,?\\s*)?(особенно\\s+)?по\\s+(\\w+\\w*)\\s+(и|или|,)\\s+(\\w+\\w*)",
  "scope": ["ch_02", "ch_03", "ch_04"],
  "severity": "error",
  "reason": "Class 11 awkward formulation — частное перечисление вместо обобщения; GW prompt v2.19 ЗАПРЕТ 14 регулярно не выполняется"
}
```

**Lemma-friendly variants** для extended match:
- «не любил/любила/любили/любил» — `\\bне\\s+люб\\w+`
- alternates: «не выносил», «не терпел», «не переваривал»
- «по + N+N» — listing of categories

### 2. Минор скрипт — `enforce_class11_awkward`

В `pipeline_utils.py` (опционально, only if Никита okays auto-rewrite):

- Найти `class11_not_loved_x_by_y_and_z` match → flag warning
- **Не enforce delete** (риск потери конкретного fact) — только flag для GW revision pass или human review
- Действие при error severity:
  - В `style_checks.json` записать `requires_rewrite: true` с suggestion: «Переписать обобщённо: «не любил советов» (без перечисления категорий)»

### 3. Unit-test со снимком v62a

**`tests/test_class11_recurring_pattern.py`** (новый) — обязательный pytest со **снимком конкретного example**:

```python
def test_class11_v62a_example():
    """Recurring Class 11 from v62a — must be flagged."""
    paragraph = (
        "Отношения Валентины с зятем не сложились — Владимир не любил советов, "
        "особенно по электричеству и поездкам."
    )
    flags = validate_narrative_stop_phrases(paragraph, scope="ch_02")
    assert any(f["category"] == "class11_not_loved_x_by_y_and_z" for f in flags)
    assert flags[0]["severity"] == "error"


def test_class11_v61_example():
    """Recurring Class 11 from v61 — same class, slightly different surface."""
    paragraph = "Владимир не любил советов по электричеству или поездкам."
    flags = validate_narrative_stop_phrases(paragraph, scope="ch_02")
    assert any(f["category"] == "class11_not_loved_x_by_y_and_z" for f in flags)


def test_class11_negative_no_listing():
    """Generic sentence without listing should NOT flag."""
    paragraph = "Владимир не любил советов от тещи."  # single object, no listing
    flags = validate_narrative_stop_phrases(paragraph, scope="ch_02")
    assert not any(f["category"] == "class11_not_loved_x_by_y_and_z" for f in flags)
```

**Дисциплина:** при каждом будущем recurrence — добавлять новый snapshot test (как minimal failing case). Если pattern эволюционировал и тест не ловит — fix pattern, не тест.

### Какой результат ожидается

В v63:
- `style_checks.json` error для line 229 «Владимир не любил советов, особенно по электричеству и поездкам»
- GW при revision pass перепишет: «Отношения с зятем не сложились — Владимир не любил советов.» (короче, без перечисления)
- Все 3 unit-test'а PASS

### Как проверить

1. **Unit-тесты** (см. выше) — обязательны
2. **Integration** на v62a text line 229 → flag error
3. **Verified-on-run** v63:
   - `style_checks.json` содержит `class11_not_loved_x_by_y_and_z` flag (если pattern всё ещё в тексте — что было бы регрессией pattern detection)
   - **ИЛИ** narrative переписан и pattern отсутствует (PASS)

---

## Ограничения

- [ ] **Generic patterns**, без subject-конкретики
- [ ] **Не enforce auto-rewrite** — только flag (риск потери fact)
- [ ] **Idempotent** validator
- [ ] **Unit-test mandatory** — каждый recurring pattern имеет snapshot test
- [ ] Lemmatize-aware

---

## Dev Review

**Статус:** ожидает

**[TECH]** — pre-answer от Опуса:
- Pattern complexity: `\\bне\\s+(люб|выноси|терп|перевари)\\w+\\s+...\\s+по\\s+\\w+\\s+(и|или|,)\\s+\\w+` — calibrate на v62a после прогона, may need iteration
- Pattern может дать false positive если «по» legitimate preposition (e.g. «не любил гулять по парку и лесу» — это normal usage, не пафос). Mitigation: require **abstract noun** в первой позиции (`совет\w+`, `подарок\w+`, etc.) — добавить explicit list абстрактных существительных в pattern OR оставить regex permissive + manual review false positives
- Альтернатива — keep pattern wide, severity=warning instead of error; calibrate later

**[PRODUCT]** — нет

**Сложность:** `xs` (<1 ч)
**Риск:** `low` (warning/error flag-only)

---

## Verified-on-run

**Cursor:** [после v63]
**Опус:** независимо проверит — `style_checks.json` или narrative переписан

---

## История

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-18 | `new` | Опус |
