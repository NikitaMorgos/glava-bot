# Задача 048f: Class 12 extend — потомки X упомянуты в контексте раннего возраста X (Толя/Коля/Витя в детстве Валентины)

**Статус:** `new`
**Номер:** 048f
**Автор:** Опус
**Дата создания:** 2026-05-19
**Тип:** `cco-скрипт` (chronology validator extend)
**Sprint:** v65
**Связано:** task 048/048b/048c/048d (Class 12 chronology); Никитин feedback v64 — потомки Полины упомянуты в narrative про детство Валентины (1933+)

---

## Контекст

В v64 narrative ch_02 про ранние годы Валентины (1933, голод, детдом, спасение Полиной):

> «У тёти Поли была фамилия Амельченко — по мужу, и трое сыновей: Толя из Белгорода, Коля-лётчик и Витя из Энгельса. С Толей Валентина особенно дружила.»

**Проблема:** Полина — старшая сестра Валентины (родилась ~1908-1912, забрала 13-летнюю Валентину из детдома в 1933). У Полины в 1933 — **ещё нет** троих сыновей (она сама молодая женщина 21-25 лет, могла иметь 0-1 ребёнка максимум).

Толя, Коля, Витя родились **позже** (где-то 1935-1950+). «Толя из Белгорода» — Никитин внук-возраст знакомства = далеко не 1933. «Коля-лётчик» — лётчик профессия ≈1950+.

Это **Class 12 в новой форме** — «потомки X (или родственники сложного родства) упомянуты в контексте раннего возраста X». Существующий валидатор (task 048b/048d) проверяет только:
- Дети субъекта (relation=сын/дочь) с known birth_year
- Внуки субъекта (через parent.birth_year/marriage_year)

**Не покрывает:** «потомки старшего родственника» — племянники субъекта (relation=племянник, parent=Полина старшая сестра).

---

## Pre-sprint checklist

- [x] Stocktake актуален
- [x] Critical reading — v64 narrative прочитан, FP example identified Никитой
- [x] Universality — n/a (scripted, generic relative chronology)
- [x] Защита подключена — да, hint в revision pass
- [x] Прогон раздельный — combined в v65 bugfix sprint OK
- [x] Класс — Class 12 extend (generic «descendants in early ancestor context»)
- [x] Скрипт-first — да

---

## Спек

### 1. Generic algorithm

В `validate_chronological_consistency` (либо `validate_children_before_birth` extend):

**Новая проверка `descendants_in_ancestor_early_context`:**

Для каждого person в `fact_map.persons` с relation типа «племянник / племянница / внук / внучка / внучатый племянник / правнук»:
1. Найти `parent_link` (если в fact_map persons есть relation field) либо inferred через имя/контекст
2. Если parent unknown → skip (нельзя проверить)
3. Если у person есть профессия/контекст указывающий на возраст («лётчик» = ≥18 лет, «школьник» = 7-17, «из Белгорода» = взрослый):
   - `inferred_descendant_min_birth = parent.birth_year + 18` (если parent не married в young age — adjustable)
4. Если в narrative paragraph упоминается subject's event year ≤ inferred_descendant_min_birth - 5 (т.е. context > 5 лет до ожидаемого descendant birth):
   - **Flag warning** `descendant_mentioned_in_ancestor_early_context`

### 2. Реализация — параметризовано через config

```python
def validate_descendants_in_early_context(book, fact_map, config=None):
    """Class 12 extend — потомки upомянуты в context когда они ещё не родились
    либо слишком молоды относительно их предков.

    Generic algorithm:
    1. Identify descendants (relation contains 'племянник|внук|правнук|внучатый')
    2. Infer descendant min_birth_year through parent chain
    3. If narrative paragraph mentions subject event year < descendant min_birth_year:
       flag as Class 12 extension

    Config:
    - relation_descendant_patterns: список relation типов (default стандартный)
    - default_age_adjustment: int (default 18)
    """
    config = config or {}
    DESCENDANT_RELATIONS = config.get("descendant_relations", [
        "племянник", "племянница", "внук", "внучка",
        "внучатый племянник", "правнук", "правнучка"
    ])
    issues = []
    persons = fact_map.get("persons", [])
    descendants = [p for p in persons if any(r in (p.get("relation_to_subject") or "").lower() for r in DESCENDANT_RELATIONS)]

    for ch in book.get("chapters", []):
        if ch.get("id") in ("ch_01", "epilogue"):
            continue  # ch_01 — паспортичка, epilogue — общий обзор
        content = ch.get("content", "") or ""
        for paragraph in content.split("\n\n"):
            years = [int(y) for y in re.findall(r'\b(19|20)\d{2}\b', paragraph) if 1900 <= int(y) <= 2030]
            if not years:
                continue
            min_year_in_para = min(years)
            for desc in descendants:
                name_lower = desc.get("name", "").lower()
                if name_lower and name_lower in paragraph.lower():
                    inferred_min = _infer_descendant_min_birth(desc, fact_map, config)
                    if inferred_min and min_year_in_para < inferred_min:
                        issues.append({
                            "type": "descendant_in_ancestor_early_context",
                            "category": "class12_extend",
                            "chapter_id": ch["id"],
                            "person_name": desc.get("name"),
                            "inferred_min_birth": inferred_min,
                            "event_year_in_paragraph": min_year_in_para,
                            "snippet": paragraph[:200],
                            "severity": "warning",
                            "suggestion": (
                                f"Удалить упоминание [{desc.get('name')}] в paragraph про "
                                f"{min_year_in_para} год — этот родственник родился ≥{inferred_min}. "
                                f"Альтернатива: переписать через generic 'старшая сестра' / "
                                f"'её родственники' без named descendants."
                            ),
                            "reason": "Class 12 extend — потомок упомянут в context раннего возраста предка"
                        })
                        break  # одно flag per paragraph per person
    return {
        "issues": issues,
        "errors_count": 0,
        "warnings_count": len(issues),
    }


def _infer_descendant_min_birth(descendant, fact_map, config):
    """Inferred min birth year потомка через parent chain.

    Heuristics:
    - profession 'лётчик' / 'военный' → min adult 18-25
    - context 'школьник' → min 7-17
    - parent.birth_year known → parent + 18 (default config.default_age_adjustment)
    - parent.marriage_year known → marriage + 1
    - chained: parent → grandparent → etc.
    """
    age_adj = config.get("default_age_adjustment", 18)

    # Простейшее — through parent chain
    parent_link = descendant.get("parent") or _find_parent_via_relation_pattern(descendant, fact_map)
    if parent_link:
        parent = next((p for p in fact_map.get("persons", []) if p.get("name") == parent_link), None)
        if parent:
            if parent.get("marriage_year"):
                return int(parent["marriage_year"]) + 1
            if parent.get("birth_year"):
                return int(parent["birth_year"]) + age_adj
    # Если профессия указывает на adult — fallback
    prof = (descendant.get("profession") or "").lower()
    if any(p in prof for p in ["лётчик", "военный", "врач", "инженер"]):
        # Adult profession — min birth = subject_birth + 30 как нестрогая оценка
        subject_birth = fact_map.get("subject", {}).get("birth_year")
        if subject_birth:
            return int(subject_birth) + 30
    return None  # cannot determine
```

### 3. Pin-list extension (опционально)

В `known_episodes_karakulina.md` v7 (task 044i) можно добавить **explicit parent links** для племянников:

```markdown
### Племянники / племянницы (для chronology validator)

| name | relation | parent (link) | known birth_year |
|------|----------|---------------|------------------|
| Толя | племянник | Полина (тётя Поля) | ~1935+ (unknown точно) |
| Коля | племянник | Полина | ~1935+ |
| Витя | племянник | Полина | ~1935+ |
| Римма | племянница | Шура (тётя Шура) | ~1940+ |
| Зина | племянница | Шура | ~1940+ |
```

Это data per subject — не код. Validator читает.

### 4. Snapshot tests

`tests/test_chronology_descendants_in_early_context.py`:

```python
def test_v64_polya_sons_in_childhood_context():
    """v64 FP: 'У тёти Поли... трое сыновей: Толя, Коля, Витя' в paragraph про 1933 голод."""
    book = {"chapters": [{"id": "ch_02", "content":
        "В 1933 году началась трагедия. Валентина потеряла мать. Тётя Поля "
        "забрала её из детдома. У тёти Поли была фамилия Амельченко — по мужу, "
        "и трое сыновей: Толя из Белгорода, Коля-лётчик и Витя из Энгельса."
    }]}
    fact_map = {
        "subject": {"birth_year": 1920},
        "persons": [
            {"name": "Полина", "relation_to_subject": "старшая сестра", "birth_year": 1908},
            {"name": "Толя", "relation_to_subject": "племянник", "parent": "Полина"},
            {"name": "Коля", "relation_to_subject": "племянник", "parent": "Полина", "profession": "лётчик"},
            {"name": "Витя", "relation_to_subject": "племянник", "parent": "Полина"},
        ]
    }
    result = validate_descendants_in_early_context(book, fact_map)
    # Полина 1908 + 18 = 1926; в paragraph упомянут 1933 — но Толя/Коля/Витя 
    # inferred 1926+, paragraph про 1933 → granularity недостаточна для error
    # НО: profession Коли = лётчик → adult, min birth subject+30 = 1950 → paragraph 1933 < 1950 → flag
    flagged_names = [i["person_name"] for i in result["issues"]]
    assert "Коля" in flagged_names  # лётчик в context 1933 — flagged


def test_negative_proper_grandchild_context():
    """Grandchild в context их фактического времени — НЕ flag."""
    book = {"chapters": [{"id": "ch_02", "content":
        "В 1985 году внук Никита учился в школе."
    }]}
    fact_map = {
        "subject": {"birth_year": 1920},
        "persons": [
            {"name": "Татьяна", "relation_to_subject": "дочь", "birth_year": 1956, "marriage_year": 1977},
            {"name": "Никита", "relation_to_subject": "внук", "parent": "Татьяна"},
        ]
    }
    result = validate_descendants_in_early_context(book, fact_map)
    # Никита inferred 1977+1=1978. Paragraph 1985 > 1978 → OK
    assert not result["issues"]
```

---

## Universality check

- [x] Промпт — n/a
- [x] Subject-specific — n/a (relation patterns generic, age adjustments config)
- [x] Algorithm generic — relation-based descendant chain
- [x] Subject-replacement — для Корольковой/Дмитриева с другими племянниками/внуками работает ✅

---

## Ограничения

- [ ] Severity = warning (heuristic-based, не strict bound)
- [ ] Skip ch_01 (паспортичка) и epilogue (overview)
- [ ] Profession-based heuristics через config (лётчик, военный, врач)
- [ ] Parent link через fact_map persons либо pin-list extension
- [ ] Snapshot tests на v64 FP example + не сломать real grandchild detection
- [ ] Idempotent

---

## Dev Review

**Статус:** ожидает

**[TECH]** — pre-answer от Опуса:
- Extension в `pipeline_utils.py` (новая функция либо часть `validate_chronological_consistency`)
- `chronology_check_config.json` extend
- Pin-list parent links — optional но повышает точность
- Severity warning, GW при revision переписывает (per ПРАВИЛО 13)

**[PRODUCT]** — нет (Никитин feedback v64)

**Сложность:** `s` (1-3 ч)
**Риск:** `low` (warning level, новая generic функция)

---

## Verified-on-run v65

**Cursor:** [после v65]
**Опус:** независимо проверит:
- `chronology_check.json` содержит flag для «Толя/Коля/Витя в context 1933»
- Snapshot tests PASS
- Не сломаны существующие checks (Даша 1973 v59 example, Германия 1946-48 v62a example)

---

## История

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-19 | `new` | Опус |
