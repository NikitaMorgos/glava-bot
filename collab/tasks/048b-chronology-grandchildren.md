# Задача 048b: Chronology check — внуки + неизвестные birth_year (extension Класса 12)

**Статус:** `new`
**Номер:** 048b
**Автор:** Опус (роль архитектор+продакт)
**Дата создания:** 2026-05-17
**Тип:** `cco-скрипт`
**Batch:** v60 sprint
**Связано:** task 048 (chronological consistency check); diagnostic v59: «В 1973 году дочь Татьяна попросила Валентину уйти с работы, чтобы встречать внучку Дашу после школы» — Даша ещё не родилась в 1973; chronology check не поймал

---

## Контекст

v59 ch_02 содержит **галлюцинацию**:
> «В 1973 году дочь Татьяна попросила Валентину уйти с работы, чтобы встречать внучку Дашу после школы.»

В 1973:
- Татьяна (1956) — 17 лет, **не замужем** (свадьба с Маргось 1977)
- Дочери Даши **ещё не существует**

Это **семейная галлюцинация**, опасная.

`chronology_check.json` v59 показал 3 errors но **НЕ Дашу 1973**. Корень: task 048 detector работает с persons где `birth_year` известен. У Даши `birth_year` в fact_map пуст/неизвестен. Без birth_year — chronology не может проверить.

**Универсальное решение:** для внуков birth_year можно **inferred** из:
- birth_year родителя (внуки в среднем 20-30 лет после родителя)
- Дата брака родителей + ~1-2 года (если родители женаты)
- Контекст событий («сломал руку в 3 года», «пошёл в школу» = ~7 лет)

Для **галлюцинации DEтект** достаточно min bound: «внук/внучка моложе чем замужество родителя + 1 год».

## Universality check

- [x] Промпт — n/a
- [x] Subject-specific — n/a (логика generic)
- [x] Алгоритм generic — использует fact_map.persons с relation parsing
- [x] Subject-replacement test — для Корольковой если её внуки упомянуты в events — chronology bounds работают через её детей ✅

---

## Спек

### Что нужно изменить

**Расширить `validate_chronological_consistency`:**

1. Для **внук/внучка** — если birth_year неизвестен:
   - Найти parent (persons с relation=сын/дочь) — у внука должен быть один из них как родитель
   - Если parent.birth_year известен → grandchild_min_birth_year = parent.birth_year + 16 (минимум для родительства)
   - Если у parent есть `marriage_year` (или event «брак») → grandchild_min_birth_year = marriage_year (или marriage_year + 1)
   - Если parent.relation_to_subject — child субъекта, и в event есть упоминание «внук X» с year < grandchild_min_birth_year → flag `grandchild_mentioned_before_birth`

2. Аналогично для **племянник/племянница**:
   - Parent — sibling субъекта; их birth_year + 16

3. Если parent тоже unknown birth_year — chain rule (parent of parent), либо warning «cannot determine bound», не error

4. Сохранить отдельный severity:
   - `person_mentioned_before_birth` (известный birth_year): error
   - `grandchild_mentioned_before_inferred_birth` (inferred via parent): warning (не error — bound нестрогий)

### Какой результат ожидается

В v60 chronology_check.json:
- ✅ «1973 год + внучка Даша» → flag warning `grandchild_mentioned_before_inferred_birth`
- ✅ В book v60 GW переписал ch_02 без этой галлюцинации (если detector flags GW во время revision)

### Как проверить

1. **Unit-тесты** `tests/test_chronology_grandchildren.py`:
   - Внук без birth_year + parent 1956 + событие 1970 → flag (внук inferred min 1972)
   - Внучка + parent marriage 1977 + событие 1973 → flag
   - Племянник + sibling unknown → warning «cannot determine», не error

2. **Integration** на v59 text:
   - «1973 внучка Даша» → flag

3. **Verified-on-run** v60:
   - chronology_check.json содержит flag для grandchild before inferred birth
   - В book v60 эта галлюцинация переписана

---

## Ограничения

- [ ] Inferred bounds — нестрогие, могут давать false positives — warning не error
- [ ] Generic algorithm — использует fact_map persons + relations
- [ ] Universal

---

## Dev Review

**Статус:** ожидает
**[TECH]** — relation parsing требует ясной связи parent ↔ grandchild в fact_map; если связи нет — warning «cannot determine», не fail
**[PRODUCT]** — нет
**Сложность:** `s` (1-3 ч)
**Риск:** `low` (warning-level, не enforce)

---

## История

| Дата | Статус | Кто |
|---|---|---|
| 2026-05-17 | `new` | Опус |
