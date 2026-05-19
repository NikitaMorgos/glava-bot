# Задача 044i: Pin-list v6 → v7 — required_in_narrative + required_episodes mechanism + Капошвара verify

**Статус:** `new`
**Номер:** 044i
**Автор:** Опус
**Дата создания:** 2026-05-19
**Тип:** pin-list edit + scripted mechanism + GW input wire
**Sprint:** v65
**Связано:** task 044/044b/044c/044h (required_persons mechanism); Никитин feedback v64 — грибы/ягоды/тётя Маша/дача потерялись; «улица Капошвара» = ошибка, должна быть «площадь»

---

## Контекст

В v64 потерялись из narrative:
- Грибы/ягоды (byt_009)
- Тётя Маша-соседка (связана с грибами)
- Продажа дачи (ep_029)
- Полина «забрала из детдома» — в bio_data есть, но в narrative нет detail

Mechanism `required_persons` (task 044b) работает для **bio_data.family** — force-add person в семью. **Аналогичного mechanism для эпизодов нет** — pin-list указывает «должно быть в narrative», GW игнорирует, validator не enforce.

Также Никита заметил **factual error v64**: «улица Капошвара» — на самом деле **площадь**. В pin-list v6 ep_028 — проверить. Если в pin-list корректно «площадь» — это GW drift (Class 1). Если в pin-list «улица» — pin-list edit.

Кроме того: текущая метрика «Episodes full 14/67 / partial 7 / skipped 46» **непонятна** (Никитин вопрос). Решение: добавить marker `required_in_narrative: true` для obligatory episodes — build_gate1 покажет «Required: 12/14 covered, missing: грибы, дача» (понятно).

---

## Pre-sprint checklist

- [x] Stocktake актуален
- [x] Critical reading — v64 narrative + v6 pin-list проверены, missing episodes verified, Капошвара status TBD
- [x] Universality — pin-list per subject (правильно); mechanism generic
- [x] Защита подключена — да, через orchestrator → required_episodes hint → GW
- [x] Прогон раздельный — combined в v65 bugfix sprint OK
- [x] Класс — Class 5 «episode regression» (generic) + новый mechanism `required_episodes`
- [x] Скрипт-first — да (parser extension + new validator)

---

## Спек

### 1. Pin-list v7 — добавить `required_in_narrative` marker

В `known_episodes_karakulina.md` v7 — для каждой записи в секциях `Хронологические эпизоды` и `Бытовые эпизоды`:

Текущий формат:
```markdown
| 17 | ep_017 | Дача появилась в 60-х | 1960-е | TR1 | ... | ✅ | ... |
```

Новый формат — добавить колонку **`req`** (required_in_narrative):

```markdown
| 17 | ep_017 | Дача появилась в 60-х | 1960-е | TR1 | ... | ✅ | **REQ** | ... |
| 29 | ep_029 | **Продажа дачи (до 1990-х по уточнению Никиты)** | before_1990s | TR2 | ... | ❌ | **REQ** | ... |
| B9 | byt_009 | **Не любила грибы/ягоды; тётя Маша-соседка любила** | TR1 | ... | ❌ | **REQ** | ... |
```

Колонка `REQ` = `true` если эпизод **обязателен** в narrative. По умолчанию `false` (для antitriggers, контрольных anchors, мелких деталей).

### 2. Required_episodes mechanism

Parser `parse_pin_list_episodes` recognizes new column `req`, возвращает field `required_in_narrative: true|false`.

Новый валидатор `validate_required_episodes_coverage`:

```python
def validate_required_episodes_coverage(book, pin_list, config=None):
    """Check что required_in_narrative episodes присутствуют в narrative.

    Algorithm:
    1. Extract required episodes from pin_list (where required_in_narrative == true)
    2. For each — search в narrative chapters by markers (existing 'Маркеры для grep' column)
    3. If not found OR partial (< min_mentions, default 1) — flag error

    Output (включается в orchestrator):
    {
      "required_episodes": [
        {"episode_id": "ep_017", "title": "Дача", "found": true, "mentions": 2, "chapter": "ch_02"},
        {"episode_id": "ep_029", "title": "Продажа дачи", "found": false, "severity": "error"},
        {"episode_id": "byt_009", "title": "Грибы/ягоды", "found": false, "severity": "error"},
      ],
      "covered_count": N,
      "total_required": M,
      "issues": [...]
    }
    """
```

Suggestion для GW (через orchestrator hint):
```
Episode [ep_029] «Продажа дачи» — required_in_narrative, отсутствует в text.
Развернуть в ch_03 или ch_04 на ≥3 sentences с маркером из pin-list ([sample marker]).
Source quote: «[from pin-list]».
```

### 3. Капошвара verify + fix если нужно

Открыть `known_episodes_karakulina.md` v6 запись ep_028:
```
| 28 | ep_028 | Татьяна замуж за Кужбу Олега, переезд на площадь Капошвара 1996 | 1996 | ... | `Кужб`, `1996`, `Капошвар` | ✅ |
```

✅ В v6 уже **«площадь Капошвара»**. То есть GW v64 написал «улица Капошвара» — это GW drift (Class 1 named entity).

Action:
- В v7 pin-list — **подтвердить** «площадь Капошвара» (явная пометка)
- В `entity_substitution` validator (existing) — добавить snapshot test «улица Капошвара» → должна flag как drift
- Добавить snapshot pattern «улица\s+Капошвар» → suggestion «replace 'улица' → 'площадь'»

```python
# В entity_substitution validator или narrative_stop_phrases:
{
  "category": "place_misnaming_kaposhvara",
  "pattern": "улиц\\w+\\s+Капошвар",
  "scope": ["ch_02", "ch_03", "ch_04", "epilogue"],
  "severity": "error",
  "suggestion": "Заменить 'улица Капошвара' → 'площадь Капошвара' (TR2 + pin-list: ep_028)",
  "reason": "Class 1 named entity drift — Капошвара это площадь, не улица"
}
```

### 4. GW input wire — передавать `required_episodes` явно

В Stage 2 input GW receive `pin_list_episodes` фильтрованный по `required_in_narrative=true` — как **highest priority** episodes. Не просто весь pin-list, а **required subset** с пометкой «обязательно развернуть ≥3 sentences» (ПРАВИЛО 12 GW v2.22+).

Это — input format change, **не** GW prompt change.

### 5. Build_gate1 enhancement (часть task build_gate1)

Build_gate1 summary вместо текущего:
```
Pin-list coverage:
- Episodes full: 14 / 67
- Episodes partial: 7 / 67
- Episodes skipped: 46 / 67
```

Показывает:
```
Pin-list coverage:
- Required in narrative: 12 / 14 covered ⚠️
  - Missing (2): byt_009 «грибы/ягоды», ep_029 «продажа дачи»
- Optional episodes: 9 / 53 mentioned (informational)
```

Это понятнее и actionable.

### 6. Snapshot tests

`tests/test_required_episodes.py`:

```python
def test_required_episode_missing_flag():
    """ep_029 required, отсутствует в book → flag error."""
    pin_list = [{"episode_id": "ep_029", "title": "Продажа дачи", "markers": ["продал.*дач"], "required_in_narrative": True}]
    book = {"chapters": [{"id": "ch_02", "content": "Текст без упоминания дачи."}]}
    result = validate_required_episodes_coverage(book, pin_list)
    assert result["covered_count"] == 0
    assert any(i["category"] == "missing_required_episode" for i in result["issues"])


def test_required_episode_present_ok():
    """ep_017 required, упомянут в book → no flag."""
    pin_list = [{"episode_id": "ep_017", "title": "Дача 60-х", "markers": ["дач"], "required_in_narrative": True}]
    book = {"chapters": [{"id": "ch_02", "content": "В 60-х появилась дача."}]}
    result = validate_required_episodes_coverage(book, pin_list)
    assert result["covered_count"] == 1
    assert not any(i["category"] == "missing_required_episode" for i in result["issues"])


def test_optional_episode_not_flagged():
    """ep with required=false, отсутствует → no flag."""
    pin_list = [{"episode_id": "byt_012", "title": "Шляпки", "markers": ["шляпк"], "required_in_narrative": False}]
    book = {"chapters": [{"id": "ch_02", "content": "Текст без шляпок."}]}
    result = validate_required_episodes_coverage(book, pin_list)
    assert not result["issues"]  # optional — no flag


def test_kaposhvara_ulitsa_drift():
    """v64 example: 'улица Капошвара' → entity_substitution flag."""
    sentence = "Они переехали на улицу Капошвара в 1996 году."
    flags = validate_narrative_stop_phrases_for_sentence(sentence)  # либо entity_substitution
    assert any(f["category"] == "place_misnaming_kaposhvara" for f in flags)
```

### 7. Применение required_in_narrative — какие episodes mark в v7

После критического чтения v64 + Никитин feedback — обязательные в narrative:

**Хронологические (минимум):**
- ep_001 Голод 1933 (мать + брат + отец)
- ep_005 Свадьба 1946
- ep_006 Документы вокзала
- ep_007 Германия 1946-48
- ep_008 Валерий 1948
- ep_009 Татьяна 1956
- ep_011 Операция желудок 1960
- ep_012 Валерий у тёти Шуры 1961
- ep_013 Сахалин-развилка 1962
- ep_014 Химинститут
- ep_015 Татьяна в детский сад №95
- ep_016 Поликлиника
- ep_017 Дача в 60-х
- ep_018 Ударник 1965
- ep_022 Счётчик 1977 (зять)
- ep_023 Смерть Дмитрия 1978
- ep_024 Огурцы Молдавия
- ep_027 Пенсия 1994
- ep_028 Кужба + площадь Капошвара 1996
- ep_029 **Продажа дачи** (Никитин блокер v64)

**Бытовые (минимум):**
- byt_001 Шуба → пианино
- byt_004 Авоська из зонтика
- byt_007 Сервиз немецкий
- byt_008 Хор в Венгрии
- byt_009 **Грибы/ягоды + тётя Маша-соседка** (Никитин блокер v64)
- byt_010 Нинвана-врач
- byt_015 Карты и домино
- byt_017 «На дорожку»

Остальные — `required_in_narrative: false` (optional).

---

## Universality check

- [x] Промпт — n/a (input format extension)
- [x] Subject-specific — pin-list per subject (правильно)
- [x] Algorithm generic — required_episodes mechanism works для любого subject
- [x] Subject-replacement — для Корольковой свой pin-list с её `req` markers ✅

---

## Ограничения

- [ ] Pin-list `req` column — opt-in (default false)
- [ ] Validator detect только missing required — не trog optional
- [ ] Капошвара flag — generic «place_misnaming_X» pattern, не Каракулино-specific только Капошвара
- [ ] Snapshot tests
- [ ] GW input wire — additional metadata, не prompt change

---

## Dev Review

**Статус:** ожидает

**[TECH]** — pre-answer от Опуса:
- Pin-list parser extend для `req` column
- Новый `validate_required_episodes_coverage` в `pipeline_utils.py`
- GW input — добавить `required_episodes` blocked separately в PIN_LIST_EVENTS block
- entity_substitution validator — add Капошвара pattern (или narrative_stop_phrases)

**[PRODUCT]** — нет (Никитин feedback v64)

**Сложность:** `s` (1-3 ч — pin-list edit + parser + validator + tests + GW input wire)
**Риск:** `low`

---

## Verified-on-run v65

**Cursor:** [после v65]
**Опус:** независимо проверит:
- В narrative ch_03 либо ch_04 — упоминание грибов/ягод + тётя Маша
- В narrative — упоминание продажи дачи (с маркером «до 1990-х»)
- Нет «улицы Капошвара» (заменено на «площадь Капошвара»)
- Build_gate1 summary — «Required: N/M covered, missing: [...]»
- `required_episodes_coverage.json` — issues для missing required

---

## История

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-19 | `new` | Опус |
