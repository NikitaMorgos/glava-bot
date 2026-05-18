# Задача 046b: Stage 3 runner — auto_rewrite ДО style_checks (порядок шагов)

**Статус:** `new`
**Номер:** 046b
**Автор:** Опус (роль архитектор+продакт)
**Дата создания:** 2026-05-17
**Тип:** `cco-скрипт` (минор fix Stage 3 runner)
**Batch:** v60 sprint
**Связано:** task 046 (epilogue auto-rewrite); diagnostic v59: epilogue_rewrite_log удалил 2 предложения, но style_checks показал 4 errors на тех же предложениях

---

## Контекст

В v59 заметная несостыковка:
- `epilogue_rewrite_log.json`: удалено 2 предложения («Она была человеком своего времени», «Её жизнь была наполнена трудом и служением людям»)
- `style_checks.json`: 4 errors включая ту же «жизнь была наполнена» (которая уже удалена)

**Корень:** в Stage 3 runner порядок шагов:
- ✅ Правильно: `enforce_epilogue_stop_phrases` (auto-rewrite) → потом `validate_epilogue_stop_phrases` (check)
- ❌ В v59: `validate_epilogue_stop_phrases` сначала → потом `enforce_epilogue_stop_phrases`

В результате style_checks v59 показывает старые ошибки до rewrite. Финальный текст уже чище.

## Universality check

- [x] Промпт без конкретики — n/a (это код runner-а, не промпт)
- [x] Subject-specific — n/a (порядок шагов универсальный)
- [x] Алгоритм generic — да, порядок Stage 3 одинаков для всех subjects
- [x] Subject-replacement test — для Корольковой/Дмитриева тот же порядок ✅

---

## Спек

### Что нужно изменить

**`scripts/test_stage3.py`** (или соответствующий runner): пересортировать post-LE цепочку:

```python
# v59 (incorrect order):
preserve_chapter_structural_fields(book, before_le)
apply_relation_overrides(fact_map, overrides)
enforce_bio_data_completeness(book, fact_map)
filter_bio_data_family_by_relation_whitelist(book)
validate_bio_data_required_fields(...)
enforce_persona_notes(book, persona_notes)
normalize_book_topo(book, gazeteer)
# Validators (НЕЛЬЗЯ ЗАПУСКАТЬ ДО auto_rewrite):
validate_epilogue_stop_phrases(book, stop_list)
validate_narrative_stop_phrases(book, stop_list)
validate_awkward_formulation(book)
validate_chronological_consistency(book, fact_map)
validate_discourse_markers(book, fact_map, config)
validate_pin_list_coverage(book, pin_list)
validate_pin_list_depth(book, pin_list)
enforce_paspart_format(book)
enforce_epilogue_stop_phrases(book, mapping)  # ← TOO LATE — validators already ran on dirty text
```

**v60 (correct order):**

```python
preserve_chapter_structural_fields(book, before_le)
apply_relation_overrides(fact_map, overrides)
enforce_bio_data_completeness(book, fact_map)
filter_bio_data_family_by_relation_whitelist(book)
validate_bio_data_required_fields(...)
enforce_persona_notes(book, persona_notes)
normalize_book_topo(book, gazeteer)
enforce_paspart_format(book)              # auto-rewrite paspart
enforce_epilogue_stop_phrases(book, ...)  # auto-rewrite epilogue ← MOVED EARLIER
# Validators (теперь на cleaned text):
validate_epilogue_stop_phrases(book, stop_list)
validate_narrative_stop_phrases(book, stop_list)
validate_awkward_formulation(book)
validate_chronological_consistency(book, fact_map)
validate_discourse_markers(book, fact_map, config)
validate_pin_list_coverage(book, pin_list)
validate_pin_list_depth(book, pin_list)
```

**Принцип:** все `enforce_*` (auto-rewrite) — **до** всех `validate_*` (check). Validators работают на финальном тексте.

### Какой результат ожидается

В v60 `style_checks.json` errors_count соответствует реально оставшимся проблемам после auto_rewrite (не до).

### Как проверить

1. **Integration на v59 book_FINAL_stage3** (re-run Stage 3 post-LE chain):
   - Сравнить: после reorder → style_checks errors = 0 для epilogue stop_phrases которые auto_rewrite покрывает

2. **Verified-on-run** v60:
   - `epilogue_rewrite_log.json` показывает удаления
   - `style_checks.json` НЕ показывает ошибки на удалённых фразах

---

## Ограничения

- [ ] НЕ менять логику отдельных функций — только порядок вызовов
- [ ] Idempotent
- [ ] Universal (для всех subjects)

---

## Dev Review

**Статус:** ожидает
**[TECH]** — нет
**[PRODUCT]** — нет
**Сложность:** `xs` (<1 ч)
**Риск:** `low`

---

## История

| Дата | Статус | Кто |
|---|---|---|
| 2026-05-17 | `new` | Опус |
