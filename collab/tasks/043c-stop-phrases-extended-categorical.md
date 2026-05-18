# Задача 043c: Stop-phrases extended categorical patterns

**Статус:** `new`
**Номер:** 043c
**Автор:** Опус (роль архитектор+продакт)
**Дата создания:** 2026-05-17
**Тип:** конфиг + минор скрипт
**Batch:** v60 sprint
**Связано:** task 043b (lemmatize stop-phrases); diagnostic v59: Class 1 в новых формах

---

## Контекст

В v59 GW переписал украшательства в **новых формах**, обходящих текущие patterns:

| v59 фраза | Категория |
|---|---|
| «родственные связи оказались крепче обстоятельств» | metaphor_bonds — категория есть, но текущий regex не покрывает «связи... крепче обстоятельств» (без «семейные/родственные узы») |
| «специальность, которая определила всю её дальнейшую жизнь в медицине» | lifedefining_speciality — категория есть, regex покрывает «определила всю жизнь», но **в epilogue также** «вместила в себя основные вехи советской эпохи» (новая) |
| «верила в идеалы, за которые воевала» | новая категория — `motivation_attribution` (атрибуция мотивации без подтверждения) |
| «не сломленная обстоятельствами» | новая категория — `unbroken_by_circumstances` (epilogue клише) |
| «такой она и ушла» | новая категория — `that_is_how_X_passed` (epilogue клише) |
| «сохранившая до конца свои принципы» | новая категория — `kept_until_end` (epilogue клише) |
| «помогла пережить все испытания и сохранить достоинство» | расширение `path_from_X_to_Y` — `survived_all_X` |
| «вместила в себя основные вехи советской эпохи» | новая категория — `embraced_milestones_of_era` |

Все **universal categorical patterns**, не subject-specific.

## Universality check

- [x] Промпт — паттерны в конфиге, не в промпте
- [x] Subject-specific — паттерны generic для русского biographical жанра; для других subjects работают
- [x] Алгоритм generic — regex lemmatize-aware
- [x] Subject-replacement test — для Корольковой «верила в идеалы, за которые работала» — тоже flag ✅

---

## Спек

### Что нужно изменить

**`collab/context/narrative_stop_phrases.json`** (или соответствующий) — расширить categories:

```json
{
  "generic_categorical_patterns": [
    {
      "category": "metaphor_bonds_extended",
      "pattern": "\\b(семейн\\w+|кровн\\w+|родств\\w+)\\s+(узы|связи)\\s+(оказ\\w+\\s+)?крепче\\s+\\w+",
      "scope": ["epilogue", "ch_02", "ch_03"]
    },
    {
      "category": "lifedefining_X",
      "pattern": "(определ\\w+|стал\\w+)\\s+(всю|её|всей|его)?\\s*(дальнейш\\w+|будущ\\w+|всю)?\\s*(жизн\\w+|карьер\\w+|судьб\\w+|путь)",
      "scope": ["epilogue", "ch_02"]
    },
    {
      "category": "motivation_attribution_ideals",
      "pattern": "\\bверил\\w+\\s+в\\s+(идеал\\w+|ценност\\w+|мечт\\w+)\\s*(,?\\s*за\\s+котор\\w+\\s+\\w+)?",
      "scope": ["epilogue"],
      "reason": "атрибуция мотивации без подтверждения в источнике"
    },
    {
      "category": "unbroken_by_circumstances",
      "pattern": "\\bне\\s+сломленн\\w+\\s+(обстоятельств\\w+|испытан\\w+|судьб\\w+|жизн\\w+)",
      "scope": ["epilogue"]
    },
    {
      "category": "that_is_how_X_passed",
      "pattern": "\\b[Тт]ак\\w*\\s+(она|он|они)\\s+и\\s+ушл\\w+",
      "scope": ["epilogue"]
    },
    {
      "category": "kept_until_end",
      "pattern": "\\bсохранив\\w+\\s+(до\\s+конца|до\\s+самого\\s+конца|до\\s+последнего)\\s+\\w+",
      "scope": ["epilogue"]
    },
    {
      "category": "survived_all_X",
      "pattern": "\\bпережит\\w+\\s+все\\s+(испытан\\w+|трудност\\w+|невзгод\\w+)",
      "scope": ["epilogue"]
    },
    {
      "category": "embraced_milestones",
      "pattern": "\\bвместил\\w+\\s+(в\\s+себя)?\\s*(основные\\s+)?(вехи|этапы|событи\\w+)\\s+\\w+\\s*(эпох\\w+|столетия|века)",
      "scope": ["epilogue"]
    }
  ]
}
```

**Расширить `enforce_epilogue_stop_phrases`** (task 046) — добавить новые categories в mapping:

```json
{
  "rules": [
    {
      "category": "motivation_attribution_ideals",
      "pattern_regex": "\\bверил\\w+\\s+в\\s+(идеал\\w+|ценност\\w+)\\s*(,?\\s*за\\s+котор\\w+\\s+\\w+)?",
      "action": "delete_sentence"
    },
    {
      "category": "unbroken_by_circumstances",
      "pattern_regex": "\\bне\\s+сломленн\\w+\\s+(обстоятельств\\w+|испытан\\w+|судьб\\w+|жизн\\w+)",
      "action": "delete_sentence"
    },
    {
      "category": "that_is_how_X_passed",
      "pattern_regex": "\\b[Тт]ак\\w*\\s+(она|он|они)\\s+и\\s+ушл\\w+",
      "action": "delete_sentence"
    },
    {
      "category": "kept_until_end",
      "pattern_regex": "\\bсохранив\\w+\\s+(до\\s+конца|до\\s+самого\\s+конца)\\s+\\w+",
      "action": "delete_sentence_if_part_of_clause"
    },
    {
      "category": "survived_all_X",
      "pattern_regex": "\\bпережит\\w+\\s+все\\s+(испытан\\w+|трудност\\w+)",
      "action": "delete_sentence"
    }
  ]
}
```

### Какой результат ожидается

В v60 epilogue:
- ❌ «верила в идеалы, за которые воевала» — удалено
- ❌ «не сломленная обстоятельствами» — удалено
- ❌ «такой она и ушла» — удалено
- ❌ «сохранившая до конца свои принципы» — удалено
- ❌ «помогла ей пережить все испытания и сохранить достоинство» — удалено
- ❌ «жизнь вместила в себя основные вехи советской эпохи» — удалено
- ❌ «родственные связи оказались крепче обстоятельств» (ch_02) — flagged как warning

После всех удалений epilogue будет **более конкретный** — фактологический, без клише.

### Как проверить

1. **Unit-тесты** на каждую новую category:
   - Pattern match → flag
   - Negative case → PASS
   - Idempotent

2. **Integration** на v59 epilogue + ch_02:
   - 5+ новых categories flagged + удалены (epilogue)
   - 1 ch_02 warning «связи крепче»

3. **Verified-on-run** v60:
   - `style_checks.json` errors=0 для epilogue
   - `epilogue_rewrite_log.json` — действия по новым categories

---

## Ограничения

- [ ] Generic patterns, без subject-specific
- [ ] Idempotent
- [ ] Universal (применимо к любому биографическому тексту)

---

## Dev Review

**Статус:** ожидает
**[TECH]** — `delete_sentence_if_part_of_clause` — новый action; реализовать как extension `delete_sentence`
**[PRODUCT]** — нет
**Сложность:** `xs` (<1 ч)
**Риск:** `low`

---

## История

| Дата | Статус | Кто |
|---|---|---|
| 2026-05-17 | `new` | Опус |
