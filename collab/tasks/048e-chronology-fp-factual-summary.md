# Задача 048e: Chronology validator FP fix — factual summary в паспортичке и эпилоге

**Статус:** `new`
**Номер:** 048e
**Автор:** Опус
**Дата создания:** 2026-05-19
**Тип:** `cco-скрипт` (validator fix)
**Sprint:** v65 (bugfix v64)
**Связано:** task 048 / 048b / 048c / 048d (chronology validators)

---

## Контекст

В v64 финальные validators показали **5 chronology errors** (vs v62a/v63 = 1-2). Из них **4 — false positives** на legitимных factual summaries:

### FP пример 1 — ch_01 паспортичка
```
В 1946 году вышла замуж за Дмитрия Каракулина после двух недель знакомства.
Жили в Германии, Вышнем Волочке, Калинине, Венгрии.
Родились дети: Валерий в 1948 году, Татьяна в 1956 году.
```
Validator поднял 2 errors:
- «Валерий упомянут в context 1946, но birth_year=1948»
- «Татьяна упомянута в context 1946, но birth_year=1956»

**Реально:** это **factual summary** в паспортичке. Sentence «Родились дети: Валерий в 1948 году, Татьяна в 1956 году» — **сама** содержит birth years. Это **не** ошибка — это legitимное перечисление в паспартичке.

### FP пример 2 — epilogue
```
Родившись в украинском селе в 1920 году, она потеряла семью в 13 лет,
но не сломалась. Война стала для неё школой жизни — четыре года в
госпиталях, боевые награды, партийность. После войны создала семью...
```
Validator: «Валерий упомянут (через слово 'семью') в context 1920, birth_year=1948» — **false positive**, «семья» здесь generic, не named child.

**Также:** в epilogue упоминания «семья / создала семью / внуки» — это **обзор всей жизни**, не привязанные к конкретному году.

---

## Pre-sprint checklist

- [x] Stocktake актуален
- [x] Critical reading — v64 chronology_check.json прочитан, FP examples idenfitied
- [x] Universality — n/a (scripted validator fix)
- [x] Защита подключена к лечению — да, FP fix перестаёт триггерить wrong revision_hints
- [x] Прогон раздельный — bugfix existing validator
- [x] Класс — «scope too narrow в validator» (generic class — sentence-scope vs paragraph-scope vs section-scope)
- [x] Скрипт-first — да

---

## Спек

### 1. Исключить ch_01 (паспортичка) из chronology validator scope

В `validate_chronological_consistency` (и `validate_children_before_birth` task 048d) — добавить explicit skip для `ch_01`:

```python
def validate_chronological_consistency(book, fact_map, config=None):
    issues = []
    SKIP_CHAPTERS = (config or {}).get("skip_chapters", ["ch_01"])
    for ch in book.get("chapters", []):
        if ch.get("id") in SKIP_CHAPTERS:
            continue  # паспортичка содержит legitimate factual summaries with multiple years
        ...
```

**Причина:** ch_01 = паспортичка, в ней legitимно перечисляются key dates (рождение, свадьба, дети, награды) — это **по дизайну**. Chronology errors здесь не дают полезного сигнала.

### 2. Skip epilogue для child-mention checks (но не для grandchild)

В эпилоге обычно sentences типа «после войны создала семью / дождалась внуков / тридцать лет в медицине» — это **summary всей жизни**. Year mentioned (1920, 1933 — birth/childhood) ≠ event year где упоминаются children.

Опция (выбор):
- **A) Skip epilogue целиком** — все chronology errors → suppress в epilogue
- **B) Skip только child references в epilogue, оставить grandchild check** — grandchild_before_inferred_birth остаётся
- **C) Paragraph-scope** — если sentence упоминает «семью / дети / внуки» в paragraph про «всю жизнь» (multiple years), не sentence про конкретный event — skip

**Рекомендация: B.** Epilogue child references = generic «создала семью» — это legitimate summary. Grandchild specific dates («в 1973 встречала Дашу») — реально могут быть hallucination, оставить detect.

### 3. Sentence vs paragraph scope для chronology check

Текущая логика: ищет year в sentence, проверяет children в same sentence. Это слишком narrow:
- «Родились дети: Валерий в 1948 году, Татьяна в 1956 году» — sentence содержит **3 years** (1948, 1956 + если рядом event year). Validator берёт **первый** year, проверяет с child birth — false positive если другой year ≠ child birth.

Fix: **multi-year aware** — если sentence содержит ≥2 years и один из них = child.birth_year — assume sentence сама объявляет birth, не error.

```python
def is_birth_declaration_sentence(sentence, child_birth_year):
    """Sentence объявляет birth ребёнка (год в same sentence)?"""
    years_in_sentence = re.findall(r'\b(19|20)\d{2}\b', sentence)
    if str(child_birth_year) in [y[0] + y[1:] for y in years_in_sentence] or any(int(y[0]+y[1:]) == child_birth_year for y in years_in_sentence):
        return True
    return False

def child_mentioned_outside_birth_context(sentence, child_name, child_birth_year, event_year):
    # Skip if sentence себя декларирует birth (factual summary case)
    if is_birth_declaration_sentence(sentence, child_birth_year):
        return False
    # Existing logic
    return event_year < child_birth_year
```

### 4. Конфиг

`chronology_check_config.json` (новый, generic per subject):
```json
{
  "skip_chapters": ["ch_01"],
  "epilogue_skip_child_refs": true,
  "epilogue_keep_grandchild_specific_dates": true,
  "sentence_birth_self_declaration_skip": true
}
```

### 5. Тесты

`tests/test_chronology_fp_fix.py`:

```python
def test_birth_declaration_self_skip():
    """v64 FP: 'Родились дети: Валерий в 1948 году, Татьяна в 1956 году' — НЕ flag."""
    sentence = "Родились дети: Валерий в 1948 году, Татьяна в 1956 году."
    # Валерий упомянут, его birth=1948 — но в sentence явно 1948, это birth declaration
    assert not check_child_mentioned_before_birth(
        sentence, child_name="Валерий", child_birth_year=1948, event_year=1946,
    )

def test_ch_01_paspart_skip():
    """ch_01 паспортичка skipped по config."""
    book = {"chapters": [{"id": "ch_01", "content": "Родились дети: Валерий 1948, Татьяна 1956."}]}
    result = validate_chronological_consistency(book, fact_map={})
    assert result["errors_count"] == 0

def test_epilogue_generic_family_skip():
    """v64 FP: 'после войны создала семью' в epilogue — НЕ flag."""
    sentence = "После войны создала семью."
    # Generic «семью» — НЕ named child
    assert not check_named_child_before_birth(sentence, named_children=["Валерий", "Татьяна"], event_year=1946)

def test_real_chronology_error_still_caught():
    """v62a-style real error: 'В 1973 году встречала внучку Дашу' — flagged."""
    sentence = "В 1973 году дочь Татьяна попросила Валентину встречать внучку Дашу после школы."
    # Даша inferred min_birth ~1977+ (после свадьбы Татьяны 1977)
    assert check_grandchild_before_inferred_birth(sentence, grandchild_name="Даша", inferred_min_birth=1977, event_year=1973)
```

---

## Universality check

- [x] Промпт — n/a
- [x] Subject-specific — n/a (skip_chapters generic config)
- [x] Algorithm generic — birth declaration self-detection, epilogue generic family skip
- [x] Subject-replacement — works для любого subject ✅

---

## Ограничения

- [ ] ch_01 паспортичка skipped полностью для chronology
- [ ] Epilogue child references skipped (generic «семья», «дети» plural)
- [ ] Epilogue grandchild specific dates остаются (real hallucination risk)
- [ ] Birth declaration self-skip — multi-year sentence где child birth_year присутствует
- [ ] Snapshot tests для FP cases v64 + reproduction real errors v59 («Даша 1973»)
- [ ] Idempotent

---

## Dev Review

**Статус:** ожидает

**[TECH]** — pre-answer от Опуса:
- Extension `validate_chronological_consistency` + `validate_children_before_birth` (task 048d)
- Config `chronology_check_config.json` (generic, не subject-specific)
- Snapshot tests на FP examples v64 + не сломать v59 real example

**[PRODUCT]** — нет

**Сложность:** `xs` (<1 ч + tests)
**Риск:** `low` (FP fix не trog real error detection)

---

## Verified-on-run v65

**Cursor:** [после v65]
**Опус:** независимо проверит `chronology_check.json` — errors_count = 0 либо только real (не FP), epilogue/ch_01 не в issues.

---

## История

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-19 | `new` | Опус |
