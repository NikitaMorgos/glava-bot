# Задача 049f: Revision hints orchestrator (collect + format + Stage 2 revision pass + diff audit)

**Статус:** `new`
**Номер:** 049f
**Автор:** Опус (роль архитектор+продакт)
**Дата создания:** 2026-05-18
**Тип:** `cco-скрипт` (большая задача — отдельный модуль)
**Sprint:** v64
**Связано:** task 049e (GW v2.23 ПРАВИЛО 13 — consumer of revision_hints); все validators в `pipeline_utils.py`

---

## Контекст

Архитектурный partner для task 049e. ПРАВИЛО 13 в GW v2.23 говорит «получи revision_hints → переписывай flagged sentences». Этот task — **producer + dispatcher** revision_hints.

Поток:
1. Stage 2 GW first pass → `book_draft.json`
2. **Все validators** прогоняются на `book_draft` (chronology, pin_list_depth, style_checks, narrative_stop_phrases, anti_facts, discourse_markers, новые Class 17 / 18)
3. **Orchestrator (этот task)** собирает все validator outputs → конвертирует в формат `revision_hints` для GW
4. Stage 2 GW second pass с `call_type="revision"` + `revision_hints` → `book_after_revision.json`
5. **Orchestrator diff audit**: сравнить draft vs after_revision; проверить что ПРАВИЛО 0 SCOPE LOCK не нарушено (только flagged sentences изменены)
6. Если revision_failed=true → stop, Опус review
7. Иначе → проход к Stage 3 (LE + post-processing)

---

## Universality check

- [x] Промпт — n/a (чистый скрипт)
- [x] Subject-specific — n/a (orchestrator работает с любым subject)
- [x] Алгоритм generic — собирает validator outputs (которые сами generic), нет hardcoded subject
- [x] Subject-replacement test — для Корольковой/Дмитриева revision pass работает аналогично ✅

---

## Спек

### 1. Новый модуль `pipeline_utils/revision_orchestrator.py` (или extend `pipeline_utils.py`)

```python
def collect_revision_hints(
    book_draft: dict,
    validator_outputs: dict,  # все JSON reports от validators
    config: dict | None = None,
) -> list[dict]:
    """Собрать revision_hints из validator outputs в формат для GW.

    Reads from:
    - chronology_check.json
    - pin_list_depth.json
    - style_checks.json (включая sub-categories: epilogue_stop_phrases,
      awkward_formulation, narrative_stop_phrases)
    - anti_facts_check.json
    - discourse_markers.json
    - narrative_truism_check.json  # task 043h
    - personal_historical_voice_check.json  # task 046e

    Каждая issue → один hint в стандартном формате (см. ниже).
    """
    hints = []
    hint_counter = 0

    for validator_name, output in validator_outputs.items():
        issues = output.get("issues", [])
        for issue in issues:
            hint_counter += 1
            hint = build_hint(
                hint_id=f"h_{hint_counter:03d}",
                validator=validator_name,
                issue=issue,
                book_draft=book_draft,  # для localization snippet
            )
            if hint:  # некоторые issues не actionable (e.g. info-only)
                hints.append(hint)
    return hints


def build_hint(hint_id, validator, issue, book_draft) -> dict | None:
    """Convert single validator issue to GW revision_hint format."""
    # Универсальные поля
    hint = {
        "hint_id": hint_id,
        "validator": validator,
        "category": issue.get("category") or issue.get("type"),
        "chapter_id": issue.get("chapter_id"),
        "severity": issue.get("severity", "warning"),
        "snippet": issue.get("snippet") or _extract_snippet(book_draft, issue),
        "reason": _build_reason(validator, issue),
        "suggestion": _build_suggestion(validator, issue),
        "must_apply": issue.get("severity") == "error",
    }
    if not hint["snippet"]:
        return None  # cannot localize → skip (warning level OK to skip)
    return hint


def _build_suggestion(validator, issue) -> str:
    """Generate concrete suggestion per validator category."""
    cat = issue.get("category") or issue.get("type") or ""

    # Map per validator category
    if validator == "chronology_check":
        if cat == "person_mentioned_before_birth":
            return (
                f"Удалить упоминание ребёнка [{issue.get('person_name')}] "
                f"в этом контексте. Этот ребёнок родился позже {issue.get('event_year_range')}. "
                f"Заменить на 'занималась домом' / 'вела хозяйство' / 'жила одна' "
                f"или контекст-appropriate phrasing."
            )
        if cat == "children_mentioned_before_first_child_birth":
            return (
                f"Удалить plural упоминание детей. first_child_birth = "
                f"{issue.get('first_child_birth')}. Текущий контекст ранее. "
                f"Заменить на single-person context (без plural дети)."
            )

    if validator == "narrative_truism":
        return "delete_sentence"  # task 043h Class 17 — обычно удалить целиком

    if validator == "narrative_stop_phrases":
        if cat in ("speciality_defined_life", "speciality_defined_life_recurring"):
            return (
                "Удалить causal claim (часть после тире про 'определила жизнь'). "
                "Оставить только factual content (год обучения, специальность)."
            )
        if cat == "typical_for_generation":
            return "delete_sentence (целиком, без замены)"
        # ... (другие categories)

    if validator == "pin_list_depth":
        return (
            f"Развернуть эпизод [{issue.get('episode_id')}] на ≥3 sentences "
            f"per ПРАВИЛО 12. Текущая глубина: {issue.get('actual_sentences')} sent. "
            f"Добавить: setup year+место+кто / детали действия / последствие."
        )

    if validator == "anti_facts":
        return (
            f"Не объединять [{issue.get('item_A')}] с [{issue.get('item_B')}] "
            f"в одном sentence/paragraph. В источнике это отдельные позиции."
        )

    if validator == "discourse_markers":
        if cat == "below_threshold":
            return (
                f"Добавить ≥{issue['expected'] - issue['found']} discourse markers "
                f"({issue.get('chapter_id')}). Pattern: '[rapporteur] вспоминает' / "
                f"'по словам [rapporteur]' / 'как помнит [родственное_отношение]'. "
                f"Использовать имена из discourse_markers config."
            )

    if validator == "personal_historical_voice":
        if cat == "below_threshold":
            return (
                f"Добавить personal-historical voice anchors в narrative: "
                f"'[rapporteur] помнит как в [период] ...' / 'тогда в нашей семье ...' / "
                f"'когда я был ребёнком, в [период], [исторический контекст]'. "
                f"Использовать narrator_voice_anchors из pin-list."
            )

    # Default fallback
    return issue.get("suggestion") or "Переписать или удалить flagged sentence."


def _build_reason(validator, issue) -> str:
    """Generate human-readable reason."""
    cat = issue.get("category") or issue.get("type") or "unknown"
    severity = issue.get("severity", "warning")
    return f"{validator}/{cat} ({severity})"


def _extract_snippet(book_draft, issue) -> str | None:
    """Если в issue нет snippet — попытаться найти в book_draft."""
    # Реализация: ищется paragraph по chapter_id + другим markers
    # (year_range / person_name / pattern match)
    ...
```

### 2. Stage 2 runner extension

В `scripts/test_stage2_pipeline.py`:

```python
# После first GW pass (existing)
book_draft = run_gw_first_pass(...)
save_artifact(book_draft, "book_draft.json")

# Run all validators on book_draft
validator_outputs = run_all_validators(book_draft, fact_map, configs)
save_artifact(validator_outputs, "validators_on_draft.json")

# Collect revision_hints
revision_hints = collect_revision_hints(book_draft, validator_outputs)

if not revision_hints:
    # No issues found → no revision needed
    book_final = book_draft
    save_artifact({"skipped": "no_revision_hints"}, "revision_pass_log.json")
else:
    # Stage 2 revision pass
    book_after_revision = run_gw_revision_pass(
        current_book=book_draft,
        revision_hints=revision_hints,
        call_type="revision",
    )

    # Audit: diff between draft and revision
    diff_audit = audit_revision_diff(
        book_draft, book_after_revision, revision_hints,
    )
    save_artifact(diff_audit, "revision_diff_audit.json")

    # Check revision_failed flag
    revision_meta = book_after_revision.get("writing_notes", {})
    if revision_meta.get("rule13_revision_failed"):
        raise RevisionFailedError(
            f"GW не выполнил revision: {revision_meta.get('rule13_revision_failed_reason')}"
        )

    book_final = book_after_revision

save_artifact(book_final, "book_FINAL.json")
```

### 3. Diff audit функция

```python
def audit_revision_diff(
    book_draft: dict,
    book_after_revision: dict,
    revision_hints: list[dict],
) -> dict:
    """Sanity check: что revision pass changed only flagged sentences.

    Per ПРАВИЛО 0 SCOPE LOCK + ПРАВИЛО 13: только snippets из revision_hints
    должны быть changed; rest unchanged.

    Returns:
    {
        "hints_count": int,
        "applied": [{"hint_id": ..., "before": ..., "after": ...}],
        "skipped": [{"hint_id": ..., "reason": ...}],
        "unauthorized_changes": [{"chapter_id": ..., "diff_snippet": ...}],
        # ^ если изменилось что-то не из revision_hints — это нарушение
        "writing_notes_proof": book_after_revision.get("writing_notes", {}).get("rule13_revision_applied", []),
    }
    """
    ...
```

Если `unauthorized_changes` не пуст → warning (не error, потому что GW может legitимно добавить connecting phrase). Но если >5 unauthorized changes — flag для Опуса review.

### 4. Конфиг (опционально)

`revision_orchestrator_config.json`:
```json
{
  "max_revision_passes": 1,
  "stop_on_revision_failed": true,
  "audit_unauthorized_changes_warn_threshold": 5,
  "skip_validators": []
}
```

### 5. Тесты

`tests/test_revision_orchestrator.py`:
- **Schema:** `collect_revision_hints(empty_validators)` → `[]`
- **Conversion:** chronology issue → hint format (snippet + reason + suggestion + must_apply=true для error)
- **Suggestion building:** per validator/category → correct concrete suggestion
- **Diff audit:** simulated draft + revision → unauthorized_changes detection
- **Schema test:** revision pass output без `rule13_revision_applied` → RevisionFailedError raised

---

## Risk и mitigation

**Risk A: Revision pass дороже + медленнее (2 LLM passes vs 1).**

**Mitigation:**
- Финансово: $4-6 vs $2-3. Acceptable per Никитино go.
- Время: +2-3 минуты per Stage 2. Не критично.
- Optimization v65 backlog: можно cache draft → если revision_hints малые (<5), skip revision pass — но в v64 always run.

**Risk B: GW при revision sometimes ломает связность.**

**Mitigation:**
- Diff audit (unauthorized_changes warning)
- LE Stage 3 + post-processing исправят минор связность
- Если major breakage → revision_failed flag → stop

**Risk C: revision_hints пустой — orchestrator пропускает revision pass.**

**Mitigation:**
- Это **корректное** поведение (если validators 0 errors — revision не нужен). В artifacts фиксируется `{"skipped": "no_revision_hints"}`.
- Документировать в run_registry: «v64 revision pass = applied / skipped»

**Risk D: validators не дают concrete suggestions (e.g. сложные семантические patterns).**

**Mitigation:**
- `_build_suggestion` имеет per-category mapping; fallback на generic «переписать или удалить»
- В v64 sprint каждый validator должен возвращать `suggestion` field (расширение task'ов 043h, 046d, 046e, 043d-2, 043f-2 включает suggestion field)

---

## Ограничения

- [ ] Generic orchestrator — не subject-specific
- [ ] Subject content приходит через book_draft + validator outputs
- [ ] Idempotent: повторный вызов с same inputs → same hints
- [ ] Max 1 revision pass в v64 (Loop prevention; v65+ может иметь 2)
- [ ] revision_failed flag → STOP (не silently proceed)
- [ ] diff audit warning при unauthorized_changes >threshold

---

## Dev Review

**Статус:** ожидает

**[TECH]** — pre-answer от Опуса:
- Файлы: возможно отдельный `pipeline_utils/revision_orchestrator.py` (новый модуль) или extend `pipeline_utils.py` (~600 строк добавится). Курсорское решение
- Stage 2 runner extend — `scripts/test_stage2_pipeline.py` добавляется revision pass logic
- Artifacts добавляются: `book_draft.json`, `validators_on_draft.json`, `revision_diff_audit.json`, `revision_pass_log.json` (либо `{"skipped": ...}`)
- Suggestion generation centralized в `_build_suggestion()` — extensible per validator

**[PRODUCT]** — нет (архитектурный, Никита sign-off на развилке 1b)

**Сложность:** `m` (3-8 ч — большая часть, новый модуль + 5+ функций + tests)
**Риск:** `medium` (новая архитектура; mitigation diff audit + revision_failed flag + max 1 pass)

---

## Verified-on-run v64

**Cursor:** [после v64 прогона] — отчёт по revision_hints + diff_audit
**Опус:** независимо откроет `validators_on_draft.json` + `revision_diff_audit.json`:
- ✅ revision_hints count > 0 (если в draft есть issues)
- ✅ error-level hints все applied (per writing_notes.rule13_*)
- ✅ unauthorized_changes count < threshold
- ✅ revision_failed=false

---

## История

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-18 | `new` | Опус |
