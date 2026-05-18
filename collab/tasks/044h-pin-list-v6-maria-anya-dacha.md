# Задача 044h: Pin-list v6 — Мария + баба Аня в required_persons + ep_029 уточнение «дача раньше 1990-х»

**Статус:** `new`
**Номер:** 044h
**Автор:** Опус (роль архитектор+продакт)
**Дата создания:** 2026-05-18
**Тип:** pin-list edit (конфиг)
**Sprint:** v64
**Связано:** task 044b (required_persons mechanism); task 051d (year_confidence convention); v63 regression Мария + баба Аня выпали из bio_data.family; Никитин feedback v63 «дача продана раньше [1990-х]»

---

## Контекст

**Class 5 regression v63:**
- v59, v61, v62a: bio_data.family = 23 (включая Мария + баба Аня)
- **v63: 21** — Мария и баба Аня выпали

Курсор сам в VERIFIED_ON_RUN_v63 написал: «Мария и баба Аня — 2 критических персоны не вошли в нарратив. Добавлены в auto_enrich CA, но GW не развернул. **Кандидаты для pin_list v6 / required_persons**».

**ep_029 «продажа дачи» уточнение Никиты:**

В Pin-list v5 (task 051d) ep_029 был помечен `year=unknown` (year_confidence=low), описание «Продажа дачи (год неточен)». **Никитин feedback v63:** «дача была продана раньше — В 1990-е годы семья продала дачу, что очень расстроило Валентину».

То есть **TR не подтверждает 1990-е** — Никита помнит **раньше**. Нужно либо confirm/uncertain с явным marker «раньше 1990-х», либо узнать у TR более конкретный year. В v6 — конкретизировать что **«до 1990-х»** более точно.

---

## Universality check

- [x] Промпт — n/a (pin-list edit)
- [x] Subject-specific — да, pin-list — per subject. Generic mechanism `required_persons` уже есть (task 044b)
- [x] Алгоритм generic — encforce_required_persons работает с любым subject
- [x] Subject-replacement test — для других subjects pin-list pattern works ✅

---

## Спек

### 1. Pin-list edit `known_episodes_karakulina.md` v5 → v6

**Изменения:**

#### A. Раздел «Прямые родственники» — explicit required_persons markers

Текущий формат:
```markdown
- **Старшая сестра:** Мария (тётя Маня), **разный отец с Валентиной**
- **Бабушка:** Марфа (мать отца Валентины)
```

Расширить с явными `required_in_bio_data_family: true` markers:

```markdown
### Прямые родственники Валентины (whitelist OK)

> required_in_bio_data_family: true — обязательно в bio_data.family, force-add
> через `enforce_required_persons` если CA/GW пропустит.

- **Отец:** Рудай Иван Андреевич, плотник (ушёл на заработки в 1933) [required_in_bio_data_family]
- **Мать:** Рудая Пелагея Алексеевна, работница колхоза (ум. 1933) [required_in_bio_data_family]
- **Младший брат:** имя неизвестно, умер в детстве [required_in_bio_data_family]
- **Старшая сестра:** Полина (тётя Поля, фамилия в браке — **Амельченко**) — забрала из детдома, **разный отец с Валентиной** [required_in_bio_data_family]
- **Старшая сестра:** Мария (тётя Маня), **разный отец с Валентиной** [required_in_bio_data_family] ⭐ **v6 fix: force-add**
- **Бабушка:** Марфа (мать отца Валентины) [required_in_bio_data_family]
- **Муж:** Каракулин Дмитрий, военный (ум. 1978) [required_in_bio_data_family]
- ...
```

#### B. Раздел «Баба Аня» — корректная классификация

Баба Аня — **свекровь рассказчика (Татьяны)**, не Валентины. Не в bio_data.family Валентины — но в narrative должна быть как comparison-context («французская бабушка» в ch_03 эпизоде, существующий в v59).

Текущий relation_overrides:
```markdown
| **Баба Аня** | "свекровь или родственница зятя" | **свекровь рассказчика (мать Владимира Маргось)** | НЕ в family Валентины. В narrative ch_03 как контекст «французская бабушка» comparison. |
```

Расширить с **`narrative_required: true`** marker — она не в bio_data.family, но **обязательна в narrative** (Class 5 regression v63 — её упустили вообще):

```markdown
| **Баба Аня** | ... | ... | НЕ в family Валентины. **narrative_required: true в ch_03** (comparison contrast «французская бабушка», существующий эпизод TR2). |
```

#### C. ep_029 уточнение «дача раньше 1990-х»

Текущая запись v5:
```markdown
| 29 | ep_029 | **Продажа дачи (год неточен), Валентина жалела, тётя Маша повлияла** | unknown | TR2 | ... | TR2: «Жалела, наверное, что дачи не было. ...» (год не упомянут рассказчиком) |
```

v6 уточнение:
```markdown
| 29 | ep_029 | **Продажа дачи (до 1990-х по уточнению Никиты), Валентина жалела, тётя Маша повлияла** | before_1990s | TR2 | `продал.*дач\|дач.*продал`, `жалела` | ❌ потеряно v63 | TR2: «Жалела, наверное, что дачи не было. ... тетя Маша, наверное, тут сыграла свою роль». Уточнение Никиты v63: «дача была продана раньше [не 1990-е, точный год TR не указывает, период ~1980-е]» |
```

`year_confidence` остаётся `low` (точный year не подтверждён), но **direction** известен: `before_1990s`. Validator может flag если GW напишет «в 1990-е продали».

### 2. Required_persons mechanism integration

Существующий `enforce_required_persons` (task 044b) уже force-add'ит в bio_data.family. **Нужна проверка** что в v64 он применяется к Марии + бабе Ане:
- Мария: relation_to_subject = «старшая сестра» (whitelist OK) → force-add автоматически после parser parse `[required_in_bio_data_family]` marker
- Баба Аня: relation_to_subject = «свекровь рассказчика» (НЕ whitelist) → НЕ force-add в bio_data.family, **но** включается в `narrative_required_persons` list для CA pin-list

### 3. Narrative_required_persons mechanism (новое)

Опционально мини-extension: новая category в CA pin-list `narrative_required_persons` — persons которые НЕ в bio_data.family (по relation), но **обязательны в narrative**.

CA при auto_enrich добавляет их в fact_map.persons. GW использует их в narrative.

Implementation в `pipeline_utils.py` — `parse_pin_list_from_markdown` распознаёт marker `narrative_required: true` в relation_overrides:

```python
def parse_pin_list_narrative_required_persons(md: str) -> list[dict]:
    """Parse persons with narrative_required: true marker (not in bio_data.family but in narrative)."""
    ...
```

В Stage 1 CA enrichment — если person matches narrative_required → flagged в fact_map.persons как `narrative_required: true`. GW v2.23 при revision видит это и обязан включить в narrative (ПРАВИЛО 13 — если validator flag «person_missing_in_narrative» → revision).

### 4. Validator для narrative_required (опционально, не обязательно в v64)

`validate_narrative_required_persons` — проверка что все narrative_required persons упомянуты ≥1 в narrative. Flag warning если нет.

В v64 — **опционально**. Если в v64 sprint scope позволит — реализовать; если нет — backlog v65.

### 5. ep_029 year_confidence parser support

Existing `parse_pin_list_year_field` (task 051d) поддерживает `unknown` / `~1990-е` / точные year. Расширить на directional markers:
- `before_1990s` → `year_confidence: "low"`, `year_range: "(unknown, 1990)"`, `year_direction: "before"`
- `after_2000` → `year_range: "(2000, unknown)"`, `year_direction: "after"`

В PIN_LIST_EVENTS input для GW v2.23 — explicit hint:
```yaml
- episode_id: ep_029
  description: Продажа дачи, Валентина жалела, тётя Маша повлияла
  year: unknown
  year_direction: before_1990s
  year_hint: "НЕ ПИСАТЬ '1990-е' (по уточнению — раньше); если нужен temporal hint, использовать 'в 1980-е' или 'до перестройки' с маркером уверенности"
  source_quote: ...
```

---

## Risk и mitigation

**Risk A: Мария — relation «старшая сестра» — может уже быть в whitelist, force-add не нужен.**

**Mitigation:**
- Check existing task 044b логику: force-add работает даже если уже в whitelist (idempotent)
- В v63 Мария **выпала** — значит CA не distinguish, не added к fact_map. required_persons marker → CA добавляет в auto_enrich

**Risk B: Баба Аня — relation НЕ в whitelist (свекровь рассказчика). bio_data.family — корректно НЕ.**

**Mitigation:**
- narrative_required mechanism — отдельный path; bio_data filtering не trigger'ится
- v63 проблема — vatable была вообще missing в narrative (не только в bio_data). v6 force-add в narrative через CA pin-list

**Risk C: ep_029 «before_1990s» — слишком vague для GW.**

**Mitigation:**
- Year_hint explicit: «НЕ ПИСАТЬ '1990-е'» — GW не нарушит prohibition
- Если GW напишет конкретный год — validator (расширение `validate_pin_list_year_drift` если нужно) flag warning
- Revision pass переписывает

**Risk D: `narrative_required` mechanism — новый flow, может ломаться.**

**Mitigation:**
- v64 sprint — реализация **минимальная**: pin-list edit + CA pin-list flag + GW awareness через PIN_LIST_EVENTS hint
- Validator `validate_narrative_required_persons` — **опционально**, backlog v65 если v64 insufficient

---

## Ограничения

- [ ] Pin-list — subject-specific (Каракулина); mechanism generic
- [ ] `[required_in_bio_data_family]` marker — works through existing 044b mechanism
- [ ] `narrative_required: true` marker — new, but minimal (pin-list edit + CA hint)
- [ ] ep_029 `year_direction: before_1990s` — parser extension (task 051d расширение)
- [ ] year_hint в PIN_LIST_EVENTS — input format extension, NO GW prompt change

---

## Dev Review

**Статус:** ожидает

**[TECH]** — pre-answer от Опуса:
- Pin-list edit — main task (markdown changes)
- `parse_pin_list_year_field` extension для `before_X` / `after_X` markers
- `narrative_required_persons` parser — небольшое extension существующего pin-list parsing
- CA pin-list integration — auto_enrich flag `narrative_required: true`
- GW input format — `year_direction` field в PIN_LIST_EVENTS

**[PRODUCT]** — Никитин confirm by feedback v63 (Мария/баба Аня + дача раньше)

**Сложность:** `s` (1-3 ч — pin-list edit + parser + integration tests)
**Риск:** `low` (mostly config + minor parser extensions; mechanism 044b already exists)

---

## Verified-on-run v64

**Cursor:** [после v64] — `pin_list_compliance.json` + bio_data.family
**Опус:** независимо проверит:
- ✅ bio_data.family содержит «Старшая сестра — Мария»
- ✅ Narrative ch_02 или ch_03 содержит упоминание Марии (как старшей сестры)
- ✅ Narrative ch_03 содержит баба Аня как «французская бабушка» comparison
- ✅ Narrative не упоминает дачу в «1990-е» — либо «до 1990-х», либо без attribution

---

## История

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-18 | `new` | Опус |
