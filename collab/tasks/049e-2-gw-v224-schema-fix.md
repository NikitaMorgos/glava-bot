# Задача 049e-2: GW v2.23 → v2.24 — schema fix rule13_revision_applied как list

**Статус:** `new`
**Номер:** 049e-2
**Автор:** Опус
**Дата создания:** 2026-05-19
**Тип:** `промпт` GW (bug fix existing rule, не новое правило)
**Sprint:** v65 (bugfix v64)
**Связано:** task 049e (GW v2.23 ПРАВИЛО 13); v64 verify — GW вернул `writing_notes.revision_applied: "string"`, spec требовал `rule13_revision_applied: [list]`

---

## Контекст

В v64 GW v2.23 при revision pass записал в writing_notes:
```json
"revision_applied": "Исправлен paragraph p_02_011 согласно revision_hints h_001: убрана фраза о привилегии жён военных"
```

Spec ПРАВИЛА 13 (task 049e) требовал:
```yaml
rule13_revision_applied: [
  {"hint_id": "h_001", "action": "rewritten" | "deleted" | "skipped",
   "reason": "<если skipped — почему>", "diff": "<short before→after>"}
]
```

**Различия:**
- Key: `revision_applied` (GW) vs `rule13_revision_applied` (spec)
- Type: string (GW) vs list of dicts (spec)
- Structure: free-form (GW) vs structured (spec)

Это **partial compliance** — GW понял идею, не понял схему. revision_diff_audit ищет structured key, не находит, отчитывает `skipped`.

**Корневая причина:** в финальном тексте ПРАВИЛА 13 v2.23 я писал «В writing_notes обязательно: ...» список — но **не enforce'нул schema через explicit JSON template + 1-2 примера output**. LLM прочитал namarrative description, не точную schema, и интерпретировал по-своему.

---

## Pre-sprint checklist

- [x] Stocktake актуален
- [x] Critical reading — v64 book_REVISED writing_notes прочитан, schema mismatch verified
- [x] Universality построчно — этот fix без subject-specific examples (см. ниже)
- [x] Защита подключена — да, key unification для diff audit (049f-2)
- [x] Прогон раздельный — bugfix не новое правило; combined с v65 OK per Правило 7
- [x] Класс багов — «free-form output вместо structured schema» (generic class)
- [x] Скрипт-first — но это GW prompt fix, schema enforcement требует prompt change (alternative нет)

---

## Спек

### 1. Промпт-fix в существующем ПРАВИЛЕ 13 v2.23 → v2.24

**Файл:** `prompts/03_ghostwriter_v2.24.md` (новый, копия v2.23 + изменения).

**Шапка обновляется:**
```
## Версия: v2.24 (2026-05-19, Opus, task 049e-2, v65 bugfix)
### Изменения v2.24: 2 bug fixes existing правил (НЕ новые правила):
### 1. ПРАВИЛО 13 schema fix — rule13_revision_applied как list of dicts (см. ниже)
### 2. ПРАВИЛО 2 universality fix — replace hardcoded characteristic words examples на placeholders (см. task 049h)
###
### v2.24 не добавляет новых правил per Правило 6 — это hot-fix реализации existing v2.23.
```

**Изменение в ПРАВИЛЕ 13 (раздел PROOF OF ATTENTION):**

Заменить текущий описательный блок на **explicit JSON template + примеры**:

```
══════════════════════════════════════════════════════════════════
PROOF OF ATTENTION — обязательная schema при revision pass
══════════════════════════════════════════════════════════════════

В `out_book.writing_notes` ОБЯЗАТЕЛЬНО добавить поле
`rule13_revision_applied` СТРОГО как list объектов (НЕ string,
НЕ free-form description, НЕ объект-словарь):

```json
{
  "writing_notes": {
    "rule13_revision_applied": [
      {
        "hint_id": "h_001",
        "action": "rewritten",
        "diff_summary": "[краткое описание изменения — что убрано/добавлено/переписано]"
      },
      {
        "hint_id": "h_002",
        "action": "deleted",
        "diff_summary": "[удалено sentence: '...']"
      },
      {
        "hint_id": "h_003",
        "action": "skipped",
        "reason": "[если skipped — почему: legitimate fact / would break coherence / etc.]"
      }
    ],
    "rule13_hints_received": 3,
    "rule13_errors_applied": 2,
    "rule13_warnings_applied": 0,
    "rule13_revision_failed": false
  }
}
```

Допустимые значения `action`:
- `rewritten` — sentence/paragraph переписан
- `deleted` — sentence удалён целиком
- `skipped` — hint проигнорирован (только для warning-level либо когда apply
  нарушает legitimate content; reason обязательно)

Поля `rule13_*` — точные имена, не переименовывать. Аудит ищет
именно эти ключи; любые альтернативы (`revision_applied`, `applied`,
`rule13_changes`, etc.) НЕ распознаются.

⛔ ПЛОХО (v64 ошибка):
```json
{"writing_notes": {"revision_applied": "Исправлен paragraph p_02_011..."}}
```
↑ wrong key + string type — audit не находит

✅ ХОРОШО:
```json
{"writing_notes": {
  "rule13_revision_applied": [
    {"hint_id": "h_001", "action": "rewritten",
     "diff_summary": "убрана фраза 'привилегия жён военных'"}
  ],
  "rule13_hints_received": 1,
  "rule13_errors_applied": 1,
  "rule13_warnings_applied": 0,
  "rule13_revision_failed": false
}}
```

══════════════════════════════════════════════════════════════════

REVISION_FAILED FLAG

Установить `rule13_revision_failed: true` ТОЛЬКО когда:
- Есть hint с `must_apply: true` (severity=error) который НЕ был
  applied и НЕ записан как skipped с reason
- Если все must_apply hints либо applied либо явно skipped с reason —
  rule13_revision_failed: false

Audit (validator) проверяет: если revision_failed=true → STOP, Опус
review. Не silently proceed.

══════════════════════════════════════════════════════════════════
```

### 2. Применение

`pipeline_config.json.ghostwriter.prompt_file` → `"03_ghostwriter_v2.24.md"`.

`_notes` обновить: «v2.24 (2026-05-19, task 049e-2 + 049h, v65 bugfix sprint): hot-fix ПРАВИЛО 13 schema (rule13_revision_applied как list) + ПРАВИЛО 2 universality (replace hardcoded чармин words → placeholders + pin-list input wire). Per Правило 6 — это bug fixes existing правил, не новые правила.»

### 3. Schema validation в pipeline

В `_v64_revision_pass.py` (либо аналог) добавить **schema validation** сразу после GW response:

```python
def validate_rule13_schema(book_revised):
    """Проверка что GW следует ПРАВИЛО 13 schema."""
    wn = book_revised.get("writing_notes", {})
    if not isinstance(wn, dict):
        raise SchemaError("writing_notes должен быть dict")
    rules_applied = wn.get("rule13_revision_applied")
    if not isinstance(rules_applied, list):
        raise SchemaError(
            f"rule13_revision_applied должен быть list, получили: {type(rules_applied)}. "
            f"Если GW вернул 'revision_applied' (singular string) — это v2.23 bug, "
            f"требуется retry с v2.24 schema reminder."
        )
    required_int_fields = ["rule13_hints_received", "rule13_errors_applied", "rule13_warnings_applied"]
    for f in required_int_fields:
        if not isinstance(wn.get(f), int):
            raise SchemaError(f"{f} должен быть int")
    if not isinstance(wn.get("rule13_revision_failed"), bool):
        raise SchemaError("rule13_revision_failed должен быть bool")
    return True
```

Если validation fails — отчёт в Опуса, не proceed.

### 4. Тесты

`tests/test_gw_v224_rule13_schema.py`:
- Valid output → validation pass
- Missing `rule13_revision_applied` → SchemaError
- `rule13_revision_applied` как string → SchemaError (v64 reproduction)
- `rule13_revision_failed` как string «false» → SchemaError (должен быть bool)
- Empty list `rule13_revision_applied: []` + 0 hints received → OK

---

## Universality check (КРИТИЧНО — Правило 4)

В финальном тексте ПРАВИЛА 13 v2.24:
- ✅ Примеры используют generic `h_001`, `h_002`, `[краткое описание]` — нет Каракулино-specific
- ✅ Wrong-example «убрана фраза 'привилегия жён военных'» — это **explicit example v64 bug** (приемлемо для документации причины почему правило важно)
- ✅ Subject-replacement test: для Корольковой schema работает без правок ✅

**Grep test перед commit'ом** (per memory `architect_universality_check.md`):
```
grep -in "Каракулин\|Татьян\|Валентин\|Химинститут\|выковырив\|Молдави\|1946 год" prompts/03_ghostwriter_v2.24.md
```
Если в финальном тексте промпта (не в шапке-истории) есть match — переделать. Существующее «привилегия жён военных» в bug example — приемлемо (это generic пример GW поведения, не subject reference).

---

## Ограничения

- [ ] Один промпт-bump v2.23 → v2.24 — bug fixes existing rules (Правило 6 OK, не новые правила)
- [ ] Schema strict — list, не string; точные key names
- [ ] Schema validation в коде после GW response
- [ ] Universality preserved
- [ ] Combined с task 049h в v2.24 (оба — bug fixes existing rules)

---

## Dev Review

**Статус:** ожидает

**[TECH]** — pre-answer от Опуса:
- Файл: `prompts/03_ghostwriter_v2.24.md` (новый, копия v2.23 + 2 fixes: ПРАВИЛО 13 schema + ПРАВИЛО 2 universality)
- Schema validation в `_v64_revision_pass.py` / соответствующий runner
- `pipeline_config.json.ghostwriter.prompt_file` → v2.24
- Schema enforcement через `validate_rule13_schema` после GW response

**[PRODUCT]** — нет

**Сложность:** `xs` (<1 ч prompt edit + schema validator + tests)
**Риск:** `low` (bug fix existing rule, не новая логика)

---

## Verified-on-run v65

**Cursor:** [после v65 прогона]
**Опус:** независимо проверит:
- `book_REVISED.json` (или `book_FINAL.json` после task 049g LE preserve) содержит `writing_notes.rule13_revision_applied` как **list of dicts**
- Каждый dict имеет `hint_id`, `action`, `diff_summary` либо `reason`
- `rule13_hints_received`, `rule13_errors_applied`, `rule13_warnings_applied` — int
- `rule13_revision_failed` — bool
- `revision_diff_audit.json` `applied` != [] (если были hints)

---

## История

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-19 | `new` | Опус |
