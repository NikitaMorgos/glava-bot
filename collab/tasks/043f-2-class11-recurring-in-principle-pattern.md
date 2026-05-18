# Задача 043f-2: Class 11 recurring — pattern «не любил X в принципе, особенно по Y»

**Статус:** `new`
**Номер:** 043f-2
**Автор:** Опус (роль архитектор+продакт)
**Дата создания:** 2026-05-18
**Тип:** конфиг + snapshot test (mandatory)
**Sprint:** v64
**Связано:** task 043 (GW ЗАПРЕТ 14 v2.19), task 043f (snapshot pattern v63); Class 11 recurring 5 sprints (v59→v60→v61→v62a→v63 в новых формах)

---

## Контекст

Class 11 (awkward formulation — частное перечисление вместо обобщения) **recurring 5 sprints**:

| Sprint | Form | Pattern в config |
|--------|------|-------------------|
| v59 | «не любил советов по электричеству или поездкам» | task 043 GW ЗАПРЕТ 14 |
| v60 | similar | (continued GW prompt) |
| v61 | «не любил советов, особенно по электричеству и поездкам» | (closed v62a via 043f pattern) |
| v62a | «не любил советов, особенно по электричеству и поездкам» | task 043f pattern «не любил X по Y и Z» |
| **v63** | «не любил советов **в принципе, особенно по практическим вопросам — будь то электричество или распорядок поездок**» | **pattern эволюционировал** — длиннее, обходит regex |

**Niki feedback v63 (точная цитата):**
> «про советы владимира - Владимир не любил советов в принципе, особенно по практическим вопросам — будь то электричество или распорядок поездок - избыточно упоминать, что советы именно по электричеству он не любил»

**Класс:** **формулировка через перечисление частных категорий**, обобщение слабое или отсутствует. Pattern v63 длиннее (10+ слов вместо 5-6), но семантика та же.

**Lesson stocktake:** этот класс закрывается **архитектурно** через revision loop (task 049e), pattern в validator = backup для detection. Pattern v64 расширит coverage.

---

## Universality check

- [x] Промпт — n/a (config patterns)
- [x] Subject-specific — n/a (generic patterns)
- [x] Алгоритм generic — regex lemmatize-aware
- [x] Subject-replacement test — для любого subject «не любил X в принципе, особенно по Y» поймёт ✅

**Trap warning:** конкретные «электричество и поездки» — это симптомы класса. Класс = «не любил X (в принципе)? (особенно)? по Y (и|или|—) Z». Spec строится на классе.

---

## Спек

### 1. Конфиг extend `narrative_stop_phrases.json` (v5 → v6, after 043d-2 v5)

Расширить existing `class11_not_loved_x_by_y_and_z` category либо добавить новую более широкую:

```json
{
  "class11_not_loved_x_in_principle_v2": {
    "category": "class11_not_loved_x_by_y_and_z_extended",
    "pattern_options": [
      // EXISTING v63 (task 043f) — узкая форма
      "\\bне\\s+(люб\\w+|выноси\\w+|терп\\w+|перевари\\w+|перенос\\w+)\\s+(\\w+\\w+\\s*,?\\s*)?(особенно\\s+)?по\\s+(\\w+\\w*)\\s+(и|или|,)\\s+(\\w+\\w*)",

      // NEW v64 — расширенная форма «в принципе, особенно по X»
      "\\bне\\s+(люб\\w+|выноси\\w+|терп\\w+|перевари\\w+|перенос\\w+)\\s+(\\w+\\w+\\s+)?(в\\s+принципе|вообще|никогда)\\s*,?\\s*(\\(?особенно\\)?\\s+по\\s+\\w+\\w*)",

      // NEW v64 — форма «будь то X или Y»
      "\\bне\\s+(люб\\w+|выноси\\w+|терп\\w+|перевари\\w+|перенос\\w+)\\s+[^.]{0,80}\\s+(будь\\s+то)\\s+\\w+\\s+(и|или|,|\\u2014|\\u2013|-)\\s+\\w+",

      // NEW v64 — форма «по практическим вопросам — будь то X или Y» (general → specific cascade)
      "(по\\s+практическ\\w+\\s+вопрос\\w+|по\\s+житейск\\w+\\s+тем\\w+|по\\s+бытов\\w+\\s+\\w+)\\s*[\\u2014\\u2013\\-]\\s*будь\\s+то"
    ],
    "scope": ["ch_02", "ch_03", "ch_04"],
    "severity": "error",
    "suggestion": "Переписать обобщённо: «не любил советов» / «не любил [X]», без перечисления частных категорий. Если контекст требует — выбрать ОДНУ конкретную деталь, не cascade general→specific.",
    "reason": "Class 11 awkward formulation recurring — частное перечисление через 'в принципе, особенно по' / 'будь то X или Y' / 'по практическим вопросам — будь то'"
  }
}
```

**Note:** `pattern_options` — array; validator проверяет каждый pattern, любой match → flag. Это позволяет покрыть **3 семантически близкие формы**, не одну universal regex.

### 2. Validator function

`validate_narrative_stop_phrases` уже обрабатывает categories с `pattern` field. Расширить на `pattern_options` (array):

```python
def _check_pattern_options(sentence, category):
    """Match any of pattern_options (либо single pattern, либо list)."""
    if "pattern" in category:
        patterns = [category["pattern"]]
    elif "pattern_options" in category:
        patterns = category["pattern_options"]
    else:
        return False
    for pat in patterns:
        if re.search(pat, sentence, re.IGNORECASE):
            return True
    return False
```

### 3. Snapshot tests (mandatory, lesson v62a)

`tests/test_class11_recurring_patterns.py` (extend existing):

```python
def test_class11_v63_in_principle_especially():
    """v63 snapshot — pattern эволюция 'в принципе, особенно по'."""
    sentence = (
        "Владимир не любил советов в принципе, особенно по практическим "
        "вопросам — будь то электричество или распорядок поездок."
    )
    flags = validate_narrative_stop_phrases_for_sentence(sentence)
    assert any(
        f["category"] == "class11_not_loved_x_by_y_and_z_extended"
        for f in flags
    )


def test_class11_v62a_simple_form_still_caught():
    """v62a форма — должна оставаться в coverage."""
    sentence = "Владимир не любил советов, особенно по электричеству и поездкам."
    flags = validate_narrative_stop_phrases_for_sentence(sentence)
    assert any(f["category"].startswith("class11_not_loved") for f in flags)


def test_class11_v63_budtto_form():
    """v63 forms with 'будь то X или Y'."""
    sentence = (
        "Не любил он лишних вопросов — будь то политика или бытовые мелочи."
    )
    flags = validate_narrative_stop_phrases_for_sentence(sentence)
    assert any(f["category"].startswith("class11_not_loved") for f in flags)


def test_class11_negative_single_object():
    """Сингулярный объект без enumeration — НЕ flag."""
    sentence = "Владимир не любил советов от тёщи."
    flags = validate_narrative_stop_phrases_for_sentence(sentence)
    assert not any(f["category"].startswith("class11_not_loved") for f in flags)


def test_class11_negative_legitimate_listing():
    """Простое перечисление без 'не любил' framing — НЕ flag."""
    sentence = "Дома стояли по обеим сторонам улицы: справа кирпичные, слева деревянные."
    flags = validate_narrative_stop_phrases_for_sentence(sentence)
    assert not any(f["category"].startswith("class11_not_loved") for f in flags)
```

### 4. Integration в orchestrator (049f)

Existing `narrative_stop_phrases` validator → revision_hints orchestrator. Suggestion:
- «Переписать обобщённо без перечисления частных категорий»

GW v2.23 ПРАВИЛО 13 переписывает: «Владимир не любил советов в принципе, особенно по практическим вопросам — будь то электричество или распорядок поездок» → «Владимир не любил советов».

---

## Risk и mitigation

**Risk A: Pattern v64 продолжит эволюционировать.**

**Mitigation:**
- 3 pattern_options покрывают v59-v63 forms
- **Архитектурно** закрывается revision loop (049e): любая форма flagged → GW переписывает
- Pattern в validator = детектор для revision pass

**Risk B: False positives на legitimate factual statements with enumeration.**

**Mitigation:**
- Pattern требует «не люб/выноси/терп» prefix — narrow
- Snapshot tests negative cases
- Severity error → GW обязан apply, но suggestion позволяет переписать (keep semantic, drop listing)

**Risk C: Multi-pattern может match overlapping → дублирующие hints.**

**Mitigation:**
- В `_check_pattern_options` — match any (returns True) — single flag per sentence per category
- Multi-category match (e.g. также Class 17) — OK, разные categories отдельные hints

---

## Ограничения

- [ ] Generic patterns
- [ ] Lemma-aware
- [ ] Idempotent
- [ ] Severity error
- [ ] Snapshot tests mandatory: 3+ positive forms + 2 negative
- [ ] Scope narrative chapters

---

## Dev Review

**Статус:** ожидает

**[TECH]** — pre-answer от Опуса:
- `narrative_stop_phrases.json: v5 → v6` (Class 11 extended)
- Validator extension: support `pattern_options` (array) — backward compatible с `pattern` (single)
- Калибровка на v63 артефакте обязательна
- Multi-pattern может match same sentence несколько раз — collapsed to single flag per category

**[PRODUCT]** — нет

**Сложность:** `xs` (<1 ч — config + validator extension + 5 snapshot tests)
**Риск:** `low`

---

## Verified-on-run v64

**Cursor:** [после v64]
**Опус:** независимо проверит:
- ✅ v63 example «не любил советов в принципе, особенно по практическим вопросам — будь то электричество или распорядок поездок» — flagged
- ✅ Snapshot tests PASS (5+)
- ✅ В v64 narrative pattern удалён / переписан (после revision pass)

---

## История

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-18 | `new` | Опус |
