# Задача 046d: Historical_notes enrichment script (post-Stage 2 ≥5 inline from fact_map.timeline)

**Статус:** `new`
**Номер:** 046d
**Автор:** Опус (роль архитектор+продакт)
**Дата создания:** 2026-05-18
**Тип:** `cco-скрипт` + historian agent reuse
**Sprint:** v64
**Связано:** task 041 (historical_notes anchors в pin-list); v62a artifacts (10 field + 10 inline) vs v63 (3 field + 0 inline — большая регрессия); product-decision Никиты 2b (target 20K = 15K narrative + 3K paspart + **2K historical_notes**)

---

## Контекст

**Никитин feedback v63:** «мало врезок историка, почему так? и нет исторических вкраплений рассказчика».

**Метрика регрессии:**
- v62a: 10 historical_notes field + 10 inline (`***...***` patterns) = ~20 контекстных врезок эпохи
- v63: 3 historical_notes field + 0 inline = ~3 врезки. **Большой откат**

**Корень:** в v62a Stage 1 split-extract + CA pin-list event mode давал richer fact_map, который GW использовал для inline врезок. В v63 GW v2.22 ПРАВИЛО 12 акцентировало narrative depth + voice, и **inline historical_notes deprioritized**.

**Архитектурное решение Никиты (развилка 2b):** target 20K = 15K narrative + 3K paspart + **2K historical_notes (objective context)**. Historical_notes как часть distribution gate, **не** narrative padding.

**Подход:** скрипт-first enrichment — post-Stage 2 проверка historical_notes count, если меньше 5 inline → автоматически добавить из fact_map.timeline + historian agent.

---

## Universality check

- [x] Промпт — n/a (script + reuse existing historian prompt)
- [x] Subject-specific — n/a (использует fact_map per subject; historian agent generic)
- [x] Алгоритм generic — для любого subject historical anchors из fact_map.timeline
- [x] Subject-replacement test — для Корольковой historian заполняет аналогично ✅

---

## Спек

### 1. Новая функция `enrich_historical_notes_inline`

В `pipeline_utils.py`:

```python
def enrich_historical_notes_inline(
    book: dict,
    fact_map: dict,
    pin_list_historical_anchors: list[dict] | None = None,
    config: dict | None = None,
) -> dict:
    """Post-Stage 2 enrichment: добавить inline historical_notes до minimum.

    Запускается:
    1. После Stage 2 GW (либо после revision pass — depends on orchestrator order)
    2. Cчитает текущие historical_notes inline (***...*** patterns)
    3. Если count < min_inline_notes:
       a. Определяет slots для вставки — paragraphs упоминающие year
          из fact_map.timeline без существующего inline note рядом
       b. Для каждого slot — вызывает historian agent с конкретным timeline event
          → получает 1-2 sentence historical context
       c. Inline-вставляет `***...***` в соответствующее место

    Config:
    - min_inline_notes: 5 (default per Никитин 2b target ~2K hist_notes)
    - min_field_notes: 3 (already covered by existing flow)
    - historian_prompt_version: "12_historian_v3" (current)
    """
    min_inline = (config or {}).get("min_inline_notes", 5)
    current_inline = _count_inline_historical_notes(book)
    if current_inline >= min_inline:
        return book  # already sufficient

    # Identify slots — paragraphs with year mentioned + matched timeline event
    slots = _identify_enrichment_slots(book, fact_map, pin_list_historical_anchors)

    # Generate historical context via historian agent (reuse existing)
    notes_added = 0
    for slot in slots:
        if current_inline + notes_added >= min_inline:
            break
        try:
            note_text = _generate_historical_note(
                slot=slot,
                fact_map=fact_map,
                pin_list_anchors=pin_list_historical_anchors,
            )
            if note_text:
                _insert_inline_note(book, slot, note_text)
                notes_added += 1
        except Exception as e:
            # Log skip, continue
            ...

    return book


def _count_inline_historical_notes(book: dict) -> int:
    """Count ***...*** patterns в всех chapters."""
    count = 0
    for ch in book.get("chapters", []):
        content = ch.get("content", "") or ""
        count += len(re.findall(r'\*{3}[^*]+\*{3}', content))
    return count


def _identify_enrichment_slots(book, fact_map, pin_list_anchors) -> list[dict]:
    """Identify candidate locations for new inline historical_notes.

    Heuristic:
    1. Paragraphs with year mention (\\d{4}) в ch_02/ch_03
    2. Year matches timeline event с историческим контекстом
       (либо pin_list_historical_anchors anchor с этим year)
    3. Paragraph не содержит уже inline note рядом
    4. Distance от другого inline note ≥2 paragraphs (избежать over-clustering)

    Returns list of slots: {chapter_id, paragraph_index, year, anchor_hint}.
    """
    ...


def _generate_historical_note(slot, fact_map, pin_list_anchors) -> str | None:
    """Call historian agent for 1-2 sentence context.

    Reuses existing historian prompt (12_historian_v3.md).
    Input: year + brief slot context (sentences around).
    Output: short historical fact (2-3 sentences max) wrapped в *** ... ***.

    Если historian не находит достоверного контекста → return None (skip slot).
    """
    ...


def _insert_inline_note(book, slot, note_text):
    """Insert note as `*** {note_text} ***` after the sentence в slot.paragraph."""
    ...
```

### 2. Pin-list extension (опционально usage уже есть)

`known_episodes_karakulina.md` v6 секция `## historical_notes anchors` (уже есть в v4, секция расширяется при необходимости). В v64 не обязательно расширять — task 044h может включить дополнительные anchors если нужно.

### 3. Stage 2 runner integration

В `scripts/test_stage2_pipeline.py` (после revision pass, перед save book_FINAL):

```python
# Post-revision: enrichment historical_notes inline if below threshold
fact_map = load_artifact("fact_map_full.json")
book_final = enrich_historical_notes_inline(
    book=book_after_revision,  # or book_draft if no revision
    fact_map=fact_map,
    pin_list_historical_anchors=parse_historical_anchors(pin_list_path),
    config={"min_inline_notes": 5},
)
save_artifact(book_final, "book_FINAL.json")
save_artifact(
    {
        "inline_before": count_before,
        "inline_after": count_after,
        "slots_filled": count_after - count_before,
    },
    "historical_notes_enrichment_log.json",
)
```

### 4. Конфиг

`historical_notes_enrichment_config.json` (generic):
```json
{
  "min_inline_notes": 5,
  "min_field_notes": 3,
  "max_inline_notes": 12,
  "historian_prompt_version": "12_historian_v3",
  "skip_chapters": ["ch_01"],
  "min_distance_between_inline": 2,
  "anchor_year_tolerance": 2
}
```

### 5. Тесты

`tests/test_historical_notes_enrichment.py`:
- **Schema:** book с 10 inline notes (уже sufficient) → returned unchanged
- **Schema:** book с 0 inline + 3 candidate slots в timeline → 3 slots filled
- **Slot detection:** paragraph «В 1933 году голод» с timeline event «hn_holodomor 1933» → slot identified
- **Distance constraint:** 2 candidate paragraphs adjacent → only 1 filled (distance ≥2)
- **Idempotent:** повторный enrichment не добавляет (уже sufficient)
- **Negative:** historian возвращает None → slot skipped, не error

---

## Risk и mitigation

**Risk A: Historian agent добавляет factually wrong context.**

**Mitigation:**
- Historian уже battle-tested (v54-v63 — generic правки минимальны)
- Validator anti_facts (task 043e v62a) проверит added inline notes на pin-list anti-facts violations
- Generated text validated через `validate_historical_note_grounding` (existing task 038)

**Risk B: Over-enrichment — слишком много врезок снижает читаемость.**

**Mitigation:**
- `max_inline_notes: 12` cap
- `min_distance_between_inline: 2` — не плотные кластеры
- Skip ch_01 (паспортичка structured, не narrative)

**Risk C: Historian agent добавит ~$0.50-1 на прогон.**

**Mitigation:**
- Acceptable cost (v64 total ~$5-6 OK)
- Skip if уже sufficient (count check first)

**Risk D: pin_list_historical_anchors отсутствуют для subject.**

**Mitigation:**
- Fallback: auto-generate anchors из fact_map.timeline.events с year
- Historian decides сам, был ли достоверный контекст для year
- Если pin-list anchors есть — use them (better quality)

---

## Ограничения

- [ ] Generic — не subject-specific
- [ ] Idempotent — повторный вызов не дублирует
- [ ] Min/max thresholds в config
- [ ] Skip ch_01 (paspart structured)
- [ ] Historian agent reuse — no new prompt
- [ ] При revision pass orchestrator (049f) этот скрипт запускается **после** revision (или после draft если revision_hints пуст)

---

## Dev Review

**Статус:** ожидает

**[TECH]** — pre-answer от Опуса:
- Reuse `12_historian_v3.md` prompt (без изменений)
- Slot detection через regex year + cross-ref с fact_map.timeline
- Historical_notes enrichment runs **после** Stage 2 (либо first pass, либо revision) и **до** Stage 3 LE
- Anti_facts + historical_note_grounding validators применяются после enrichment (existing flow)

**[PRODUCT]** — нет (Никитин 2b sign-off: historical_notes ≥5 inline как часть target 20K)

**Сложность:** `s` (1-3 ч) + integration test ~30 min
**Риск:** `low` (historian battle-tested; validators catch hallucinations)

---

## Verified-on-run v64

**Cursor:** [после v64] — отчёт по slots_filled
**Опус:** независимо проверит `historical_notes_enrichment_log.json` + посчитает inline `***...***` в text_FULL.md:
- ✅ Inline count ≥5
- ✅ Field count ≥3
- ✅ Total historical_notes chars ≈2K
- ✅ Никаких inline в ch_01

---

## История

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-18 | `new` | Опус |
