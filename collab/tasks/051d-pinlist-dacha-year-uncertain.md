# Задача 051d: Pin-list ep_029 — продажа дачи year уточнение или remove year attribution

**Статус:** `new`
**Номер:** 051d
**Автор:** Опус (роль архитектор+продакт)
**Дата создания:** 2026-05-18
**Тип:** pin-list edit (конфиг)
**Sprint:** v63
**Связано:** known_episodes_karakulina.md v4 ep_029 («Продажа дачи 1990-е, Валентина жалела, тётя Маша повлияла»); Никитин live review v62a — «семья продала дачу в 1990-е» — год возможно неточный

---

## Контекст

В `known_episodes_karakulina.md` v4 ep_029:
```
| 29 | ep_029 | **Продажа дачи 1990-е, Валентина жалела, тётя Маша повлияла** | 1990-е |
  TR2 | `продал.*дач\|дач.*продал`, `жалела` | ❌ потеряно |
  TR2: «Жалела, наверное, что дачи не было...»
```

Никита в v62a feedback (#4) уточнил: год возможно неточный — в TR2 нет конкретной даты, «1990-е» — рассказчик-внук (Никита) **предполагает period**, не помнит точно.

Это **pin-list ошибка attribution**, не narrative ошибка. Pin-list указывает «1990-е» как factual — GW потом использует как factual claim. Лучше:
- Либо уточнить (если рассказчик может вспомнить и Никита подтвердит)
- Либо **снять year attribution** — pin-list `year` поле для ep_029 → `unknown`, и в narrative period не указывать

**Класс:** **узкий конкретный fix** (pin-list edit, не algorithm) — не universal class, но важный для качества v63.

---

## Universality check

- [x] Промпт — n/a
- [x] Subject-specific — да, ep_029 — Каракулино-специфичная запись pin-list. Но **mechanism** «когда year attribution unsure → mark unknown» — универсален для любого pin-list.
- [x] Алгоритм generic — pin-list parser уже поддерживает years `unknown` / `~1990-е` / точные year
- [x] Subject-replacement test — для Корольковой/Дмитриева pin-list edit делается аналогично если нужно ✅

**Trap warning:** конкретное правило для дачи Каракулиной — это **тактика**, не архитектура. Архитектурный wrapper: «pin-list events с uncertain year маркируются `year: "unknown"` или `year_confidence: low` → GW не использует year в narrative». Это **универсально**. Spec ниже даёт **оба** — конкретный edit для ep_029 + generic convention для будущих pin-list edits.

---

## Спек

### Что нужно изменить

### 1. Generic convention: pin-list year confidence

**`collab/context/known_episodes_<subject>.md`** — для эпизодов где year неточен, использовать:
- `year: "unknown"` — нет данных в источнике
- `year: "~1990-е"` или `year: "1990-е (по предположению рассказчика)"` — period известен, но рассказчик неуверен

### 2. Конкретный edit ep_029

В `known_episodes_karakulina.md` v4 → v5:

Old (v4):
```
| 29 | ep_029 | **Продажа дачи 1990-е, Валентина жалела, тётя Маша повлияла** | 1990-е | TR2 | ...
```

New (v5):
```
| 29 | ep_029 | **Продажа дачи (год неточен), Валентина жалела, тётя Маша повлияла** | unknown | TR2 | `продал.*дач\|дач.*продал`, `жалела` | ❌ потеряно | TR2: «Жалела, наверное, что дачи не было. ... тетя Маша, наверное, тут сыграла свою роль» (год не упомянут рассказчиком) |
```

И в hints для GW: «продажа дачи — без указания года; рассказывать о факте + сожалении + влиянии тёти Маши, не привязывая к 1990-м».

### 3. Pin-list parser support for `year: "unknown"`

**`pipeline_utils.py`** — `parse_pin_list_from_markdown`:
- Если year cell `unknown` / `~неточен` / содержит явный uncertainty marker (`~`, `по предположению`, `возможно`) → `episode.year_confidence = "unknown"` или `"low"`
- Если `year_confidence == "unknown"` → GW prompt PIN_LIST_EVENTS блок указывает «year unspecified — не упоминай конкретный год в narrative»

Конкретный формат в `PIN_LIST_EVENTS` block:
```yaml
- episode_id: ep_029
  description: Продажа дачи (год неточен), Валентина жалела, тётя Маша повлияла
  year: unknown
  year_hint: НЕ ПИСАТЬ КОНКРЕТНЫЙ ГОД В НАРРАТИВЕ
  source_quote: ...
```

### 4. (Опционально) Validator

`validate_pin_list_year_drift` — если в narrative для эпизода с `year_confidence: unknown` появляется конкретный year (`в 1990 году`, `1995 году`, etc.) в нужном paragraph → flag `unauthorized_year_attribution` warning.

### Какой результат ожидается

В v63:
- `known_episodes_karakulina.md` v5 содержит ep_029 с `year: unknown`
- GW narrative ch_03/ch_04 раскрывает продажу дачи **без** упоминания «1990-е» или конкретного года (или упоминает с маркером «вероятно», если рассказчик так формулировал)
- pin-list parser correctly handles `year: unknown`
- Optional: `style_checks.json` warning если GW написал конкретный год для unknown episode

### Как проверить

1. **Unit-тесты** `tests/test_pin_list_year_confidence.py`:
   - parse_pin_list with `year: "unknown"` → `episode.year_confidence == "unknown"`
   - parse_pin_list with `year: "~1990-е"` → `episode.year_confidence == "low"`
   - parse_pin_list with `year: "1962"` → `episode.year_confidence == "high"`

2. **Integration** на v62a:
   - Загрузить v5 known_episodes_karakulina.md → ep_029 year_confidence=unknown
   - PIN_LIST_EVENTS block для GW содержит `year: unknown` + hint

3. **Verified-on-run** v63:
   - Открыть `karakulina_v63_text_FULL.md` — продажа дачи раскрыта (Никита недавно отмечал что эпизод missed); year **не зафиксирован** как «1990-е» если рассказчик не подтверждал

---

## Ограничения

- [ ] **Generic convention** `year_confidence` — для любого subject pin-list
- [ ] **Не удалять эпизод** — только переразметить year
- [ ] **Idempotent** parser
- [ ] **GW prompt не меняется** (используется только PIN_LIST_EVENTS input block, который уже есть с task 041)
- [ ] **Validator опционален** — если не реализуется в v63, всё равно pin-list edit полезен

---

## Dev Review

**Статус:** ожидает

**[TECH]** — pre-answer от Опуса:
- `year: "unknown"` — литеральная строка в pin-list markdown; parser распознаёт case-insensitive
- year_confidence levels: `high` (точный year), `low` (~1990-е, period), `unknown` (нет данных)
- В PIN_LIST_EVENTS input для GW — explicit hint строка «НЕ ПИСАТЬ КОНКРЕТНЫЙ ГОД»; GW v2.20 уже использует hints

**[PRODUCT]** — нет (Никитино решение «год неточен» — pin-list edit отражает это)

**Сложность:** `xs` (<1 ч)
**Риск:** `low` (pin-list edit, parser extension)

---

## Verified-on-run

**Cursor:** [после v63]
**Опус:** независимо проверит — в narrative ch_03/ch_04 продажа дачи присутствует, конкретный год **не** упомянут (или явно отмечен как «возможно»)

---

## История

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-18 | `new` | Опус |
