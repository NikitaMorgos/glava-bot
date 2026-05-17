# Задача 048: Chronological consistency check (Класс 12 — новый)

**Статус:** `new`
**Номер:** 048
**Автор:** Опус (роль архитектор+продакт)
**Дата создания:** 2026-05-17
**Тип:** `cco-скрипт`
**Batch:** 2-fix
**Связано:** stocktake 2026-05-17 — **новый Класс 12** (chronological inconsistency); Никитин feedback v58

---

## Контекст

В v58 ch_02 GW написал:

> «С 1946 по 1948 год семья жила в Германии. Валентина не работала — **сидела с детьми**, как было принято в военных семьях.»

**Глюк:** в 1946 у неё ещё не было детей. Сын Валерий родился в 1948 (в Вышнем Волочке). В 1946-48 Германия — она сидела **без** детей (или с одним ребёнком к 1948).

Это **Класс 12 — chronological inconsistency**: GW упомянул persons (детей) в event period где они ещё не родились (по их `birth_year` в fact_map).

Универсальный класс для всех биографий — где много persons и временных рамок.

---

## Спек

### Что нужно изменить / создать

**1. Функция `validate_chronological_consistency(book, fact_map) -> report`** в `pipeline_utils.py`:

```python
def validate_chronological_consistency(book, fact_map) -> dict:
    """
    Класс 12: проверка что persons упомянуты только в events где они уже existed.
    
    Returns:
        {
          "issues": [
            {
              "chapter_id": "ch_02",
              "type": "person_mentioned_before_birth",
              "person_name": "дети",
              "person_birth_year_min": 1948,
              "event_year_range": "1946-1948",
              "snippet": "...сидела с детьми, как было принято...",
              "severity": "error"
            }
          ],
          "errors_count": N,
          "warnings_count": M
        }
    """
```

**Алгоритм:**

1. Для каждого chapter — извлечь paragraphs + content
2. Для каждого paragraph:
   - Извлечь упомянутые **years** (regex `\b(19|20)\d{2}\b`) и **year ranges** (`\bN+\s*[-–]\s*N+\b`)
   - Извлечь упомянутые **persons** (имена/aliases из fact_map.persons + общие термины: «дети», «сын», «дочь», «внуки», «муж», «жена»)
   - Для каждой пары (year_or_range, person):
     - Получить `birth_year` персоны из fact_map (или min год для коллективных терминов)
     - Если year < birth_year → flag `person_mentioned_before_birth`
     - Если year > death_year + 5 (с буфером) → flag `person_mentioned_after_death`

3. Особый случай — **«дети» / «внуки» как общий термин**:
   - «дети» = min(birth_year всех `relation in {сын, дочь}`)
   - «внуки» = min(birth_year всех `relation in {внук, внучка}`)
   - «сидела с детьми» в 1946 → min(сын Валерий 1948, дочь Татьяна 1956) = 1948. **1946 < 1948 → ERROR.**

### Какой результат ожидается

В v59 `<run>_chronology_check.json`:
- 0 errors

Конкретно — v58 «1946-48 сидела с детьми» в v59 GW должен переписать как:
- ✅ «С 1946 по 1948 год семья жила в Германии. Валентина не работала. В 1948 году в Вышнем Волочке родился сын Валерий.»

### Как проверить

1. **Unit-тесты** `tests/test_chronology_check.py`:
   - «1946 сидела с детьми» + Валерий birth=1948 → flag person_mentioned_before_birth
   - «1948 жила с сыном Валерием» + Валерий birth=1948 → PASS
   - «1985 встречалась с дочерью» + дочь жива → PASS
   - «1990 говорила с мужем» + муж died 1978 → flag person_mentioned_after_death

2. **Integration** на v58c:
   - Должен найти «1946 сидела с детьми» → 1 error

3. **Verified-on-run** v59:
   - `<run>_chronology_check.json` errors_count: 0

---

## Ограничения

- [ ] Generic for any subject — persons и birth/death years из fact_map
- [ ] Коллективные термины («дети», «внуки») — list patterns
- [ ] Edge case: «дети» в общем смысле (не свои) — НЕ flag. Распознавать по контексту: если paragraph упоминает конкретного субъекта + событие, то «дети» = свои дети
- [ ] Severity: error для children/spouse, warning для distant relatives
- [ ] Idempotent

---

## Dev Review

**Статус:** ожидает

**[TECH]** — пред-резолв:
- Word-tokenize русский — sentence-aware (точка = граница events)
- «дети» как термин — patterns: `\bдет\w+\b`, `\bсын\w*\b`, `\bдоч\w*\b`, `\bвнук\w*\b`
- Birth/death years — обязательно у persons в fact_map; иначе skip с warning

**[PRODUCT]** — нет.

**Сложность:** `m` (3-8 ч; сложность в правильном tokenize + correct collective term resolution)
**Риск:** `medium` (false positives возможны — например «дети 1990-х» как общий термин эпохи)

---

## История

| Дата | Статус | Кто |
|---|---|---|
| 2026-05-17 | `new` | Опус |
