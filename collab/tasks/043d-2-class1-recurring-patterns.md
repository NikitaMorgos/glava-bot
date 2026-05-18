# Задача 043d-2: Class 1 recurring patterns extend — speciality_defined_life recurring + episode_especially_remembered + motivation_confabulation

**Статус:** `new`
**Номер:** 043d-2
**Автор:** Опус (роль архитектор+продакт)
**Дата создания:** 2026-05-18
**Тип:** конфиг + минор скрипт + snapshot tests (mandatory)
**Sprint:** v64
**Связано:** task 043d (v62a), task 043g (v63), Class 1 causal confabulation recurring (v56→v60→v62a→v63 в новых формах)

---

## Контекст

Class 1 (causal confabulation в narrative / CA description) **возвращается в новых формах** каждый sprint:

| Sprint | Form | Закрыт в |
|--------|------|----------|
| v56 | огурцы «не привозит достаточно подарков» (causal claim не в источнике) | task 038 v62a |
| v60 | (общий тренд continued) | scripted defenses |
| v62a | огурцы «не привозит подарки из командировок» (location generalisation) | task 038c v63 |
| v62a | «специальность, которая определила всю её жизнь» | task 043d v63 |
| **v63** | «специальность, которая определила всю её **дальнейшую** жизнь в медицине» — recurring (task 043d не покрыл новую форму) | этот task |
| **v63** | «ей казалось, что родственники мужа должны присылать больше подарков» (motivation confabulation, not location) | этот task |
| **v63** | «Один эпизод особенно запомнился: ...» (multiplication of significance — subjective claim о memorability) | этот task |

**Класс остаётся:** GW добавляет **causal/motivational claims которых нет в transcripts**. Patterns эволюционируют семантически.

**Lesson stocktake:** этот класс **архитектурно** закрывается через revision loop (task 049e), но также нужны **scripted snapshot patterns** для detection. Pattern-based detection всегда behind LLM creativity, но minimum coverage обязателен.

---

## Universality check

- [x] Промпт — n/a (config + script)
- [x] Subject-specific — n/a (generic patterns)
- [x] Алгоритм generic — regex lemmatize-aware
- [x] Subject-replacement test — для любого subject «X — специальность, которая определила Y» / «эпизод особенно запомнился» поймёт без правок ✅

---

## Спек

### 1. Конфиг extend `narrative_stop_phrases.json` (v4 → v5)

Расширить existing categories + добавить новые:

```json
{
  "generic_categorical_patterns": [
    // EXISTING: speciality_defined_life — расширить pattern для recurring форм
    {
      "category": "speciality_defined_life_v3",
      "pattern": "(специальност\\w+|профессия|образовани\\w+|обучени\\w+)\\W{1,40}(определ\\w+|стал\\w+|сформирова\\w+)\\W{1,30}(всю|её|его|их|дальнейш\\w+|будущ\\w+)?\\W{0,10}(жизн\\w+|карьер\\w+|судьб\\w+|путь|деятельност\\w+)",
      "scope": ["ch_02", "ch_03", "epilogue"],
      "severity": "error",
      "suggestion": "Удалить causal claim (часть про 'определила/стала жизнь/карьеру'). Оставить factual content (год обучения, специальность, место).",
      "reason": "Class 1 recurring — causal claim не в источнике; pattern эволюционировал v62a→v63"
    },

    // NEW: episode_especially_remembered (multiplication of significance)
    {
      "category": "episode_especially_remembered",
      "pattern": "(один|какой[-\\s]?то|особенно)\\s+(эпизод|случа\\w+|момент|разговор|инцидент)\\s+\\w*\\s*(особенно|больше\\s+всего|навсегда|надолго|глубок\\w+)?\\s*(запомнил\\w+|остал\\w+\\s+в\\s+памяти|врезал\\w+\\s+в\\s+память|поразил\\w+)",
      "scope": ["ch_02", "ch_03", "ch_04"],
      "severity": "error",
      "suggestion": "Удалить subjective claim о memorability. Оставить factual content эпизода без оценки.",
      "reason": "Class 1 multiplication of significance — subjective claim 'особенно запомнился' не в источнике; новая форма v63"
    },

    // NEW: motivation_attribution_seemed
    {
      "category": "motivation_attribution_seemed",
      "pattern": "(ей|ему|им)\\s+(казал\\w+|представля\\w+|думал\\w+|показ\\w+)\\W{1,5}\\s+что\\s+\\w+\\s+(должн\\w+|обязан\\w+|следов\\w+|стоил\\w+)",
      "scope": ["ch_02", "ch_03", "ch_04"],
      "severity": "error",
      "suggestion": "Удалить attribution мотивации/мысли которой нет в источнике. Оставить factual content (что произошло), не догадки о причинах.",
      "reason": "Class 1 motivation confabulation — 'ей казалось что X должны Y' — psychic insight без подтверждения в transcripts; новая форма v63"
    },

    // NEW: stage_event_changed_X_extended (расширение task 043g)
    {
      "category": "stage_event_changed_X_extended",
      "pattern": "(произошл\\w+|случил\\w+|стал\\w+)\\s+(событи\\w+|переломн\\w+\\s+момент\\w+|важн\\w+\\s+поворот\\w+)[\\s\\S]{1,50}котор\\w+\\s+(измен\\w+|преобраз\\w+|перевернул\\w+|сильно\\s+повлия\\w+|серьёзно\\s+отразил\\w+)\\W{0,20}(жизн\\w+|сем\\w+|судьб\\w+)",
      "scope": ["ch_02", "ch_03"],
      "severity": "warning",
      "suggestion": "Удалить framing-фразу. Начинать с конкретного факта (год, событие, действующее лицо), не с abstract 'событие, которое изменило'.",
      "reason": "Class 6 narrative пафос extended — task 043g pattern эволюционировал v63 («сильно повлияло на семью» vs «изменило семейную жизнь»)"
    }
  ]
}
```

### 2. Snapshot tests (mandatory per lesson v62a)

`tests/test_class1_recurring_patterns.py`:

```python
def test_class1_speciality_defined_life_v62a():
    """v62a snapshot — original form (закрыт task 043d)."""
    sentence = (
        "В 1938 году Валентине дали специальность, "
        "которая определила всю её жизнь."
    )
    flags = validate_narrative_stop_phrases_for_sentence(sentence)
    assert any(f["category"] == "speciality_defined_life_v3" for f in flags)


def test_class1_speciality_defined_life_v63_recurring():
    """v63 snapshot — recurring form с 'дальнейшую жизнь в медицине'."""
    sentence = (
        "В 1938 году ей дали профессию акушерки — специальность, "
        "которая определила всю её дальнейшую жизнь в медицине."
    )
    flags = validate_narrative_stop_phrases_for_sentence(sentence)
    assert any(f["category"] == "speciality_defined_life_v3" for f in flags)


def test_class1_episode_especially_remembered_v63():
    """v63 snapshot — multiplication of significance."""
    sentence = (
        "Один эпизод особенно запомнился: когда Владимир работал со счётчиком, "
        "Валентина сделала ему замечание."
    )
    flags = validate_narrative_stop_phrases_for_sentence(sentence)
    assert any(f["category"] == "episode_especially_remembered" for f in flags)


def test_class1_motivation_attribution_seemed_v63():
    """v63 snapshot — motivation confabulation (огурцы новая форма)."""
    sentence = (
        "Валентина была недовольна — ей казалось, что родственники мужа "
        "должны присылать больше подарков."
    )
    flags = validate_narrative_stop_phrases_for_sentence(sentence)
    assert any(f["category"] == "motivation_attribution_seemed" for f in flags)


def test_class1_negative_factual_education():
    """Generic factual statement без causal claim — НЕ flag."""
    sentence = "В 1938 году Валентина поступила в Кировоградскую фельдшерско-акушерскую школу."
    flags = validate_narrative_stop_phrases_for_sentence(sentence)
    assert not any(f["category"].startswith("speciality_defined_life") for f in flags)


def test_class1_negative_factual_episode():
    """Factual episode без 'особенно запомнился' — НЕ flag."""
    sentence = "В 1977 году произошёл конфликт между Валентиной и зятем из-за счётчика."
    flags = validate_narrative_stop_phrases_for_sentence(sentence)
    assert not any(f["category"] == "episode_especially_remembered" for f in flags)
```

### 3. Integration в orchestrator (049f)

Existing `narrative_stop_phrases` validator уже подключён в orchestrator. Новые categories автоматически попадут в revision_hints.

Suggestion mapping в `_build_suggestion`:
- `speciality_defined_life_v3` → «Удалить causal claim. Оставить factual content.»
- `episode_especially_remembered` → «Удалить subjective claim о memorability.»
- `motivation_attribution_seemed` → «Удалить attribution мотивации без источника.»
- `stage_event_changed_X_extended` → «Удалить framing-фразу. Начать с факта.»

---

## Risk и mitigation

**Risk A: Pattern эволюция продолжается — v64 закроет 3 формы, v65 GW найдёт 4-ю.**

**Mitigation:**
- Этот task — **тактический backup**, не primary defense
- **Primary** = revision loop через GW v2.23 ПРАВИЛО 13 (task 049e). Validator flag → GW переписывает любую форму
- Pattern в validator — minimum coverage для detect, чтобы revision pass получил hint
- Per stocktake: цикл закрывается архитектурно (revision loop), не tactically (patterns)

**Risk B: False positives на factual sentences.**

**Mitigation:**
- Snapshot tests с negative cases (factual education/episode не flag)
- Severity error → GW обязан apply; если GW считает что factual content потеряется — suggestion позволяет переписать (не только delete)

**Risk C: Pattern complexity большой regex может match unintended.**

**Mitigation:**
- Калибровка на v63 артефактах перед deploy
- Snapshot tests должны pass: positive examples flagged + negative examples not flagged

---

## Ограничения

- [ ] Generic patterns, без subject-конкретики
- [ ] Lemma-aware (`\\w+` suffixes)
- [ ] Idempotent validator (existing `narrative_stop_phrases` validator extension)
- [ ] Severity error для recurring forms (task 043d уже error level)
- [ ] Snapshot tests mandatory (lesson v62a): 4+ tests, 2+ negative
- [ ] Scope = narrative chapters (НЕ ch_01)
- [ ] Cited speech (« ») — skip (existing logic в validator)

---

## Dev Review

**Статус:** ожидает

**[TECH]** — pre-answer от Опуса:
- `narrative_stop_phrases.json: v4 → v5` (4 новые/расширенные categories)
- Validator function существует (`validate_narrative_stop_phrases`) — config extension достаточен
- Suggestion field в каждой category — consumer orchestrator (049f)
- Калибровка regex на v63 артефактах **обязательна** перед commit
- Snapshot test для multi-pattern match (один sentence может match 2+ categories) — OK, оба flag

**[PRODUCT]** — нет

**Сложность:** `xs` (<1 ч — config extend + 6 snapshot tests)
**Риск:** `low` (config-only + tests; не trog существующий код)

---

## Verified-on-run v64

**Cursor:** [после v64] — `narrative_stop_phrases.json` results
**Опус:** независимо проверит:
- ✅ В v63 артефактах (input) 4 forms flagged
- ✅ В v64 артефактах (output) 0 этих forms (после revision pass)
- ✅ Snapshot tests PASS (6+)

---

## История

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-18 | `new` | Опус |
