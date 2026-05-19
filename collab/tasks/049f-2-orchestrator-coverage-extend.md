# Задача 049f-2: Orchestrator coverage extend — все 10 валидаторов + warnings передавать в hints

**Статус:** `new`
**Номер:** 049f-2
**Автор:** Опус
**Дата создания:** 2026-05-19
**Тип:** `cco-скрипт` (extend существующего модуля)
**Sprint:** v65 (bugfix v64)
**Связано:** task 049f v64 (revision_hints orchestrator); v64 verify revealed 4 bugs реализации; принципы Правило 8 (каждая защита подключена к лечению)

---

## Контекст

В v64 реализация orchestrator показала **2 серьёзных gap'а**:

1. **Только 6 из 10+ валидаторов подключены** к сбору `revision_hints`. В `validators_on_draft.json` есть:
   - chronology_check ✅
   - narrative_truism ✅
   - narrative_stop_phrases ✅
   - personal_historical_voice ✅
   - epilogue_quote_density ✅
   - entity_substitution ✅

   **Отсутствуют (важные):**
   - `pin_list_depth` — нашёл 4 errors в финальных validators, ни одного в hints
   - `discourse_markers` — ch_02=0/8 (хуже чем v63), 0 hints
   - `epilogue_stop_phrases` — 3 errors в финальных validators, 0 hints
   - `timeline_anchors` — обычно clean, но должен быть подключён
   - `anti_facts` — был в v62a, не подключён в v64 orchestrator

2. **Warnings отфильтрованы** в hints. В `revision_hints.json` только **1 hint** (chronology error). Все warning-level findings отсечены:
   - 3 personal_historical_voice warnings (ch_02/03/04) — потеряны
   - 1 epilogue_quote_density warning — потеряна
   - Все potential narrative_truism warnings (если бы были) — потерялись бы

**Эффект v64:** GW получил только 1 hint → переписал 1 paragraph → все остальные блокеры (depth, discourse, voice, density) остались. Revision loop архитектурно работает, но coverage 10% от потенциала.

---

## Pre-sprint checklist (Правила 3+4+7+8)

- [x] **Stocktake актуален** — `stocktake-2026-05-18-v60-v63.md` свежий
- [x] **Critical reading артефактов** — открыты v64 text_FULL.md, validators_on_draft.json, revision_hints.json, revision_diff_audit.json
- [x] **Universality построчно** — этот task scripted, нет промпт-текста для grep
- [x] **Защита подключена к лечению** — это и есть закрытие gap'а «detect → fix»; closure для всех валидаторов
- [x] **Прогон раздельный** — bugfix реализации v64, не новое правило; v65 = combined bugfix sprint OK per Правило 7
- [x] **Класс багов, не симптом** — gap «detect без fix» — это **класс архитектурный**, не один эпизод
- [x] **Скрипт-first** — это и есть scripted (orchestrator)

---

## Спек

### 1. Перечень validators которые orchestrator должен подключить

В `pipeline_utils/revision_orchestrator.py` (или соответствующее место) — `collect_revision_hints` обходит **все** валидаторы Stage 2 после first pass:

```python
def collect_revision_hints(book_draft, validator_outputs, config=None):
    """Собрать revision_hints из ВСЕХ validator outputs.

    Источники (все обязательны, не subset):
    - chronology_check
    - pin_list_depth
    - discourse_markers
    - narrative_stop_phrases (включая narrative_truism под этим именем)
    - anti_facts
    - epilogue_stop_phrases
    - epilogue_quote_density
    - personal_historical_voice
    - timeline_anchors
    - entity_substitution
    - + любой новый валидатор v65 (cross_paragraph_duplication, historical_notes_distribution)
    """
    ...
```

Если какой-то validator не запустился — warning в лог orchestrator'а, **не** silent skip. Это критично для diagnostic (мы не должны не знать что валидатор не выполнился).

### 2. Warning-level — передавать в hints, не фильтровать

Текущая логика (v64): только `severity=error` + `must_apply=true` → hint. **Изменение:** все findings → hints, с `must_apply` = (severity == "error").

GW в ПРАВИЛЕ 13 v2.23 уже различает:
- `must_apply: true` (severity=error) — обязан выполнить
- `must_apply: false` (severity=warning) — выполнить если возможно без потери fact

**Бенефит:** warnings (например personal_historical_voice below_threshold, discourse_markers below_threshold, epilogue_density too_many_generic) попадают в GW input. GW при revision может добавить voice markers / переписать pathos / сжать density — даже если не обязан.

### 3. Suggestion для каждой category

Для **всех** validator categories в `_build_suggestion()` должна быть конкретная инструкция. v64 имел defaults типа «Переписать или удалить flagged sentence» — слишком общо.

Per-validator расширение (минимум):

```python
def _build_suggestion(validator, issue):
    cat = issue.get("category") or issue.get("type")

    # pin_list_depth — было 4 errors в v64 без hint
    if validator == "pin_list_depth":
        return (
            f"Развернуть эпизод [{issue.get('episode_id')}] на ≥{issue.get('min_required', 3)} "
            f"sentences. Сейчас {issue.get('actual_sentences')}. Структура: setup (год+место+кто) → "
            f"action (что произошло) → деталь из source_quote или последствие."
        )

    # discourse_markers — было ch_02=0/8 в v64
    if validator == "discourse_markers" and cat == "below_threshold":
        return (
            f"Добавить ≥{issue['expected'] - issue['found']} discourse markers в {issue.get('chapter_id')}. "
            f"Patterns: '[rapporteur] вспоминает', 'по словам [rapporteur]', "
            f"'как помнит [родственное_отношение]'. Использовать имена из discourse_markers config."
        )

    # epilogue_stop_phrases — было 3 errors в v64
    if validator == "epilogue_stop_phrases":
        return f"Удалить epilogue stop-фразу: '{issue.get('phrase', '...')}'."

    # personal_historical_voice — v64 warnings не передавались
    if validator == "personal_historical_voice":
        # уже имеет suggestion в validator output — оставить как есть
        return issue.get("suggestion", "Добавить personal-historical voice anchors из pin-list.")

    # epilogue_quote_density
    if validator == "epilogue_quote_density":
        return "Снизить density cited phrases в epilogue. Распределить характерные слова по ch_02/ch_03/ch_04, в epilogue оставить spokoyno."

    # timeline_anchors
    if validator == "timeline_anchors" and cat == "anchor_absorbed":
        return f"Период '{issue.get('anchor_id')}' поглощён другим. Разделить как отдельный block в ch_01 markdown."

    # entity_substitution
    if validator == "entity_substitution":
        return f"Replace '{issue.get('from')}' → '{issue.get('to')}' в snippet (на {issue.get('chapter_id')})."

    # anti_facts
    if validator == "anti_facts":
        return f"Не объединять '{issue.get('item_A')}' с '{issue.get('item_B')}' в одном paragraph (в источнике отдельны)."

    # narrative_truism — task 043h
    if validator == "narrative_truism":
        return issue.get("suggestion", "delete_sentence")

    # narrative_stop_phrases (Class 1/6/11/17)
    if validator == "narrative_stop_phrases":
        return issue.get("suggestion") or "Переписать без causal claim / generic listing / truism."

    # NEW v65 валидаторы
    if validator == "cross_paragraph_duplication":  # task 048g
        return f"Дословный повтор paragraph из {issue.get('original_chapter_id')}. Удалить дубликат либо переписать со ссылкой."

    if validator == "historical_notes_distribution":  # task 046f
        return f"Добавить historical_note inline в {issue.get('chapter_id')} (текущий count {issue.get('found')}, нужно ≥{issue.get('expected')})."

    return issue.get("suggestion") or "Переписать или удалить flagged sentence."
```

### 4. Audit unauthorized_changes — расширить

Сейчас audit сравнивает draft vs revision по диффу. Если изменения за пределами `revision_hints.snippet` — warning. v64 показал `unauthorized_changes=1` (acceptable, но без explanation что именно).

Доработка: для каждого unauthorized change — добавить context (какая глава, какие 50 chars до/после, чтобы было понятно при review).

### 5. Тесты

`tests/test_orchestrator_coverage.py` (новый):

- Test: orchestrator принимает validator_outputs со всеми 10+ источниками → производит hints для каждого
- Test: warning-level finding → hint с `must_apply=false`
- Test: error-level finding → hint с `must_apply=true`
- Test: missing validator (orchestrator не получил output) → warning в лог, hint count корректен (без falling)
- Test: per-validator suggestion content проверяется (snapshot для каждой category)

---

## Universality check

- [x] Промпт — n/a (scripted orchestrator)
- [x] Subject-specific — n/a (orchestrator generic)
- [x] Алгоритм generic — работает с любым subject
- [x] Subject-replacement test — для Корольковой validator outputs тоже generic, orchestrator работает без правок ✅

---

## Ограничения

- [ ] Все 10+ валидаторов подключены явно (не auto-discovery — explicit list для предсказуемости)
- [ ] Warning-level передаётся с `must_apply=false`, GW сам решает
- [ ] Idempotent
- [ ] Generic suggestions per category
- [ ] Missing validator = warning в лог, не silent skip
- [ ] Audit unauthorized_changes расширен context'ом

---

## Dev Review

**Статус:** ожидает

**[TECH]** — pre-answer от Опуса:
- Extension существующего `pipeline_utils/revision_orchestrator.py` (либо часть pipeline_utils.py)
- Explicit validator list в `_KNOWN_VALIDATORS = [...]` constant
- Backward compatible с v64 orchestrator API
- Suggestion mapping расширен per-validator (не generic fallback)

**[PRODUCT]** — нет

**Сложность:** `s` (1-3 ч — extend существующего модуля)
**Риск:** `low` (bugfix реализации, не новая архитектура)

---

## Verified-on-run v65

**Cursor:** [после v65 прогона]
**Опус:** независимо откроет:
- `revision_hints.json` — count >= 5 hints (vs v64 = 1)
- Каждый из 10 валидаторов представлен в hints либо явно log'нут как «no issues»
- pin_list_depth, discourse_markers, epilogue_stop_phrases — присутствуют в hints
- Warning-level hints видны с `must_apply=false`

---

## История

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-19 | `new` | Опус |
