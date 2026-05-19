# Задача 048g: Class 19 NEW — cross-paragraph text duplication (дословный повтор абзацев)

**Статус:** `new`
**Номер:** 048g
**Автор:** Опус
**Дата создания:** 2026-05-19
**Тип:** `cco-скрипт` (новый валидатор) + snapshot tests
**Sprint:** v65
**Связано:** Никитин feedback v64 — «дословно повторяется один абзац» (про крещения/Власьево); новый класс багов

---

## Контекст

**Никитин feedback v64 (точная цитата):**
> «дословно повторяется один абзац. Даже в 1990-е годы, когда в семье прошла волна крещений, сама не крестилась. Несколько раз ходила в Воскресенскую церковь во Власево, но в душе осталась атеисткой. В доме не было икон, Библии — "вообще ничего про Бога не было".»

Один и тот же paragraph появился **дважды** в narrative v64. Это **новый класс** который мы не лечили:

- **Class 19 NEW: Cross-paragraph text duplication** — дословный или near-дословный повтор одного и того же содержательного фрагмента в разных местах книги (в одной главе либо в разных).

Отличается от:
- **Class 4 cross-chapter dedup** (волна 1.2) — это про **тот же эпизод** дословно раскрытый в 2+ главах. Но это **разные** проблемы:
  - Class 4 = «развёрнутый эпизод про огурцы и в ch_02 и в ch_04»
  - Class 19 = «дословный повтор одного абзаца в одной главе либо разных»

---

## Pre-sprint checklist

- [x] Stocktake актуален
- [x] Critical reading — v64 narrative прочитан, дубль найден Никитой
- [x] Universality — n/a (text similarity generic)
- [x] Защита подключена к лечению — да, hint в revision pass (delete duplicate)
- [x] Прогон раздельный — combined OK
- [x] Класс багов, не симптом — Class 19 NEW generic
- [x] Скрипт-first — да

---

## Спек

### 1. Новый валидатор `validate_cross_paragraph_duplication`

В `pipeline_utils.py`:

```python
def validate_cross_paragraph_duplication(book, config=None):
    """Detect cross-paragraph дословное повторение текста.

    Algorithm:
    1. Извлечь все paragraphs из chapters.content (split by \n\n)
    2. Для каждого paragraph длиной ≥min_chars (default 100):
       a. Нормализовать (lower, strip whitespace, remove markdown)
       b. Сравнить с другими paragraphs через similarity (Jaccard на 3-gram words либо normalized longest common substring)
    3. Если similarity >= threshold (default 0.85) И длина оригинала >= min_chars:
       flag duplicate

    Config:
    - min_paragraph_chars: 100 (короткие фразы могут повторяться legitimno)
    - similarity_threshold: 0.85
    - skip_quoted_only: true (если paragraph — только цитата в кавычках, skip)
    - exempt_callouts: true (callouts могут повторять цитаты)
    """
    config = config or {}
    min_chars = config.get("min_paragraph_chars", 100)
    threshold = config.get("similarity_threshold", 0.85)

    paragraphs = []
    for ch in book.get("chapters", []):
        if ch.get("id") == "ch_01":
            continue  # паспортичка может иметь повторяющиеся sections
        content = ch.get("content", "") or ""
        for idx, para in enumerate(content.split("\n\n")):
            para_clean = _normalize_for_dedup(para)
            if len(para_clean) >= min_chars:
                paragraphs.append({
                    "chapter_id": ch["id"],
                    "paragraph_index": idx,
                    "text": para,
                    "normalized": para_clean,
                })

    issues = []
    seen = []
    for p in paragraphs:
        for prev in seen:
            sim = _text_similarity(prev["normalized"], p["normalized"])
            if sim >= threshold:
                issues.append({
                    "type": "cross_paragraph_duplication",
                    "category": "duplicate_paragraph",
                    "similarity": round(sim, 3),
                    "original_chapter_id": prev["chapter_id"],
                    "original_paragraph_index": prev["paragraph_index"],
                    "duplicate_chapter_id": p["chapter_id"],
                    "duplicate_paragraph_index": p["paragraph_index"],
                    "snippet": p["text"][:200],
                    "severity": "error",
                    "suggestion": (
                        f"Удалить duplicate paragraph (index {p['paragraph_index']} в "
                        f"{p['chapter_id']}). Оригинал в {prev['chapter_id']} "
                        f"(index {prev['paragraph_index']}). Если содержит уникальный fact — "
                        f"переписать со ссылкой на оригинал либо объединить."
                    ),
                    "reason": "Class 19 — cross-paragraph дословное повторение текста"
                })
                break  # один duplicate per paragraph
        seen.append(p)

    return {
        "issues": issues,
        "errors_count": len(issues),
        "warnings_count": 0,
    }


def _normalize_for_dedup(text):
    """Normalize text для similarity comparison."""
    # Strip markdown markers
    text = re.sub(r'\*+|_+|`+', '', text)
    # Lowercase + collapse whitespace
    text = re.sub(r'\s+', ' ', text.lower().strip())
    # Strip leading/trailing punctuation
    text = text.strip(' .,;:!?-')
    return text


def _text_similarity(a, b):
    """Jaccard similarity on 3-gram words OR normalized longest common substring ratio.

    Lightweight, без heavy deps. Возможно использовать difflib.SequenceMatcher.ratio() — built-in.
    """
    from difflib import SequenceMatcher
    return SequenceMatcher(None, a, b).ratio()
```

### 2. Конфиг

`cross_paragraph_duplication_config.json` (generic):
```json
{
  "min_paragraph_chars": 100,
  "similarity_threshold": 0.85,
  "skip_chapters": ["ch_01"],
  "skip_quoted_only": true,
  "exempt_callouts": true
}
```

### 3. Integration с orchestrator (049f-2)

Validator подключён к orchestrator → revision_hint с suggestion «удалить duplicate paragraph».

GW v2.24 ПРАВИЛО 13 переписывает (либо удаляет paragraph) per hint.

### 4. Snapshot tests

`tests/test_cross_paragraph_duplication.py`:

```python
def test_v64_duplicate_krescheniya_vlasevo():
    """v64 snapshot — дословный повтор абзаца про крещения/Власьево."""
    para = (
        "Даже в 1990-е годы, когда в семье прошла волна крещений, сама не "
        "крестилась. Несколько раз ходила в Воскресенскую церковь во Власево, "
        "но в душе осталась атеисткой. В доме не было икон, Библии — "
        "«вообще ничего про Бога не было»."
    )
    book = {"chapters": [
        {"id": "ch_03", "content": f"Some intro paragraph.\n\n{para}\n\nSome ending."},
        {"id": "ch_04", "content": f"Other intro.\n\n{para}\n\nOther ending."},
    ]}
    result = validate_cross_paragraph_duplication(book)
    assert result["errors_count"] == 1
    assert result["issues"][0]["similarity"] > 0.95


def test_negative_short_phrases_repeat():
    """Короткие фразы (например cited «такая она и есть») могут повторяться — НЕ flag."""
    book = {"chapters": [
        {"id": "ch_02", "content": "First para about Германия.\n\n«Такая она и есть»."},
        {"id": "ch_03", "content": "Other para.\n\n«Такая она и есть»."},
    ]}
    result = validate_cross_paragraph_duplication(book)
    assert result["errors_count"] == 0  # below min_paragraph_chars


def test_negative_paraphrase_below_threshold():
    """Перефразирование с ~50% сходства — НЕ flag."""
    para1 = "В Германии Валентина не работала, занималась домом и хозяйством."
    para2 = "В период послевоенной Германии она вела домашнее хозяйство."
    book = {"chapters": [
        {"id": "ch_02", "content": f"{para1}\n\nДругая тема."},
        {"id": "ch_03", "content": f"{para2}\n\nЕщё что-то."},
    ]}
    result = validate_cross_paragraph_duplication(book)
    # Sim ~0.5 — below threshold 0.85
    assert result["errors_count"] == 0


def test_idempotent():
    """Повторный вызов даёт same result."""
    ...
```

---

## Universality check

- [x] Промпт — n/a
- [x] Subject-specific — n/a (text similarity generic)
- [x] Algorithm generic — Jaccard / SequenceMatcher без subject knowledge
- [x] Subject-replacement — для Корольковой/Дмитриева работает без правок ✅

---

## Ограничения

- [ ] min_chars = 100 (короткие фразы могут legitimno повторяться)
- [ ] Threshold 0.85 (calibrate на v64 при необходимости)
- [ ] Skip ch_01 (паспортичка структурно может повторяться)
- [ ] Skip cited speech (callouts) — exempt callouts
- [ ] Severity error (явный дубль — нарушение качества)
- [ ] Idempotent
- [ ] SequenceMatcher built-in (no extra deps)

---

## Dev Review

**Статус:** ожидает

**[TECH]** — pre-answer от Опуса:
- Используем `difflib.SequenceMatcher` (built-in stdlib)
- Suggestion «удалить duplicate» — primary action для GW при revision pass
- Threshold calibrate на v64 пример (similarity дубля Власьево должна быть >0.9)

**[PRODUCT]** — нет (Никитин feedback, явный bug)

**Сложность:** `xs` (<1 ч + tests)
**Риск:** `low` (новый detector, не trog existing)

---

## Verified-on-run v65

**Cursor:** [после v65]
**Опус:** независимо проверит:
- `cross_paragraph_duplication_check.json` — 0 errors (если revision pass удалил дубли)
- Snapshot tests PASS
- В v65 narrative дубль Власьево отсутствует

---

## История

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-19 | `new` | Опус |
