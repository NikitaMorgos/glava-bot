# Задача 046c: Epilogue auto-rewrite regex — поддержка intermediate words

**Статус:** `new`
**Номер:** 046c
**Автор:** Опус (роль архитектор+продакт)
**Дата создания:** 2026-05-17
**Тип:** `cco-скрипт` (минор regex fix)
**Batch:** v61 sprint (Вариант 1)
**Связано:** task 046 (epilogue auto-rewrite); diagnostic v60: «путь от сироты ИЗ украинского села до уважаемой» detected style_checks но not deleted auto_rewrite

---

## Контекст

В v60 `epilogue_rewrite_mapping.json` v2 (task 043c) содержит правило:

```json
{
  "category": "path_from_X_to_Y",
  "pattern_regex": "(прош\\w+|прокат\\w+|преодолел\\w+)\\s+путь\\s+от\\s+\\w+\\s+(до|к)\\s+\\w+",
  "action": "delete_sentence"
}
```

В тексте epilogue v60:
> «Валентина Ивановна прошла путь от сироты **из украинского села** до уважаемой медицинской сестры в подмосковном Химинституте.»

Regex требует `\w+ (один word) + (до|к) + \w+` — но в реальности между «сироты» и «до» есть **intermediate words** («из украинского села»). Match fails → auto_rewrite не сработал → style_checks v60 показал 1 error.

**Корень:** regex не учитывает intermediate clauses между «от X» и «до Y».

## Universality check

- [x] Промпт без конкретики — regex в JSON конфиге, не в промпте
- [x] Subject-specific — generic русские pattern, без Каракулиноспецифики
- [x] Алгоритм generic — regex matching
- [x] Subject-replacement test — «прошёл путь от Y из деревни до W» — другой subject, same pattern ✅

---

## Спек

### Что нужно изменить

**`collab/context/epilogue_rewrite_mapping.json`** — расширить pattern для категории `path_from_X_to_Y`:

```json
{
  "category": "path_from_X_to_Y",
  "pattern_regex": "(прош\\w+|прокат\\w+|преодолел\\w+)\\s+путь\\s+от\\s+\\S+(\\s+[^.!?]*?)?\\s+(до|к)\\s+\\S+",
  "action": "delete_sentence",
  "reason": "стандартная риторическая фигура без конкретики (поддержка intermediate words)"
}
```

**Ключевое изменение:** `\w+` → `\S+(\s+[^.!?]*?)?` — позволяет intermediate words между «от X» и «до Y» (до конца предложения).

`[^.!?]*?` — non-greedy match любых символов кроме конца предложения. Это предотвращает overmatching через границы предложений.

### Какой результат ожидается

В v61 epilogue:
- ✅ «прошла путь от сироты из украинского села до уважаемой медицинской сестры» → match → delete_sentence
- ✅ «прошёл путь от подростка к директору завода» → match → delete (нет intermediate, всё равно работает)
- ✅ «преодолела путь от деревни к городу» → match
- ❌ «прошла путь длиной в семьдесят лет» → НЕ match (нет «до|к»)

### Как проверить

1. **Unit-тесты** `tests/test_epilogue_rewrite_intermediate.py`:
   - «прошла путь от сироты из X до уважаемой Y» → match
   - «прошёл путь от A к B» (без intermediate) → match (backward compat)
   - «прошла путь длиной в годы» → НЕ match
   - Idempotent

2. **Integration на v60 epilogue:**
   - Текст «прошла путь от сироты из украинского села до уважаемой» → правило применяется → предложение удалено

3. **Verified-on-run** v61:
   - epilogue_rewrite_log содержит удаление «путь от сироты»
   - style_checks epilogue stop phrases errors = 0 (вместо 1 в v60)

---

## Ограничения

- [ ] Generic regex, без subject-specific
- [ ] Non-greedy match `[^.!?]*?` — не выходит за границы предложения
- [ ] Idempotent
- [ ] Universal

---

## Dev Review

**Статус:** ожидает
**[TECH]** — `\S+(\s+[^.!?]*?)?` — нужны тесты на edge cases: пустой intermediate, много intermediate words, окончание предложения внутри clause
**[PRODUCT]** — нет
**Сложность:** `xs` (<1 ч)
**Риск:** `low`

---

## История

| Дата | Статус | Кто |
|---|---|---|
| 2026-05-17 | `new` | Опус |
