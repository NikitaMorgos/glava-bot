# Задача v65-meta: build_gate1 — pin-list coverage breakdown понятный (required vs optional)

**Статус:** `new`
**Номер:** v65-meta-build_gate1
**Автор:** Опус
**Дата создания:** 2026-05-19
**Тип:** `cco-скрипт` (build_gate1 enhancement)
**Sprint:** v65
**Связано:** task 044i (pin-list v7 `required_in_narrative` markers); Никитин вопрос v64 «что это значит — Pin-list full 14/67 partial 7/67 skipped 46/67?»

---

## Контекст

Текущий build_gate1 summary показывает:
```
Pin-list coverage:
- Episodes full: 14 / 67
- Episodes partial: 7 / 67
- Episodes skipped: 46 / 67
```

Никита спросил что это значит. Проблема:
- 67 эпизодов в pin-list = всё что мы знаем про Валентину (включая мелкие бытовые, антитриггеры, контрольные anchors)
- Не все 67 должны попасть в narrative
- Метрика «skipped 46/67» = 69% — выглядит как plохо, **но** это **по дизайну** (мелкие детали optional)
- Реальная проблема: в «skipped» попадают **важные** эпизоды (грибы/ягоды, дача) — пользователь не различает

---

## Pre-sprint checklist

- [x] Stocktake актуален
- [x] Critical reading — v64 build_gate1 summary прочитан, Никитин feedback identified
- [x] Universality — да (generic enhancement)
- [x] Защита подключена — нет, это reporting fix (но связан с task 044i required_episodes mechanism)
- [x] Прогон раздельный — combined OK (no LLM call)
- [x] Класс — «reporting clarity» (generic, не subject-specific)
- [x] Скрипт-first — да

---

## Спек

### 1. Pin-list coverage с разделением на required vs optional

В `scripts/build_gate1_full_text.py` — функция формирующая summary:

```python
def render_pin_list_coverage_summary(pin_list, book):
    """Render pin-list coverage section с разделением required vs optional.

    Required = episodes с `required_in_narrative: true` (task 044i)
    Optional = остальные (informational)
    """
    episodes = pin_list.get("episodes", []) + pin_list.get("bytovye", [])

    required_episodes = [e for e in episodes if e.get("required_in_narrative")]
    optional_episodes = [e for e in episodes if not e.get("required_in_narrative")]

    required_found = []
    required_missing = []
    for ep in required_episodes:
        if _episode_found_in_book(ep, book, min_match_count=1):
            required_found.append(ep)
        else:
            required_missing.append(ep)

    optional_mentioned = sum(1 for ep in optional_episodes
                             if _episode_found_in_book(ep, book, min_match_count=1))

    lines = [
        "## Pin-list coverage",
        "",
        f"- **Required in narrative: {len(required_found)} / {len(required_episodes)} covered** {'✅' if not required_missing else '⚠️'}",
    ]
    if required_missing:
        missing_names = ", ".join(f"`{e['episode_id']}` «{e['title'][:40]}...»" for e in required_missing[:5])
        lines.append(f"  - Missing ({len(required_missing)}): {missing_names}")
        if len(required_missing) > 5:
            lines.append(f"  - + {len(required_missing) - 5} more (full list в required_episodes_coverage.json)")
    lines.append(f"- Optional episodes: {optional_mentioned} / {len(optional_episodes)} mentioned (informational)")

    # Backward compatibility — старая метрика как сводка
    full_count = required_found + [e for e in optional_episodes if _episode_found_in_book(e, book, min_match_count=3)]
    partial_count = [e for e in optional_episodes if 1 <= _episode_match_count(e, book) < 3]
    skipped_count = [e for e in episodes if _episode_match_count(e, book) == 0]
    lines.extend([
        "",
        f"- Legacy metric: full={len(full_count)} / partial={len(partial_count)} / skipped={len(skipped_count)} (total {len(episodes)})",
    ])

    return "\n".join(lines)
```

### 2. Output example v65

```
## Pin-list coverage

- **Required in narrative: 18 / 20 covered** ⚠️
  - Missing (2): `byt_009` «Не любила грибы/ягоды; тётя Маша...», `ep_029` «Продажа дачи (до 1990-х по уточнению...)»
- Optional episodes: 12 / 47 mentioned (informational)

- Legacy metric: full=22 / partial=8 / skipped=37 (total 67)
```

**Понятно:**
- 18 из 20 обязательных эпизодов покрыты ✅ (хорошо)
- 2 missing — конкретный список (грибы, дача) ⚠️ (вот что фиксить)
- 12/47 optional mentioned — informational (не блокер)

### 3. Backward compatibility

Старая метрика `full/partial/skipped` сохраняется (Legacy metric line) — для исторического сравнения с v54-v64. Новая метрика — primary.

### 4. Тесты

`tests/test_pin_list_coverage_render.py`:

```python
def test_pin_list_coverage_required_breakdown():
    """Required episodes — breakdown с missing list."""
    pin_list = {
        "episodes": [
            {"episode_id": "ep_001", "title": "Голод 1933", "markers": ["голод", "1933"], "required_in_narrative": True},
            {"episode_id": "ep_029", "title": "Дача продажа", "markers": ["продал.*дач"], "required_in_narrative": True},
        ],
        "bytovye": []
    }
    book = {"chapters": [{"id": "ch_02", "content": "В 1933 году был голод..."}]}
    summary = render_pin_list_coverage_summary(pin_list, book)
    assert "Required in narrative: 1 / 2 covered" in summary
    assert "ep_029" in summary  # missing


def test_pin_list_coverage_all_required_covered():
    """Все required — ✅."""
    pin_list = {...}
    book = {...}
    summary = render_pin_list_coverage_summary(pin_list, book)
    assert "covered ✅" in summary
    assert "Missing" not in summary
```

### 5. Output JSON (для validators consumption)

В artifacts добавить `required_episodes_coverage.json`:
```json
{
  "required_episodes": [
    {"episode_id": "ep_017", "title": "Дача в 60-х", "found": true, "mentions": 2, "chapter": "ch_02"},
    {"episode_id": "ep_029", "title": "Продажа дачи", "found": false},
    {"episode_id": "byt_009", "title": "Грибы/ягоды", "found": false}
  ],
  "covered_count": 18,
  "missing_count": 2,
  "total_required": 20,
  "optional_mentioned": 12,
  "optional_total": 47
}
```

Это **тот же** артефакт что `validate_required_episodes_coverage` (task 044i) production output. Consume same — build_gate1 reads JSON либо вычисляет в-place.

---

## Universality check

- [x] Промпт — n/a
- [x] Subject-specific — n/a (rendering generic)
- [x] Algorithm generic
- [x] Subject-replacement — для любого subject pin-list с required markers ✅

---

## Ограничения

- [ ] Backward compatibility (legacy metric остаётся)
- [ ] Missing list ограничен (top 5 + «more»)
- [ ] Зависит от task 044i (`required_in_narrative` marker в pin-list v7)
- [ ] Idempotent

---

## Dev Review

**Статус:** ожидает

**[TECH]** — pre-answer от Опуса:
- Изменение в `scripts/build_gate1_full_text.py` render summary
- Consume `pin_list.required_in_narrative` markers (task 044i prerequisite)
- Output JSON `required_episodes_coverage.json` reuse существующего validator output

**[PRODUCT]** — нет (Никитин вопрос-clarity, явно user-facing fix)

**Сложность:** `xs` (<1 ч + tests)
**Риск:** `low`

---

## Verified-on-run v65

**Cursor:** [после v65]
**Опус:** проверит:
- В `karakulina_v65_text_FULL.md` summary header — секция Pin-list coverage в новом формате
- «Required: N / M covered» + missing list присутствует
- Legacy metric тоже остаётся (для сравнения с предыдущими прогонами)

---

## История

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-19 | `new` | Опус |
