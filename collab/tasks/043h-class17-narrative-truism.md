# Задача 043h: Class 17 NEW — narrative truism / констатация очевидного (validator + patterns + snapshot tests)

**Статус:** `new`
**Номер:** 043h
**Автор:** Опус (роль архитектор+продакт)
**Дата создания:** 2026-05-18
**Тип:** конфиг + скрипт + snapshot tests (mandatory per lesson v62a)
**Sprint:** v64
**Связано:** Никитин feedback v63 — «писатель нагоняет объем знаков»; новый Class 17 не лечился раньше; stocktake 2026-05-18

---

## Контекст

**Никитин feedback v63 (точные цитаты):**

> «местами кажется, что писатель нагоняет объем знаков. это плохо. может не так жестко ставить таргет по количеству знаков или добивать его врезками историка. но не писать многословно, там где это не нужно типа - В те годы сестра, забравшая ребёнка из детдома, брала на себя огромную ответственность — продуктовые карточки, одежда, образование, всё ложилось на её плечи. - это вроде констатация очевидного»

> «избыточно: Валерий не захотел возвращаться после летних каникул в венгерский интернат и остался с тётей Шурой в городе Кирсанов Тамбовской области. Валентина приняла это решение сына спокойно. - зачем писать, что она приняла решение спокойно»

**Класс 17 — Narrative truism / констатация очевидного:**

GW добавляет sentences которые констатируют то, что и так понятно из контекста — без новой information, без характерных деталей, без голоса рассказчика. Pattern семантический, не лексический.

**Sub-categories (из v63 feedback):**

1. **Obvious responsibility constatation** — «брал на себя ответственность» + перечисление generic obligations
2. **Subjective emotional ascription** — «приняла спокойно», «отнеслась с пониманием», «переживала молча» — приписывание эмоционального состояния без подтверждения в источнике
3. **Generic mid-event commentary** — «это требовало силы и характера» / «было непросто в те годы»

**Класс vs Class 6 (epilogue пафос):** Class 6 — пафос финала («типичная для поколения»); Class 17 — затяжка в narrative («всё ложилось на её плечи»). Разные scope, разные patterns.

---

## Universality check

- [x] Промпт — n/a (config patterns + validator)
- [x] Subject-specific — n/a (generic russian narrative patterns)
- [x] Алгоритм generic — regex lemmatize-aware patterns
- [x] Subject-replacement test — для Корольковой/Дмитриева аналогичные truisms поймает без правок ✅

**Trap warning:** конкретные эпизоды (сестра-продуктовые-карточки, «приняла спокойно») — это **симптомы класса**. Класс = «truism без новой information». Spec строится на классе.

---

## Спек

### 1. Конфиг extend `narrative_stop_phrases.json` (v3 → v4)

Добавить новые categories под общим тегом `narrative_truism`:

```json
{
  "narrative_truism": {
    "categories": [
      {
        "category": "obvious_responsibility_constatation",
        "pattern": "брал\\w+\\s+на\\s+себя\\s+(огромн\\w+|больш\\w+|тяжёл\\w+|колоссальн\\w+)?\\s*(ответственност\\w+|заботу|нагрузку)",
        "scope": ["ch_02", "ch_03", "ch_04", "epilogue"],
        "severity": "warning",
        "suggestion": "delete_sentence",
        "reason": "констатация очевидного — читатель сам понимает из контекста"
      },
      {
        "category": "everything_fell_on_shoulders",
        "pattern": "(всё|вс[еёя])\\s+(ложил\\w+|легл\\w+)\\s+на\\s+(её|его|их|плечи|плечи\\s+\\w+)",
        "scope": ["ch_02", "ch_03", "ch_04", "epilogue"],
        "severity": "warning",
        "suggestion": "delete_sentence"
      },
      {
        "category": "accepted_calmly",
        "pattern": "(приня\\w+|восприня\\w+|отнесл\\w+)\\s+(это|эт\\w+|свое|его|её)?\\s*\\w+?\\s*(спокойно|молча|без\\s+слов|с\\s+пониманием|сдержанн\\w+)",
        "scope": ["ch_02", "ch_03", "ch_04"],
        "severity": "warning",
        "suggestion": "delete_sentence",
        "reason": "subjective emotional ascription без подтверждения в transcripts"
      },
      {
        "category": "required_strength_and_character",
        "pattern": "(требова\\w+|нужн\\w+|необходим\\w+)\\s+(огромн\\w+|больш\\w+|немал\\w+)?\\s*(силы|характер\\w+|мужеств\\w+|стойкости|терпени\\w+)",
        "scope": ["ch_02", "ch_03", "ch_04"],
        "severity": "warning",
        "suggestion": "delete_sentence"
      },
      {
        "category": "was_not_easy_in_those_years",
        "pattern": "(было\\s+не\\s*прост\\w+|трудн\\w+|тяжел\\w+)\\s+в\\s+(те\\s+годы|то\\s+время|эпох\\w+|период)",
        "scope": ["ch_02", "ch_03", "ch_04"],
        "severity": "warning",
        "suggestion": "delete_sentence"
      },
      {
        "category": "this_required_dedication",
        "pattern": "(это|такая|подобн\\w+)\\s+\\w*\\s*(требовал\\w+|стоил\\w+)\\s+(преданности|посвящени\\w+|жертв)",
        "scope": ["ch_02", "ch_03", "ch_04"],
        "severity": "warning",
        "suggestion": "delete_sentence"
      },
      {
        "category": "had_to_show_X",
        "pattern": "(приходил\\w+|пришл\\w+|нужн\\w+)\\s+\\w*\\s*(проявля\\w+|показыва\\w+)\\s+(\\w+\\s+)?(терпени\\w+|выдержк\\w+|изобретательност\\w+|находчивост\\w+)",
        "scope": ["ch_02", "ch_03", "ch_04"],
        "severity": "warning",
        "suggestion": "delete_sentence_or_replace_with_specific"
      }
    ]
  }
}
```

### 2. Validator function

В `pipeline_utils.py`:

```python
def validate_narrative_truism(
    book: dict,
    config: dict | None = None,
) -> dict:
    """Detect narrative truism patterns (Class 17) в narrative chapters.

    Returns:
    {
        "issues": [
            {
                "type": "narrative_truism",
                "category": "<sub-category>",
                "chapter_id": "ch_02",
                "snippet": "В те годы сестра брала на себя огромную ответственность...",
                "severity": "warning",
                "suggestion": "delete_sentence",
                "reason": "..."
            }
        ],
        "errors_count": 0,
        "warnings_count": N,
    }
    """
    config = config or _load_narrative_stop_phrases_config()
    truism_cats = config.get("narrative_truism", {}).get("categories", [])
    issues = []
    for ch in book.get("chapters", []):
        if ch.get("id") == "ch_01":
            continue
        content = ch.get("content", "") or ""
        for sentence in _split_sentences(content):
            for cat in truism_cats:
                if not re.search(cat["pattern"], sentence, re.IGNORECASE):
                    continue
                issues.append({
                    "type": "narrative_truism",
                    "category": cat["category"],
                    "chapter_id": ch["id"],
                    "snippet": sentence,
                    "severity": cat["severity"],
                    "suggestion": cat["suggestion"],
                    "reason": cat.get("reason", "narrative truism"),
                })
    return {
        "issues": issues,
        "errors_count": sum(1 for i in issues if i["severity"] == "error"),
        "warnings_count": sum(1 for i in issues if i["severity"] == "warning"),
    }
```

### 3. Snapshot tests (mandatory)

`tests/test_class17_narrative_truism.py`:

```python
def test_class17_obvious_responsibility_v63_example():
    """v63 snapshot — sister taking responsibility truism."""
    paragraph = (
        "В те годы сестра, забравшая ребёнка из детдома, брала на себя "
        "огромную ответственность — продуктовые карточки, одежда, образование, "
        "всё ложилось на её плечи."
    )
    flags = validate_narrative_truism_for_paragraph(paragraph)
    assert any(f["category"] == "obvious_responsibility_constatation" for f in flags)
    # ALSO triggers everything_fell_on_shoulders pattern
    assert any(f["category"] == "everything_fell_on_shoulders" for f in flags)


def test_class17_accepted_calmly_v63_example():
    """v63 snapshot — subjective emotional ascription."""
    sentence = "Валентина приняла это решение сына спокойно."
    flags = validate_narrative_truism_for_paragraph(sentence)
    assert any(f["category"] == "accepted_calmly" for f in flags)


def test_class17_negative_specific_action():
    """Generic sentence with specific factual content — НЕ flag."""
    paragraph = (
        "Полина забрала Валентину из детдома и привезла в Старобельск, "
        "где жила с мужем."
    )
    flags = validate_narrative_truism_for_paragraph(paragraph)
    # Specific factual action, no truism pattern
    assert not flags


def test_class17_negative_quoted_phrase():
    """Если фраза в кавычках — это цитата из transcripts, НЕ flag."""
    paragraph = '«Это было непросто в те годы», — вспоминает Татьяна.'
    flags = validate_narrative_truism_for_paragraph(paragraph)
    assert not flags  # cited speech preserved
```

Per lesson v62a — каждый recurring pattern имеет snapshot test с конкретным example из реального прогона.

### 4. Integration в orchestrator (049f)

`collect_revision_hints` использует `validate_narrative_truism` output → конвертирует в hints:
- category → hint.category
- snippet → hint.snippet
- suggestion → hint.suggestion (default "delete_sentence")
- severity → hint.severity (warning → must_apply=false)

GW v2.23 (task 049e) применяет revision_hint → удаляет/переписывает.

### 5. Опциональный auto-rewrite (без revision pass)

В случаях когда revision pass пропускается (например, no errors-level issues + только warnings) — `enforce_narrative_truism` может delete_sentence для clear cases:

```python
def enforce_narrative_truism(book, validator_output, config):
    """Delete sentences with suggestion=delete_sentence (warning level OK)."""
    ...
```

Per Никитино «лучше медленно без откатов» — в v64 **только flag**, без auto-enforce. Revision pass (049f) — primary mechanism. Auto-enforce — backlog v65 если revision loop недостаточен.

---

## Risk и mitigation

**Risk A: False positives — generic sentence flagged как truism.**

**Mitigation:**
- Snapshot tests с negative cases (specific factual content not flagged)
- Severity = warning (не error) → GW при revision pass может legitимно skip
- Калибровка thresholds на v63 артефактах

**Risk B: GW добавит ещё больше truism в революцию pass когда удаляет существующие (compensation).**

**Mitigation:**
- ПРАВИЛО 13 в GW v2.23 явно запрещает добавлять не-flagged sentences
- Revision diff audit (049f) flag warning если изменения за пределами flagged

**Risk C: Pattern эволюция (как Class 11) — GW найдёт новые формы truism.**

**Mitigation:**
- Snapshot tests фиксируют конкретные v63 examples — patterns не возвращаются
- Если GW находит новые формы — add к patterns в следующем sprint (этой задачи не v65 — backlog)

---

## Ограничения

- [ ] Generic patterns, без subject-конкретики
- [ ] Idempotent validator
- [ ] Severity = warning (revision pass решает)
- [ ] Snapshot tests mandatory (lesson v62a)
- [ ] Negative tests required (избежать false positives)
- [ ] Scope = ch_02/ch_03/ch_04/epilogue (НЕ ch_01)
- [ ] Cited speech (within « » or `"..."`) — НЕ flag

---

## Dev Review

**Статус:** ожидает

**[TECH]** — pre-answer от Опуса:
- `narrative_stop_phrases.json: v3 → v4` (новая секция `narrative_truism.categories`)
- Validator function в `pipeline_utils.py`
- Cited speech detection: regex `«[^»]+»` and `"[^"]+"` — skip if pattern inside quotes
- 7 categories on day 1 — calibrate thresholds на v63 артефактах перед integration
- Suggestion field обязателен (consumer = 049f orchestrator)

**[PRODUCT]** — нет (Никита явно поднял Class 17 в v63 feedback)

**Сложность:** `s` (1-3 ч — patterns + validator + snapshot tests)
**Риск:** `low` (warning level + revision pass решает; snapshot tests catch false positives)

---

## Verified-on-run v64

**Cursor:** [после v64] — `narrative_truism_check.json` показывает flagged sentences
**Опус:** независимо посмотрит:
- ✅ v63 example «брал на себя огромную ответственность... всё ложилось на её плечи» — flagged
- ✅ v63 example «приняла это решение сына спокойно» — flagged
- ✅ Snapshot tests PASS (4+ tests)
- ✅ Hints переданы в GW revision pass → narrative переписан (либо truism удалён)

---

## История

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-18 | `new` | Опус |
