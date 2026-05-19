# Задача 046f: Historical_notes per-chapter distribution validator

**Статус:** `new`
**Номер:** 046f
**Автор:** Опус
**Дата создания:** 2026-05-19
**Тип:** `cco-скрипт` (новый валидатор)
**Sprint:** v65
**Связано:** task 046d (historical_notes enrichment); Class 9; Никитин feedback v64 — «показалось мало цитат историка»

---

## Контекст

В v64 historical_notes:
- 2 в field
- 8 inline (`***...***`)
- Total ≈10

Метрика **total** проходит target (≥5 inline + ≥3 field per distribution gate). Но **per-chapter** распределение может быть неравномерным:
- Все 8 inline могут быть в ch_02 (хронология) — там много дат
- В ch_03 (портрет) и ch_04 (эпизоды) может быть 0

Никитин feedback v64: «мало цитат историка» — возможно subjective, потому что **в портрете нет** historical контекста, а ch_02 переполнен.

**Решение:** validator проверяет distribution per chapter, не только total. Если в ch_03 / ch_04 = 0 — flag даже если total OK.

---

## Pre-sprint checklist

- [x] Stocktake актуален
- [x] Critical reading — v64 historical_notes count проверен per chapter
- [x] Universality — n/a (generic distribution validator)
- [x] Защита подключена — да, hint в revision pass либо в historical_notes enrichment (046d)
- [x] Прогон раздельный — combined OK
- [x] Класс — Class 9 (historical_notes underutilization) extend на distribution
- [x] Скрипт-first — да

---

## Спек

### 1. Новый валидатор `validate_historical_notes_distribution`

В `pipeline_utils.py`:

```python
def validate_historical_notes_distribution(book, config=None):
    """Check per-chapter distribution historical_notes (field + inline).

    Returns:
    {
        "per_chapter": {
            "ch_02": {"field": 2, "inline": 5, "total": 7},
            "ch_03": {"field": 0, "inline": 1, "total": 1},
            "ch_04": {"field": 0, "inline": 0, "total": 0},
            "epilogue": {"field": 0, "inline": 2, "total": 2},
        },
        "thresholds": {
            "ch_02": 3,  # хронология — больше всего
            "ch_03": 2,  # портрет с историческим контекстом
            "ch_04": 1,  # эпизоды (опционально)
            "epilogue": 0,  # epilogue без historical_notes OK
        },
        "issues": [
            {
                "type": "historical_notes_distribution",
                "category": "below_threshold_per_chapter",
                "chapter_id": "ch_04",
                "found": 0,
                "expected": 1,
                "severity": "warning",
                "suggestion": "Добавить ≥1 historical_note inline в ch_04 (эпизоды эпохи).",
                "reason": "Class 9 — historical_notes underutilization per chapter"
            }
        ],
        "total_field": 2,
        "total_inline": 8,
        "errors_count": 0,
        "warnings_count": N,
    }
    """
    thresholds = (config or {}).get("thresholds_per_chapter", {
        "ch_02": 3,
        "ch_03": 2,
        "ch_04": 1,
        "epilogue": 0,
    })

    per_chapter = {}
    historical_notes_root = book.get("historical_notes", [])
    # Field-level — attribution к chapter если есть
    for note in historical_notes_root:
        ch_id = note.get("chapter_id", "ch_02")  # default if not attributed
        per_chapter.setdefault(ch_id, {"field": 0, "inline": 0, "total": 0})
        per_chapter[ch_id]["field"] += 1

    # Inline-level — count *** patterns per chapter
    for ch in book.get("chapters", []):
        chid = ch.get("id")
        if chid == "ch_01":
            continue
        content = ch.get("content", "") or ""
        inline_count = len(re.findall(r'\*{3}[^*]+\*{3}', content))
        per_chapter.setdefault(chid, {"field": 0, "inline": 0, "total": 0})
        per_chapter[chid]["inline"] += inline_count

    # Compute totals
    for chid, counts in per_chapter.items():
        counts["total"] = counts["field"] + counts["inline"]

    issues = []
    for chid, expected in thresholds.items():
        found = per_chapter.get(chid, {"total": 0})["total"]
        if found < expected:
            issues.append({
                "type": "historical_notes_distribution",
                "category": "below_threshold_per_chapter",
                "chapter_id": chid,
                "found": found,
                "expected": expected,
                "severity": "warning",
                "suggestion": (
                    f"Добавить ≥{expected - found} historical_note inline в {chid}. "
                    f"Контекст: исторический фон эпохи (для ch_03 — социальный контекст характеристик, "
                    f"для ch_04 — контекст эпизодов). Не путать с personal-historical voice (task 046e)."
                ),
                "reason": "Class 9 historical_notes underutilization per chapter"
            })

    return {
        "per_chapter": per_chapter,
        "thresholds": thresholds,
        "issues": issues,
        "total_field": sum(c["field"] for c in per_chapter.values()),
        "total_inline": sum(c["inline"] for c in per_chapter.values()),
        "errors_count": sum(1 for i in issues if i["severity"] == "error"),
        "warnings_count": sum(1 for i in issues if i["severity"] == "warning"),
    }
```

### 2. Integration

- Validator подключён к orchestrator (049f-2) → warning hints в GW revision
- 046d historical_notes enrichment может **читать** per-chapter distribution → знает куда добавить inline notes (не только total, но и distribution)

### 3. Config

`historical_notes_distribution_config.json`:
```json
{
  "version": "v1",
  "thresholds_per_chapter": {
    "ch_02": 3,
    "ch_03": 2,
    "ch_04": 1,
    "epilogue": 0
  },
  "_notes": "Per-chapter distribution для 90-минутного интервью с историческим контекстом. Calibrate per subject."
}
```

### 4. Build_gate1 summary

Текущий summary:
```
Historical notes (field): 2
Historical notes (inline ***): 8
```

Новый:
```
Historical notes:
  - Field: 2
  - Inline: 8 (per chapter: ch_02=5, ch_03=1, ch_04=0 ⚠️, epilogue=2)
  - Total: 10 ✅ (target ≥8 distribution)
```

### 5. Тесты

`tests/test_historical_notes_distribution.py`:
- All chapters above threshold → no issues
- ch_04 = 0 inline + 0 field, threshold 1 → warning
- ch_02 over-saturated (10 inline), ch_03 = 0 → ch_03 warning (распределение)
- Negative: ch_01 skipped (паспортичка)

---

## Universality check

- [x] Промпт — n/a
- [x] Subject-specific — n/a (thresholds в config)
- [x] Algorithm generic
- [x] Subject-replacement — для Корольковой можно отрегулировать thresholds ✅

---

## Ограничения

- [ ] Severity warning (revision pass решает)
- [ ] Skip ch_01 (паспортичка)
- [ ] Thresholds config-driven
- [ ] Distinguish field vs inline в per-chapter view
- [ ] Idempotent

---

## Dev Review

**Статус:** ожидает

**[TECH]** — pre-answer от Опуса:
- Validator в `pipeline_utils.py`
- Build_gate1 summary update
- Integration с 046d enrichment — pass per-chapter info чтобы enrichment добавлял где нужно
- Snapshot tests на v64 distribution

**[PRODUCT]** — нет

**Сложность:** `xs` (<1 ч + tests)
**Риск:** `low`

---

## Verified-on-run v65

**Cursor:** [после v65]
**Опус:** независимо проверит `historical_notes_distribution.json`:
- per_chapter полный (ch_02/03/04/epilogue)
- В narrative ch_03 + ch_04 — историческое содержание (если было target ≥2/≥1)

---

## История

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-19 | `new` | Опус |
