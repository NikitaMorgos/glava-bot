# Задача 038: CA v1.3 — strict description + relation_to_subject + confabulation guards

**Статус:** `new` (полный spec после v57; ранее outline)
**Номер:** 038
**Автор:** Опус (роль архитектор+продакт)
**Дата создания:** 2026-05-17
**Тип:** `промпт` (CA) + `cco-скрипт` (валидация)
**Batch:** 2 (после v57 verified)
**Связано:** stocktake 2026-05-17 **Класс 1** (CA/GW confabulation); pin-list v2 «Антитриггеры»

---

## Контекст

**Класс 1 — CA/GW confabulation** проявился в v56-v57 в нескольких формах:

### Подкласс 1a — CA description ≠ source_quote (огурцы v56)

CA event_auto_009 (огурцы) `description`:
> «Это произошло потому, что Валентина критиковала Владимира за то, что он не привозит достаточно подарков из Молдавии.»

`source_quote`:
> «Однажды папаша привез чемодан огурцов в заграничном чемодане... Я выкинула, это потому что испортились.»

CA сам выдумал причинную связку «потому что не привозит подарки». GW v56 переписал как факт.

### Подкласс 1b — CA misattribution relation_to_subject

CA лейблит:
- «тётя Маша» (соседка) → `relation_to_subject="тётя"` (потому что рассказчик так называет)
- «Баба Аня» (свекровь Татьяны) → `relation_to_subject="свекровь или родственница зятя"` (формулировка размыта)

Это попадает в bio_data.family как родственники Валентины — **task 044 фиксит на этапе пост-обработки**, но **корень — в CA extraction**.

### Подкласс 1c — GW historical overgeneralization

v57 GW добавил historical_note без основания:
> «В 1990-е многие пожилые люди оставались одни в больших квартирах — дети разъезжались, а содержать жильё становилось всё дороже.»

Этого нет в источнике; это **GW социология**.

### Подкласс 1d — GW confabulation мотивации

v57 epilogue:
> «верила в советскую власть и идеалы, **за которые воевала**»

Реально Валентина воевала «за родину в безвыходной ситуации», не за идеалы. Это **атрибуция мотивации без подтверждения**.

### Подкласс 1e — GW confabulation контекста

v57: «Перед отъездом в дальнюю дорогу семья соблюла старый обычай — «посидели на дорожку».»

TR1/TR2 говорят про общую семейную традицию, **не привязывают к конкретному отъезду 1946**. GW додумал контекст.

### Подкласс 1f — частный пример вместо обобщения (**Класс 11**)

v57: «Владимир не любил, когда ему давали советы по электричеству или поездкам»

Реально: Владимир не любил советов в принципе; электричество и поездки — примеры. См. task 043 — этот подкласс адресуется там же.

---

## Спек

### Что нужно изменить / создать

**1. Промпт Completeness Auditor v1.3** (правка `prompts/completeness_auditor_v1.2.md` → `v1.3.md`):

Новый раздел в системном промпте:

```
### ПРАВИЛО 4 — STRICT DESCRIPTION (description = парафраз source_quote)

При формировании поля `description` в timeline / character_traits / quotes:

**ОБЯЗАТЕЛЬНО:**
- description должна быть парафразом source_quote — те же факты, теми же словами или синонимами
- допускается лёгкая перефразировка для читаемости (например, оборот «получается» убирать)

**ЗАПРЕЩЕНО:**
- добавлять причинно-следственные связки которых нет в source_quote (фразы «потому что», «это произошло так как», «из-за этого», если их нет в source)
- добавлять новые даты, годы, имена, локации которых нет в source_quote
- атрибутировать мотивы или психологические состояния которых нет в source (не «Валентина критиковала, потому что хотела...», если этого нет в источнике)
- объединять 2 разных эпизода в один description (даже если оба про одну персону)

**ПРАВИЛО 5 — STRICT relation_to_subject**

При определении `relation_to_subject` для persona:

- использовать **только** прямое родственное определение из транскрипта или fact_map
- если рассказчик называет «тётя X» — это **обращение**, не обязательно родственная связь; нужно подтверждение что это реально тётя (например: «сестра моей мамы»)
- если связь неясная — использовать `relation_to_subject="знакомый\|соседка\|коллега\|подруга"` (НЕ родственные категории)
- **запрещено**: применять родственный термин только потому что рассказчик использует обращение
```

**2. Скрипт `validate_description_drift(audit_data) -> report`** в `pipeline_utils.py` (post-CA):

```python
def validate_description_drift(audit_data: dict) -> dict:
    """
    Проверяет CA description vs source_quote на признаки confabulation.

    Возвращает:
    {
      "issues": [
        {"event_id": "...", "type": "causal_drift|date_drift|name_drift|motivation_drift", ...},
        ...
      ],
      "events_checked": N,
      "events_flagged": M
    }
    """
```

Алгоритм проверки на event:
1. **Causal drift**: regex `\bпотому что\b|\bпоскольку\b|\bтак как\b|\bиз-за этого\b|\bэто произошло\b` в description
   - Если найден → проверить regex в source_quote
   - Если в source отсутствует → flag `type="causal_drift"`
2. **Date drift**: extract years (regex `\b(19|20)\d{2}\b`) из description; same из source_quote
   - Если в description есть year которого нет в source → flag `type="date_drift"`
3. **Name drift**: extract capitalized names (regex `\b[А-Я][а-я]+\b`) из description vs source
   - Если в description есть имя которого нет в source AND нет в fact_map.persons → flag `type="name_drift"`
4. **Motivation drift**: regex `\bхотел\b|\bжелал\b|\bмечтал\b|\bстремил\b|\bверил\b` (только в форме приписывания мотивации субъекту)
   - Если в description есть, но в source отсутствует → flag `type="motivation_drift"`

**3. Скрипт `validate_relation_consistency(fact_map, transcript) -> report`** в `pipeline_utils.py` (post-CA):

```python
def validate_relation_consistency(fact_map, transcript_text) -> dict:
    """
    Проверяет relation_to_subject persons vs прямое родственное упоминание в transcript.
    """
```

Алгоритм:
1. Для каждого person с relation_to_subject ∈ {тётя, дядя, бабушка, дедушка, племянник, племянница, золовка, свекровь, тесть, тёща, кум, кума, свояк, золовка}:
   - Найти в transcript предложение где есть persona.name **+** слово из родственного определения («сестра моей мамы», «брат отца», «мать мужа», и т.п.)
   - Если найдено → confidence relation OK
   - Если **не найдено** → flag `type="unconfirmed_relation"` с предложением `suggested_relation="знакомый/соседка/контекст_неясен"`

**4. Скрипт `validate_historical_note_grounding(book, fact_map, transcripts) -> report`** в `pipeline_utils.py` (post-GW Stage 2):

Алгоритм:
1. Для каждого `historical_notes[]` и каждого inline `***...***` блока в нарративе:
   - Извлечь утверждения (предложения)
   - Проверить general claim patterns: «многие», «обычно», «в те годы», «в 1990-е/советское время... все/часто/часто»
   - Если claim — general statement про эпоху/контекст без конкретного подтверждения → flag `type="generalization_unverified"` с reason
   - Известные verified исторические факты (голодомор, чёрный вторник, ленинский день — из pin-list `historical_notes_anchors`) — PASS
   - Антитриггеры из pin-list v2 («1990-е многие пожилые остаются одни» и т.п.) — explicit FAIL

**5. Скрипт `validate_motivation_attributions(book, transcripts) -> report`** в `pipeline_utils.py` (post-GW):

Алгоритм:
1. Поиск regex в narrative chapters: `\b(верила в|воевала за|хотела|стремила|жила ради|посвятила себя)\s+\S+`
2. Для каждого match:
   - Извлечь motivation phrase
   - Проверить direct match в transcripts (точное или близкое)
   - Если в transcript отсутствует → flag `type="motivation_attribution_unverified"`
3. Известные verified motivations (из pin-list — например «работящая, не наслаждающаяся» — это сама Валентина говорила) — PASS

**6. Интеграция в Stage 1 / Stage 2**:
- После CA: `validate_description_drift` + `validate_relation_consistency`
- После GW Stage 2: `validate_historical_note_grounding` + `validate_motivation_attributions`
- Все отчёты сохраняются как `<run>_ca_drift_check.json` / `<run>_gw_grounding_check.json`
- На FAIL флаги — **не блокируем pipeline**, но логируем для verified-on-run
- В будущей итерации (Batch 3) — обсудить hard-fail или auto-fix

### Какой результат ожидается

В v58:
- CA `description` поля без `потому что` / новых дат / новых имён — clean
- relation_to_subject у тёти Маши = «соседка» (или CA честно говорит `unconfirmed_relation`)
- `validate_historical_note_grounding` → 0 generalization claims без grounding
- `validate_motivation_attributions` → 0 motivation attributions без транскрипта

### Как проверить

1. **Unit-тесты** `tests/test_ca_description_drift.py` (8-12 кейсов):
   - Causal drift: «потому что не привозит подарков» в description, source без «потому что» → flag
   - Legit causal: source имеет «я выкинула, потому что испортились» → description с «потому что» → PASS
   - Date drift: description «1990 шуба», source без года → flag
   - Motivation drift: description «верила в идеалы» (если ввести), source без — flag
   - Idempotent

2. **Unit-тесты** `tests/test_relation_consistency.py`:
   - Тётя Маша, relation="тётя" в fact_map, в transcript нет «сестра моей мамы» → flag unconfirmed
   - Тётя Шура, relation="сестра мужа" подтверждена в TR1 → PASS
   - Идемпотент

3. **Integration** на v56 + v57 артефактах:
   - v56 огурцы description «потому что критиковала за подарки» → должен FAIL
   - v56 шуба event_auto_008 date=1990 → если в source quote года нет → FAIL
   - v57 «1990-е многие пожилые» в narrative → FAIL grounding
   - v57 «идеалы за которые воевала» → FAIL motivation
   - v56 + v57 «август 1994» в narrative → PASS (есть в TR1)

4. **Verified-on-run** v58:
   - Открыть `<run>_ca_drift_check.json` — 0 critical
   - Открыть `<run>_gw_grounding_check.json` — 0 antitriggers из pin-list

---

## Ограничения

- [ ] Промпт CA v1.3 — расширение, не переписывание (сохранить v1.2 правила, добавить 2 новых)
- [ ] Skрипт-валидация — **не блокирует** pipeline, только flagging (hard-fail обсуждаем в Batch 3)
- [ ] НЕ модифицировать description / relation авто-патчем — только flag (риск дальнейшей confabulation)
- [ ] regex `потому что` etc — точные и word-boundary aware, чтобы не ловить ложные срабатывания
- [ ] Idempotent

---

## Dev Review

**Статус:** ожидает

**[TECH]** — пред-резолв:
- Антитриггеры pin-list v2 (epilogue stop-phrases) — частично пересекаются с `validate_motivation_attributions`. Не дублировать — task 043 пишет stop-list для epilogue (template-фразы), task 038 для motivation attributions (динамические). Координация: task 043 имеет explicit stop-list, task 038 имеет grounding-проверку.
- Hard-fail vs flag — flag по умолчанию. Hard-fail для critical confabulation (огурцы, мотивация) — backlog.

**[PRODUCT]** — нет.

**Оценка сложности:** `m` (3-8 ч; основная сложность в качестве regex и калибровке flagger)
**Оценка риска:** `medium` (промпт CA v1.3 может изменить выход CA — нужно сравнить v57 fact_map vs новый)

---

## Реализация

**Статус:** ожидает

---

## Verified-on-run

**Cursor:** [после v58]
**Claude:** [Опус откроет ca_drift_check + gw_grounding_check + проверит огурцы description, мотивации в epilogue]

---

## История статусов

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-17 | `outline` | Опус |
| 2026-05-17 | `new` (полный spec) | Опус (роль архитектор+продакт) |
