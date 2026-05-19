# Задача 044i-2: Characteristic words universality verify — finding + fix через task 049h

**Статус:** `verified-by-opus`
**Номер:** 044i-2
**Автор:** Опус
**Дата создания:** 2026-05-19
**Тип:** verification report + delegation to 049h
**Sprint:** v65
**Связано:** task 049h (GW Правило 2 universality fix); Никитин вопрос v64 «выковыривал — это правило универсальное или каракулинское?»

---

## Контекст

Никита заметил в v64 что слово «выковыривал» **всегда сохраняется** в narrative, и спросил — это потому что universal mechanism работает (pin-list per subject) либо потому что захардкожено в GW prompt?

---

## Verification report

Опус проверил 3 слоя (2026-05-19):

| Слой | Subject-specific? | Где | Status |
|------|-------------------|-----|--------|
| Pin-list (`known_episodes_karakulina.md`) | ✅ Per subject (правильно) | Секция «Голос рассказчика — characteristic words» (строки 121+), 6 слов: выковыривал, зарубиться на пустом месте, зажиточные ребята, движуха, рукастый, бабульно | ✅ Universal mechanism |
| Pipeline code (`pipeline_utils.py`) | ✅ Generic | `pin_list.get("characteristic_words", [])` в parser + validate_pin_list_compliance | ✅ Universal mechanism |
| **GW prompt v2.23 (Правило 2)** | ❌ **Захардкожено** | Строки 58 (шапка) + 190-202 (examples в финальном тексте Правила 2) — «выковыривал», «зарубиться на пустом месте», «зажиточные ребята», «движуха», «рукастый» | ❌ **BUG universality** |

### Verdict

**Слово «выковыривал» сохраняется потому что захардкожено в GW prompt**, **не** потому что universal mechanism работает.

Pin-list секция characteristic_words **не передаётся** в GW input в текущей реализации (либо передаётся неэффективно — GW читает захардкоженный список из своего prompt раньше чем смотрит input).

### Риск при подключении Корольковой

GW увидит инструкцию «обязательно сохрани выковыривал, зарубиться, зажиточные ребята, движуха, рукастый» — слов которых в её transcripts **нет**:
- Лучший случай: GW проигнорирует (правило 2 не сработает, даже если у Корольковой есть свои characteristic words в pin-list)
- Худший случай: GW «навяжет» эти слова в narrative Корольковой (выдумает контекст где не нужно)

---

## Fix — delegated to task 049h

Этот task **только verification report**. Fix реализуется в task **049h** (GW v2.23 → v2.24 ПРАВИЛО 2 universality):
1. Заменить захардкоженные examples в финальном тексте Правила 2 на **placeholder examples**
2. Wire `pin_list.characteristic_words` per subject в GW input (через PIN_LIST_EVENTS либо отдельный блок CHARACTERISTIC_WORDS)
3. GW prompt говорит «используй characteristic_words из input», не «используй [конкретный список 5 слов]»

См. полный spec в `049h-gw-rule2-universality-fix.md`.

---

## Lesson learned (для auto-memory)

Это **рекуррентная ошибка Опуса** при universality check:
- v60 sprint: проскочил «Татьяна родилась в 1956 году в Твери» в GW ПРАВИЛО 9 (поймали ретроспективно)
- v63 sprint: поправил **перед** commit при self-check (Каракулино examples в spec 049d ПРАВИЛО 12 + 038c ПРАВИЛО 7)
- v64 sprint: пропустил **в existing правиле** (Правило 2 v2.23 — не я добавил v23, унаследовано от v2.18+; не проверил при universality check)

**Procedural fix** (зафиксирован в `architect_universality_check.md` + `_template.md` pre-sprint checklist):

При каждом GW/CA prompt-bump commit'е — обязательный grep команда **по всему файлу промпта** (не только по новому правилу):

```bash
grep -in "Каракулин\|Татьян\|Валентин\|Химинститут\|выковырив\|зарубить\|зажиточн\|движуха\|рукаст\|бабульно\|Молдави\|1946 год\|две недели" prompts/03_ghostwriter_v_X.md
```

Если хоть один match в финальном тексте промпта (не в шапке-истории, не в комментариях dev) — переделать на placeholder.

---

## Pre-sprint checklist

- [x] Stocktake актуален
- [x] Critical reading — открыт `prompts/03_ghostwriter_v2.23.md`, найдены захардкоженные words
- [x] Universality — этот task только verification, fix в 049h
- [x] Защита подключена — да, через 049h fix + procedural grep команда
- [x] Прогон — не trog (verification + delegation)
- [x] Класс — universality recurring моя ошибка
- [x] Скрипт-first — n/a

---

## Status

**Verification complete. Fix delegated to task 049h.** В v65 sprint этот task закроется автоматически после 049h реализации + verify.

---

## Verified-on-run v65

После v65 verify:
- GW v2.24 Правило 2 содержит **placeholders** для characteristic words examples, не Каракулино-specific
- В narrative Корольковой (когда подключим) — слова из её pin-list, не «выковыривал»
- Grep команда `grep -in "выковырив|зарубить|зажиточн|движуха|рукаст" prompts/03_ghostwriter_v2.24.md` возвращает 0 matches в **финальном тексте** Правила 2 (только в шапке version history допустимо)

---

## История

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-19 | `verified-by-opus`, delegation 049h | Опус |
