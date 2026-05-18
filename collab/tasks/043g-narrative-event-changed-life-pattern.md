# Задача 043g: Narrative пафос — patterns «событие, которое изменило» + «типичной для поколения»

**Статус:** `new`
**Номер:** 043g
**Автор:** Опус (роль архитектор+продакт)
**Дата создания:** 2026-05-18
**Тип:** конфиг + минор скрипт
**Sprint:** v63
**Связано:** task 043b (lemmatize stop-phrases); task 043c (categorical patterns); task 043d (Class 1 confabulations); Class 6 narrative пафос; v62a regression — два новых pattern'а в ch_02 и epilogue

---

## Контекст

В v62a Никитин live review показал два **новых** patterns Class 6 narrative пафос:

### Pattern A — «событие, которое изменило» (ch_02)

```
В 1961 году произошло событие, которое изменило семейную жизнь:
Валерий не захотел возвращаться после летних каникул в интернат в Венгрии
и остался с тётей Шурой в Кирсанове Тамбовской области.
```

Это **тот же класс** что v59 «специальность, которая определила всю её дальнейшую жизнь» (закрыт task 043d): **abstract framing-фраза** перед конкретным событием. Subjective causal claim, которого нет в transcripts.

### Pattern B — «типичной для поколения» (epilogue)

```
Её жизнь была типичной для поколения, прошедшего через войну
и восстановление страны. Но в этой типичности была своя уникальность —
стойкость «оловянного солдатика», который не сгибается под ударами судьбы.
```

«Типичной для X поколения» — generic biographical filler. Не из transcripts.

**Класс:** Class 6 (epilogue/intro пафосные обобщения), расширение на **narrative chapters** через generic categorical patterns.

---

## Universality check

- [x] Промпт — n/a, patterns в конфиге
- [x] Subject-specific — generic patterns, без имён/дат
- [x] Алгоритм generic — regex lemmatize-aware, scope per chapter
- [x] Subject-replacement test — для Корольковой/Дмитриева аналогичные клише поймает без правок ✅

**Trap warning:** конкретные эпизоды Валерия 1961 и epilogue Каракулиной — это **симптомы класса**. Класс = «framing-фраза перед event» + «типичность поколения». Spec строится на patterns, не на конкретных строках.

---

## Спек

### Что нужно изменить

**`collab/context/narrative_stop_phrases.json`** — extend `generic_categorical_patterns`:

```json
{
  "category": "event_that_changed_life",
  "pattern": "(произошл\\w+|случил\\w+|стал\\w+)\\s+(событи\\w+|момент\\w+|переломн\\w+\\s+момент\\w+)\\W{1,30}котор\\w+\\s+(измен\\w+|перевернул\\w+|повлия\\w+|определ\\w+)",
  "scope": ["ch_02", "ch_03", "ch_04"],
  "severity": "warning",
  "reason": "abstract framing перед конкретным фактом; добавляет causal claim без подтверждения в источнике"
},
{
  "category": "typical_for_generation",
  "pattern": "\\b(тип\\w+|обычн\\w+|характерн\\w+)\\s+(для\\s+)?(её|его|их|такого\\s+)?поколени\\w+",
  "scope": ["epilogue", "ch_02", "ch_03"],
  "severity": "warning",
  "reason": "generic biographical filler «типичная для поколения»; снижает индивидуальность субъекта"
},
{
  "category": "in_this_typicality_uniqueness",
  "pattern": "\\bв\\s+этой\\s+(типичност\\w+|обычност\\w+|повседневност\\w+)\\s+был\\w+\\s+(сво\\w+\\s+)?уникальност\\w+",
  "scope": ["epilogue"],
  "severity": "error",
  "reason": "клише «в типичности своя уникальность» — пустая риторическая фигура"
}
```

**`collab/context/epilogue_rewrite_mapping.json`** — extend для auto-rewrite (task 046):

```json
{
  "category": "typical_for_generation",
  "pattern_regex": "(её|его)\\s+жизнь\\s+был\\w+\\s+тип\\w+\\s+для\\s+\\w+\\s+поколени\\w+[^.]*\\.",
  "action": "delete_sentence"
},
{
  "category": "in_this_typicality_uniqueness",
  "pattern_regex": "\\bНо\\s+в\\s+этой\\s+(типичност\\w+|обычност\\w+)[^.]*\\.",
  "action": "delete_sentence"
}
```

**Note:** `event_that_changed_life` — **только flag warning**, не enforce delete. GW необходимо переписать предложение без framing-фразы — но автоматическое удаление полного sentence может потерять conкретный fact (Валерий 1961). Подход — **flag для GW revision pass** или ручной правки.

### Какой результат ожидается

В v63:
- ⚠️ `style_checks.json` flag для «произошло событие, которое изменило семейную жизнь» (warning)
- ❌ `style_checks.json` error для «в этой типичности была своя уникальность» (epilogue)
- ⚠️ `epilogue_rewrite_log.json` удалил «Её жизнь была типичной для поколения...» и «Но в этой типичности...»

После rewrite epilogue станет конкретнее:
- До: «...Её жизнь была типичной для поколения, прошедшего через войну и восстановление страны. Но в этой типичности была своя уникальность — стойкость «оловянного солдатика», который не сгибается под ударами судьбы.»
- После rewrite: «...» (оба sentences удалены — epilogue становится короче, без пафоса)

### Как проверить

1. **Unit-тесты** `tests/test_narrative_stop_phrases_event_changed.py`:
   - Pattern A match: «произошло событие, которое изменило семейную жизнь» → flag
   - Pattern A negative: «произошёл переезд» (без «событие… которое») → no flag
   - Pattern B match: «типичной для поколения» → flag
   - Pattern B negative: «типичной была её скромность» (без «поколения») → no flag
   - Pattern C match epilogue: «в этой типичности была своя уникальность» → error flag
   - Idempotent + lemmatize variants

2. **Integration** на v62a text:
   - line 217 «В 1961 году произошло событие, которое изменило...» → flag warning
   - epilogue: «Её жизнь была типичной для поколения...» → flag error + rewrite mapping delete
   - epilogue: «Но в этой типичности была своя уникальность...» → flag error + delete

3. **Verified-on-run** v63:
   - `style_checks.json` errors ≥ 1 (typicality_uniqueness в epilogue)
   - `style_checks.json` warnings ≥ 1 (event_that_changed_life в ch_02)
   - epilogue auto_rewrite log содержит actions delete для typical_for_generation + in_this_typicality_uniqueness

---

## Ограничения

- [ ] **Generic patterns**, без subject-конкретики
- [ ] **Idempotent**
- [ ] **event_that_changed_life — warning only**, не delete (может удалить конкретный fact)
- [ ] **typical_for_generation / in_this_typicality_uniqueness — error + auto_rewrite delete** (чистые клише)
- [ ] Lemmatize-aware patterns (как в task 043b)

---

## Dev Review

**Статус:** ожидает

**[TECH]** — pre-answer от Опуса:
- `event_that_changed_life` warning vs error — выбран warning, чтобы не потерять fact Валерия 1961. GW при следующем prompt-bump может выучить переписывать («В 1961 Валерий не вернулся в интернат...» — прямо с факта).
- Regex `\\W{1,30}` в pattern A — allow short clauses между «событие» и «которое»; calibrate на v62a после прогона.

**[PRODUCT]** — нет

**Сложность:** `xs` (<1 ч)
**Риск:** `low`

---

## Verified-on-run

**Cursor:** [после v63]
**Опус:** независимо проверит — `style_checks.json` содержит flags, epilogue rewrite log содержит delete actions

---

## История

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-18 | `new` | Опус |
