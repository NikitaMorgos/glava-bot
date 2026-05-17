# Задача 046: Epilogue auto-rewrite — generic mapping stop-phrase → нейтральный аналог

**Статус:** `new`
**Номер:** 046
**Автор:** Опус (роль архитектор+продакт)
**Дата создания:** 2026-05-17
**Тип:** `cco-скрипт`
**Batch:** 2-fix
**Связано:** task 043 (validate-only stop-phrases); diagnostic v58: GW v2.19 ЗАПРЕТ 13 не выучил, GW снова пишет «человеком своего времени», «жизнь была наполнена»

---

## Контекст

task 043 — validate-only без auto-fix (я сам так зафиксировал в spec'е: «не auto-replace, стиль решается GW»). GW v2.19 ЗАПРЕТ 13 (epilogue antitriggers) **не работает** — v58 epilogue имеет:
- «прошла путь от сироты времён голодомора до уважаемой медсестры»
- «жизнь была наполнена трудом и заботой о близких»
- «Она была человеком своего времени»
- «её традиция «посидеть на дорожку» живёт в семье» (явная фантазия от GW)

Это **подкрепляет принцип «промпт расслабляется, скрипт держит надёжнее»**. Скрипт **auto-rewrite** — последний рубеж.

---

## Спек

### Что нужно изменить

**1. `epilogue_rewrite_mapping.json`** (generic, не subject-specific):

```json
{
  "version": "v1",
  "rules": [
    {
      "category": "person_of_their_time",
      "pattern_regex": "\\b[Бб]ыл\\w*\\s+человек\\w{0,3}\\s+своего\\s+времени[.,]?",
      "action": "delete_sentence_if_starts_with_match",
      "reason": "клише обобщения эпохи"
    },
    {
      "category": "path_from_X_to_Y",
      "pattern_regex": "(прош\\w+|прокат\\w+|преодолел\\w+)\\s+путь\\s+от\\s+\\w+\\s+(до|к)\\s+\\w+",
      "action": "delete_sentence",
      "reason": "стандартная риторическая фигура без конкретики"
    },
    {
      "category": "life_filled_with_X",
      "pattern_regex": "(жизн\\w+|жил\\w+)\\s+был\\w+\\s+наполнен\\w+\\s+\\w+",
      "action": "delete_sentence",
      "reason": "пафосное обобщение без конкретики"
    },
    {
      "category": "passed_to_generations",
      "pattern_regex": "передал\\w+\\s+(следующ\\w+\\s+поколен|следующ\\w+\\s+поколения|потомк)",
      "action": "delete_sentence",
      "reason": "клише межпоколенческой передачи"
    },
    {
      "category": "tradition_lives_in_family",
      "pattern_regex": "(традиция|обычай)\\s+«?[^»]+»?\\s+(жив|живёт|остал\\w+)\\s+(в\\s+семье|с\\s+нами|в\\s+памяти)",
      "action": "delete_sentence",
      "reason": "часто фантазия про продолжение традиции без подтверждения в источнике"
    }
  ],
  "applies_to_chapter_ids": ["epilogue"]
}
```

**2. Функция `enforce_epilogue_stop_phrases(book, mapping) -> book`** в `pipeline_utils.py`:
- Для каждого правила:
  - Find matches в `epilogue.content` (или `paragraphs[].text`)
  - `action: delete_sentence` — удалить **всё предложение** содержащее match (разбивает по `[.!?]` + space + Capital)
  - `action: delete_sentence_if_starts_with_match` — удалить только если match в начале предложения
  - `action: replace_with` (если есть) — заменить match на fallback_replacement
- Возвращает modified book + лог изменений `<run>_epilogue_rewrite_log.json`
- Idempotent

**3. Интеграция в Stage 3 runner**:
- После `validate_epilogue_stop_phrases` (existing task 043) + `validate_narrative_stop_phrases` (task 043b):
  - `enforce_epilogue_stop_phrases(book, mapping)` — auto-fix только в epilogue (категория safer)
- Для нарратива (ch_01-04) — **только flag**, не enforce (риск удаления контента)

### Какой результат ожидается

В v59 epilogue:
- ✅ «Она была человеком своего времени» — удалено (полное предложение)
- ✅ «прошла путь от сироты ... до уважаемой медсестры» — удалено
- ✅ «жизнь была наполнена трудом и заботой» — удалено
- ✅ «её традиция «посидеть на дорожку» живёт в семье» — удалено

В epilogue_rewrite_log.json:
- 4+ удалённых предложений с pattern category

### Как проверить

1. **Unit-тесты** `tests/test_epilogue_auto_rewrite.py`:
   - «Она была человеком своего времени.» → удалено
   - «Прошла путь от сироты до уважаемой медсестры.» → удалено
   - В тексте «Это был человек твёрдых принципов» (не «своего времени») → НЕ удалено
   - Idempotent (повтор не меняет ничего)

2. **Integration** на v58c epilogue:
   - 4 stop phrases → 4 sentences deleted
   - epilogue остаётся coherent (не разрывается mid-thought)

3. **Verified-on-run** v59:
   - Открыть epilogue.content — grep по stop-list → 0 hits
   - Длина epilogue после rewrite ≥600 chars (не пустой)

---

## Ограничения

- [ ] Только в epilogue — НЕ auto-edit нарратив (риск удаления полезного контента)
- [ ] Generic patterns — universal, без subject-specific терминов в mapping
- [ ] Idempotent
- [ ] Если после удаления предложений epilogue < 400 chars — flag для human review

---

## Dev Review

**Статус:** ожидает

**[TECH]** — пред-резолв: разбивка по предложениям через простой regex `[.!?]\s+(?=[А-ЯA-Z])`; для сложных конструкций (например с восклицанием в середине) могут быть edge cases — приемлемы.

**[PRODUCT]** — нет.

**Сложность:** `xs` (<1 ч)
**Риск:** `low` (только epilogue, safe scope)

---

## История

| Дата | Статус | Кто |
|---|---|---|
| 2026-05-17 | `new` | Опус |
