# Задача: 046c — epilogue regex: поддержка intermediate words в path_from_X_to_Y

**Статус:** `verified-on-run`
**Номер:** 046c
**Автор:** Никита / Cursor
**Дата создания:** 2026-05-18
**Тип:** `скрипт-конфиг`

> **Статусный флоу:**
> `new` → `dev-review` → `spec-review` → `spec-approved` / `blocked-on-product` → `in-progress` → `dasha-review` → `verified-on-run` → `done`

---

## Контекст

Задача 046 (epilogue_rewrite_mapping.json) реализует auto-rewrite категории `path_from_X_to_Y`.
Текущий regex:
```
(прош\w+|прокат\w+|преодолел\w+)\s+путь\s+от\s+\w+\s+(до|к)\s+\w+
```

Не матчит конструкции с промежуточными словами, например:
- «прошла путь от сироты из X до Y» — `сироты` + `из` перед `до` не матчится
- «прошла долгий путь от X к Y» — «долгий» как intermediate не матчится

Если GW генерирует фразу с промежуточными словами — auto-rewrite пропускает её, validated_stop_phrases фиксирует error, но удаление не происходит.

---

## Спек

### Что нужно изменить

`collab/context/epilogue_rewrite_mapping.json` — категория `path_from_X_to_Y`:

**Старый regex:**
```
(прош\w+|прокат\w+|преодолел\w+)\s+путь\s+от\s+\w+\s+(до|к)\s+\w+
```

**Новый regex (v61-046c):**
```
(прош\w+|прокат\w+|преодолел\w+)\s+путь\s+от\s+\S+(\s+[^.!?]*?)?\s+(до|к)\s+\S+
```

**Изменения:**
- `\w+` → `\S+` (матчит слова с дефисом, скобками и т.п.)
- Добавлена группа `(\s+[^.!?]*?)?` — optional intermediate words между `от X` и `(до|к) Y`

### Какой результат ожидается

После v61: фраза «прошла путь от сироты из Старобельска до замужней женщины» матчится и удаляется auto-rewrite. `grep по «путь от» в text_FULL → 0 hits` после обработки.

### Как проверить

`grep по «путь от» в text_FULL → 0 hits` после auto_rewrite на epilogue.

---

## Ограничения

- Не менять action (`delete_sentence`) — только regex
- Не добавлять subject-specific слова в regex (universality)
- Не затрагивать другие категории rewrite_mapping.json

---

## Dev Review

**[TECH]** Новый regex с optional group `(\s+[^.!?]*?)?` — ленивое совпадение (lazy `?`), не рекурсивное. Не может вызвать catastrophic backtracking на разумном тексте (предложение ≤ 300 символов). ✅

**[TECH]** `\S+` вместо `\w+` — расширяет набор матчей. Возможный edge case: если после `до` идёт знак препинания напрямую — `\S+` съест его. В контексте epilogue это нормально (предложение всё равно удаляется). ✅

**[PRODUCT]** Изменение regex не влияет на формат `book_draft.json` / `fact_map.json`. ✅

**Universality check:**
1. Промпты не меняются → N/A
2. Subject-specific данные → нет (regex категориальный, не содержит имён)
3. Алгоритм generic → `enforce_epilogue_stop_phrases` использует конфиг без привязки к субъекту
4. Subject-replacement test: правило работает для любого субъекта (Корольков, Дмитриев) без изменений ✅

**Статус после Dev Review:** `spec-approved` (Никита go)

---

## Реализация (v61-046c)

`collab/context/epilogue_rewrite_mapping.json`:
- `version`: `"v1"` → `"v2"`
- `path_from_X_to_Y.pattern_regex`: обновлён (см. спек)
- `description`: обновлён: `"... + v61-043c + v61-046c"`

---

## Verified-on-run

**Observation (v61 run):** `grep по «путь от» в text_FULL → 0 hits` после auto_rewrite на epilogue.
