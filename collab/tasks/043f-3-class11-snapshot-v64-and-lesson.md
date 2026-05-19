# Задача 043f-3: Class 11 recurring snapshot v64 + lesson заметка (regex отстаёт от семантики)

**Статус:** `new`
**Номер:** 043f-3
**Автор:** Опус
**Дата создания:** 2026-05-19
**Тип:** конфиг + snapshot test
**Sprint:** v65
**Связано:** task 043 / 043f / 043f-2 (Class 11 recurring 5 sprints v59→v64); принцип 8 (класс лечится семантикой)

---

## Контекст

Class 11 (awkward formulation, X-по-Y listing) **recurring 6 спринтов**:

| Sprint | Форма | Pattern в config |
|--------|-------|-------------------|
| v59 | «не любил советов по электричеству или поездкам» | task 043 |
| v62a | «не любил советов, особенно по электричеству и поездкам» | task 043f |
| v63 | «не любил советов в принципе, особенно по практическим вопросам — будь то электричество или распорядок поездок» | task 043f-2 (pattern_options) |
| **v64** | **«Владимир не любил советов — особенно по электричеству, поездкам и другим бытовым вопросам»** | этот task |

Pattern v63 «в принципе, особенно по X» **не сработал** на v64 формулировке. GW написал короче (12 слов вместо 18-20), без «в принципе» — обходит regex.

**Это явная демонстрация Правила 8** — regex отстаёт от семантики. Этот task:
1. Добавляет snapshot test с v64 формулировкой (per lesson v62a — recurring без snapshot возвращается)
2. Расширяет pattern_options ещё одной формой
3. **Главное:** документирует в самом spec'е что **primary defense теперь revision loop** (Правило 8), regex = **минимальный backup**

---

## Pre-sprint checklist

- [x] Stocktake актуален
- [x] Critical reading — v64 narrative прочитан, Class 11 recurring подтверждён
- [x] Universality — n/a (config + tests)
- [x] Защита подключена — да, через orchestrator 049f-2 → revision_hints → GW семантический suggestion
- [x] Прогон раздельный — combined OK
- [x] Класс — Class 11, recurring documented
- [x] Скрипт-first — да (config + scripted validator)

---

## Спек

### 1. Config расширение `narrative_stop_phrases.json` (v6 → v7)

Существующая category `class11_not_loved_x_by_y_and_z_extended` (task 043f-2) — добавить ещё одну форму в `pattern_options`:

```json
{
  "category": "class11_not_loved_x_by_y_and_z_extended",
  "pattern_options": [
    // EXISTING v62a
    "\\bне\\s+(люб\\w+|выноси\\w+|терп\\w+|перевари\\w+|перенос\\w+)\\s+(\\w+\\w+\\s*,?\\s*)?(особенно\\s+)?по\\s+(\\w+\\w*)\\s+(и|или|,)\\s+(\\w+\\w*)",

    // EXISTING v63 «в принципе, особенно по»
    "\\bне\\s+(люб\\w+|выноси\\w+|терп\\w+|перевари\\w+|перенос\\w+)\\s+(\\w+\\w+\\s+)?(в\\s+принципе|вообще|никогда)\\s*,?\\s*(\\(?особенно\\)?\\s+по\\s+\\w+\\w*)",

    // EXISTING v63 «будь то X или Y»
    "\\bне\\s+(люб\\w+|выноси\\w+|терп\\w+|перевари\\w+|перенос\\w+)\\s+[^.]{0,80}\\s+(будь\\s+то)\\s+\\w+\\s+(и|или|,|\\u2014|\\u2013|-)\\s+\\w+",

    // NEW v64 — «X — особенно по Y, Z и другим [категория]» (без «в принципе»)
    "\\bне\\s+(люб\\w+|выноси\\w+|терп\\w+|перевари\\w+|перенос\\w+)\\s+\\w+\\s*[\\u2014\\u2013\\-]\\s*особенно\\s+по\\s+\\w+\\s*,\\s*\\w+\\s+и\\s+другим\\s+\\w+",

    // NEW v64 — «X — особенно по Y, Z» (короче)
    "\\bне\\s+(люб\\w+|выноси\\w+|терп\\w+|перевари\\w+|перенос\\w+)\\s+\\w+\\s*[\\u2014\\u2013\\-]\\s*особенно\\s+по\\s+\\w+\\s*,\\s*\\w+"
  ],
  "scope": ["ch_02", "ch_03", "ch_04"],
  "severity": "error",
  "suggestion": "Переписать обобщённо: «не любил советов» / «не любил [X]», без перечисления частных категорий. **Семантическое правило** — категорическое утверждение о dispositional черте через перечисление трёх и более частных примеров — generic штамп GW; убрать перечисление, оставить только обобщение либо ОДНУ конкретную деталь из source_quote.",
  "reason": "Class 11 awkward formulation — частное перечисление через X-по-Y/будь то/особенно по. Recurring 6 спринтов v59→v64. Primary defense — revision loop с семантическим hint (см. Правило 8 архитектора); regex = backup detection минимальной формы."
}
```

### 2. Snapshot test добавить v64 форму

`tests/test_class11_recurring_patterns.py` (extend existing):

```python
def test_class11_v64_especially_by_X_Y_other():
    """v64 snapshot — pattern эволюция «— особенно по X, Y и другим Z»."""
    sentence = (
        "Владимир не любил советов — особенно по электричеству, поездкам "
        "и другим бытовым вопросам."
    )
    flags = validate_narrative_stop_phrases_for_sentence(sentence)
    assert any(
        f["category"] == "class11_not_loved_x_by_y_and_z_extended"
        for f in flags
    )


def test_class11_v64_short_form():
    """v64 короткая форма без 'в принципе'."""
    sentence = "Не выносил замечаний — особенно по работе, дому."
    flags = validate_narrative_stop_phrases_for_sentence(sentence)
    assert any(f["category"].startswith("class11_not_loved") for f in flags)
```

### 3. Lesson заметка в spec (для будущих архитекторов)

В sprint plan v65 + handoff Курсору:

> **Class 11 recurring пример — иллюстрация Правила 8 архитектора:**
>
> Class 11 возвращается 6-й спринт подряд в новых формах. Каждый раз мы:
> 1. Видим новую форму в тексте
> 2. Добавляем новый regex
> 3. GW в следующем спринте пишет иначе, regex обходит
>
> Это **бесконечная гонка**. **Лечение через regex невозможно** — это сильный аргумент в пользу архитектурного решения через revision loop с семантическим hint.
>
> Правильное долгосрочное решение (закладывается с v65 через orchestrator 049f-2): regex остаётся как **детектор минимальной формы**, но `suggestion` для GW — **семантическая инструкция** «убрать частное перечисление, оставить обобщение либо ОДНУ конкретную деталь». GW при revision pass ловит **любую** форму класса по семантике.
>
> **К v66+:** если revision loop работает стабильно (v65 PASS), regex для Class 11 можно **заморозить** (не добавлять новые формы) и полагаться на семантический suggestion. Snapshot tests остаются как **минимальная защита** против отката (если revision loop сломается — regex поймает хотя бы last known form).

---

## Universality check

- [x] Промпт — n/a
- [x] Subject-specific — n/a (generic Russian patterns)
- [x] Algorithm generic — applies к любому subject
- [x] Subject-replacement — для Корольковой «не любил гостей — особенно дальних родственников, соседей и других знакомых» поймает ✅

---

## Ограничения

- [ ] Generic patterns
- [ ] Severity error
- [ ] Snapshot test mandatory с v64 example
- [ ] Scope narrative chapters (не ch_01)
- [ ] **Primary defense — revision loop**, regex — backup (документировано)
- [ ] К v66 — оценить можно ли заморозить regex extensions если revision loop работает

---

## Dev Review

**Статус:** ожидает

**[TECH]** — pre-answer от Опуса:
- `narrative_stop_phrases.json: v6 → v7` (расширение existing category)
- Snapshot tests 2+ новых positive (v64) + сохранить existing
- Suggestion field — **семантический** (per Правило 8)
- В sprint plan v65 — lesson заметка про recurring

**[PRODUCT]** — нет

**Сложность:** `xs` (<1 ч)
**Риск:** `low` (config-only + tests)

---

## Verified-on-run v65

**Cursor:** [после v65]
**Опус:** проверит:
- v64 example flagged
- Snapshot tests PASS
- Через revision loop (если v64 form в v65 draft) — GW переписал per семантическому hint

---

## История

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-19 | `new` | Опус |
