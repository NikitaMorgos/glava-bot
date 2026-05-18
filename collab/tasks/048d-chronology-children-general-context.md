# Задача 048d: Chronology check — children mentioned before birth (generic context)

**Статус:** `new`
**Номер:** 048d
**Автор:** Опус (роль архитектор+продакт)
**Дата создания:** 2026-05-18
**Тип:** `cco-скрипт`
**Sprint:** v63
**Связано:** task 048 / 048b / 048c (chronological consistency check, Класс 12); v62a regression «В Германии Валентина не работала — сидела с детьми» (1946-48, дети ещё не родились)

---

## Контекст

В v62a ch_02 (line 213) обнаружена **семейная хронологическая ошибка** того же класса что Даша-1973 (v59):

> «В Германии Валентина не работала — сидела с детьми. ***Жёны военных в зарубежных гарнизонах не работали — их задачей было ведение дома и воспитание детей в изоляции от местного населения.***»

Контекст «в Германии» означает **1946-1948**. По fact_map:
- Валерий родился **1948** (в Вышнем Волочке после возвращения из Германии)
- Татьяна родилась **1956**

В 1946-1947 **никаких детей ещё не было**. В 1948 Валерий родился уже после возвращения. Фраза «сидела с детьми в Германии» — хронологическая выдумка.

**Существующие защиты (task 048b/048c) не покрыли:**
- 048b проверяет **внуков** через parent.marriage_year/birth_year (relation=внук/внучка)
- 048c расширил для grandchild contexts — `validate_chronological_consistency` для grandchildren patterns
- **Дети субъекта** (relation=сын/дочь) при упоминании в общих контекстах («сидела с детьми», «воспитывала детей») **никакой проверки**

**Класс:** Class 12 (chronology) — расширение на **subject's own children mentioned in plural/generic context** (без точного имени).

---

## Universality check

- [x] Промпт — n/a (чистый скрипт)
- [x] Subject-specific — n/a (логика generic; использует fact_map.persons + birth_year)
- [x] Алгоритм generic — для любого subject: дети с relation ∈ {сын, дочь} имеют birth_year; min(children.birth_year) определяет «когда дети появились»
- [x] Subject-replacement test — для Корольковой/Дмитриева: если у них есть дети в fact_map, generic phrase «с детьми» в контексте period < min(children.birth_year) → flag ✅

**Trap warning:** конкретный эпизод «Германия 1946-48 + дети» — это **проявление**, не класс. Класс = «упоминание children pluralis/generic в period до min(birth_year) ребёнка субъекта». Spec строится на классе.

---

## Спек

### Что нужно изменить

**Расширить `validate_chronological_consistency`** в `pipeline_utils.py`:

1. Новая проверка `children_mentioned_before_first_child_birth`:
   - Собрать `children = fact_map.persons[]` где `relation_to_subject ∈ {сын, дочь}`
   - Вычислить `first_child_birth = min(child.birth_year for child in children if child.birth_year is not None)`
   - Если `children` пуст или `first_child_birth` неизвестен → skip check (warning «cannot determine»)

2. **Generic patterns в narrative** (любой paragraph book):
   - `(с|со)\s+дет(ьми|ям\w*)` — «с детьми / со детишками»
   - `воспит\w+\s+дет\w+` — «воспитывала детей»
   - `сидел\w+\s+(с\s+)?дет\w+` — «сидела с детьми»
   - `родил\w+\s+дет\w+` — «родила детей» (in plural)
   - `маленьк\w+\s+дет\w+` — «маленькие дети»
   - `(гулял\w+|играл\w+)\s+с\s+дет\w+` — «гуляла с детьми»

3. **Detection window:** в каждом paragraph где matched pattern — найти ближайший year (±2 sentences):
   - Если year < `first_child_birth` → flag `children_mentioned_before_first_child_birth`
   - Severity: **error** (точный bound, не inferred)

4. **Edge case — period упоминание без точного year:**
   - Если paragraph упоминает `Германии` / `в Венгрии` / `на фронте` / другой period (распарсить из fact_map.timeline.events с year_range):
     - Если period.year_range_end < first_child_birth → flag тоже
   - Это требует opt-in через config `period_to_year_range` mapping (см. ниже)

5. **Конфиг** `chronology_periods_<subject>.json` (новый, optional):
```json
{
  "subject_id": "karakulina",
  "version": "v1",
  "period_phrases": [
    {"phrase": "в Германии", "year_range": [1946, 1948], "source": "ep_007"},
    {"phrase": "на фронте", "year_range": [1941, 1945], "source": "ep_004"}
  ]
}
```
   - Если конфига нет → skip period-based check, только direct-year check работает
   - Универсально: для Корольковой будет свой `chronology_periods_korolkova.json`

### Какой результат ожидается

В v63 chronology_check.json:
- ✅ «В Германии Валентина не работала — сидела с детьми» (1946-48) → flag error `children_mentioned_before_first_child_birth` (first_child=1948)
- ✅ Любой будущий аналог («в Польше воспитывала детей» при period < first_child) — flag
- ⚠️ False positive risk: «в Германии родился ребёнок» — это **новое событие**, не «уже были дети». Mitigation: pattern `родил\w+\s+дет\w+` matched **только в plural** (не `родился ребёнок`). Single-child phrases (singular) excluded.

### Как проверить

1. **Unit-тесты** `tests/test_chronology_children_generic.py`:
   - Generic: subject has children born 1948 + 1956. Paragraph «в Германии (1946-1948) сидела с детьми» → flag error
   - Generic: subject has children born 1948 + 1956. Paragraph «в Венгрии (1958-1962) сидела с детьми» → no flag (1958 > 1948)
   - Edge: subject has 0 children в fact_map → skip check
   - Edge: paragraph «родила Валерия в 1948 в Германии» — match `родил\w+` но НЕ matches plural pattern → no flag

2. **Integration** на v62a text (line 213):
   - paragraph: «В Германии Валентина не работала — сидела с детьми. ...»
   - Year context: «В Германии» → period 1946-1948 (если config present) ИЛИ ближайший year mention
   - `first_child_birth = 1948`
   - flag error

3. **Verified-on-run** v63:
   - `chronology_check.json` errors включает `children_mentioned_before_first_child_birth` для Германия 1946-48 paragraph

---

## Ограничения

- [ ] **Не enforce** (риск false positive с «родился ребёнок» в singular) — только flag warning/error
- [ ] **Generic patterns**, не subject-specific фразы
- [ ] **Idempotent** — повторный вызов не дублирует findings
- [ ] **period_phrases config** — optional per subject; если отсутствует → только direct-year detection
- [ ] **Severity:** error (точный bound с known birth_year), не warning

---

## Dev Review

**Статус:** ожидает

**[TECH]** — pre-answer от Опуса:
- Period-based check требует config `chronology_periods_<subject>.json` — optional, если нет → direct-year only
- Singular vs plural pattern — критично; «ребёнок родился» singular, не должен match
- Detection window ±2 sentences — баланс между recall и precision; могут быть false positives на длинных paragraphs

**[PRODUCT]** — нет

**Сложность:** `s` (1-3 ч)
**Риск:** `low` (warning-level, generic patterns proven в 048b/048c)

---

## Verified-on-run

**Cursor:** [после v63 прогона]
**Опус:** откроет `karakulina_v63_chronology_check.json`, проверит наличие flag для line «В Германии ... сидела с детьми»

---

## История

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-18 | `new` | Опус |
