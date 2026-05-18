# Задача 043b: Stop-phrases lemmatize + categorical anti-triggers в нарративе

**Статус:** `new`
**Номер:** 043b
**Автор:** Опус (роль архитектор+продакт)
**Дата создания:** 2026-05-17
**Тип:** `cco-скрипт` + конфиг
**Batch:** 2-fix
**Связано:** task 043 (epilogue stop-phrases); diagnostic v58: detector пропустил «человеком своего времени» (падеж), нарратив имеет «семейные узы крепче», «определило всю жизнь», «расстроить любую мать»

---

## Контекст

v58 detector `validate_epilogue_stop_phrases` сработал на 2 фразы, но **пропустил**:
- «**Она была человеком своего времени**» (творительный падеж — detector ищет «человек своего времени» именительный)
- «прошла через все испытания XX века **с поднятой головой**» (variant фразы из v56 stop list)

Также в **нарративе** (вне epilogue) появились **новые** украшения (Никитин feedback):
- ❌ «семейные узы оказались крепче формальных различий» (ch_02)
- ❌ «акушерство — специальность, которая определила всю её дальнейшую жизнь» (ch_02) — фактическая ошибка + украшение
- ❌ «событие, которое могло расстроить любую мать ... отнеслась спокойно» (ch_02) — противоречивая пара украшений

Это **Класс 6 расширяется на нарратив** (не только epilogue).

---

## Спек

### Что нужно изменить

**1. Stop-phrases detector — суффикс-aware (lemmatize-like)**:

Вместо точного substring search использовать regex с **флексией суффиксов** для русских падежей.

Пример:
- Старый: `"человек своего времени"` — литеральный substring
- Новый pattern: `r"человек\w{0,3}\s+своего\s+времени"` — ловит «человек», «человеком», «человеку», «человека»

Для каждой generic stop-phrase из `epilogue_stop_phrases.json` — авто-генерация regex с суффиксами через хелпер:

```python
def lemmatize_pattern(phrase: str) -> str:
    """Грубая лемматизация — добавляет \w{0,3} к именам существительным/прилагательным."""
    words = phrase.split()
    pat = []
    for w in words:
        if len(w) >= 5 and w[-1] in "аеиоыуяюэё":
            pat.append(re.escape(w[:-1]) + r"\w{0,3}")
        else:
            pat.append(re.escape(w))
    return r"\b" + r"\s+".join(pat) + r"\b"
```

**2. Categorical anti-triggers в нарративе** — новый раздел в `epilogue_stop_phrases.json` (или новый файл `narrative_stop_phrases.json`):

```json
{
  "version": "v2",
  "generic_categorical_patterns": [
    {
      "category": "metaphor_bonds",
      "pattern": r"\b(семейн\w+|кровн\w+|родств\w+)\s+узы\s+(оказ\w+\s+)?крепче\s+\w+",
      "example_neg_template": "[семейные|кровные|родственные] узы оказались крепче [X]"
    },
    {
      "category": "lifedefining_speciality",
      "pattern": r"(определ\w+|стал\w+)\s+(всю|её|всей|его)?\s*(дальнейш\w+|будущ\w+|всю)?\s*(жизн\w+|карьер\w+|судьб\w+)",
      "example_neg_template": "[профессия] — специальность, которая определила всю [его/её] [жизнь/карьеру/судьбу]"
    },
    {
      "category": "could_X_any_Y_but_actually_Z",
      "pattern_pair": [
        r"\b(могло|способно)\s+\w+\s+любо\w+\s+(матер|отц|родител)",
        r"\bотн\w+\s+(спокойн|ровн)\w+|приняла? спокойно"
      ],
      "description": "пара противоречивых украшений — генеральное преувеличение + успокаивающее"
    },
    {
      "category": "epilogue_path_X_to_Y",
      "pattern": r"\bпуть\s+от\s+\w+\s+(до|к)\s+\w+"
    },
    {
      "category": "filled_with_X",
      "pattern": r"(жизн\w+|жил\w+)\s+был\w+\s+наполнен\w+",
      "example_neg_template": "жизнь была наполнена [абстрактное обобщение]"
    },
    {
      "category": "passed_to_generations",
      "pattern": r"передал\w+\s+(следующ\w+\s+поколен|потомк|следующ\w+\s+поколения)",
      "example_neg_template": "передались следующим поколениям"
    },
    {
      "category": "person_of_their_time",
      "pattern": r"человек\w{0,3}\s+своего\s+времени"
    }
  ],
  "scoped_to_epilogue_only": ["epilogue_path_X_to_Y", "filled_with_X", "passed_to_generations", "person_of_their_time"],
  "scoped_to_narrative_and_epilogue": ["metaphor_bonds", "lifedefining_speciality", "could_X_any_Y_but_actually_Z"]
}
```

Все patterns **categorical** — не упоминают «Каракулину», «Татьяну», «электричество». Применимы для любого subject.

**3. Detector `validate_narrative_stop_phrases(book, config)` (новый, отдельно от epilogue)**:
- Проверяет все chapters (`ch_01..ch_04`)
- Применяет `scoped_to_narrative_and_epilogue` patterns
- Pair-patterns (например «могло X любого Y» + «отнеслась спокойно») — flag если **оба в одном абзаце** (paragraph)
- Возвращает issues с severity (epilogue → error, ch_02-04 → warning, можно настроить)

### Какой результат ожидается

В v59 detector ловит:
- ✅ «человеком своего времени» (творительный)
- ✅ «семейные узы оказались крепче» (категория metaphor_bonds)
- ✅ «определило всю её дальнейшую жизнь» (lifedefining_speciality)
- ✅ «расстроить любую мать ... отнеслась спокойно» (pair)
- ✅ «прошла путь от X до Y» (epilogue_path)
- ✅ «жизнь была наполнена...» (filled_with_X)

В `<run>_style_checks.json`:
- `narrative_stop_phrases.errors`: paired flags
- `epilogue_stop_phrases.errors`: padezhi covered

### Как проверить

1. **Unit-тесты** `tests/test_stop_phrases_lemmatize.py`:
   - «человек своего времени» / «человеком своего времени» / «человека своего времени» — все match
   - «семейные узы оказались крепче формальных» → category metaphor_bonds
   - «семейные узы крепче всего» (без «оказались») — тоже match (semi-flexible)
   - Pair: «могло расстроить любую мать» + «отнеслась спокойно» в одном paragraph → flag
   - False positives: «определило встречу» (не «жизнь») → НЕ match

2. **Integration** на v58c text_FULL:
   - Должны быть пойманы все 4 главных украшения Никитиного feedback + «человеком своего времени»

3. **Verified-on-run** v59:
   - `validate_narrative_stop_phrases` → 0 errors (после GW v2.20 + epilogue auto-rewrite task 046)

---

## Ограничения

- [ ] Lemmatize — грубая, не perfect. Допустимы false positives как warnings (не блокер)
- [ ] Patterns categorical, без Каракулиноспецифики
- [ ] Idempotent
- [ ] Universal: одинаково работает на Корольковой/Дмитриеве

---

## Dev Review

**Статус:** ожидает

**[TECH]** — пред-резолв: `lemmatize_pattern` — простой хеуристический хелпер; для лучшего точности можно использовать `pymorphy2`, но это **dependency** — пока не вводим.

**[PRODUCT]** — нет (категории украшений выбраны из v58 feedback Никиты, обобщены до generic patterns).

**Сложность:** `s` (1-3 ч)
**Риск:** `low`

---

## История

| Дата | Статус | Кто |
|---|---|---|
| 2026-05-17 | `new` | Опус |
