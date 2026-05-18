# v62a sprint: 10 точечных scripted fixes (NO GW change)

**Статус:** `new`
**Sprint ID:** v62a
**Автор:** Опус (роль архитектор+продакт)
**Дата создания:** 2026-05-18
**Тип:** `cco-скрипты` + конфиги (NO LLM prompt changes!)
**Триггер:** v61 verified review (5 моих блокеров + 13 Никитиных, 2 false alarm → 14 unique → 10 точечных + 1 meta)
**Связано:** run_registry v61 verification; v59 baseline; Правила 1-6 архитектора

---

## Контекст

После v61 (Hybrid rollback) — content quality v59 в основном восстановлен, все 8 cherry-pick fixes работают. Но Никитин review дал 13 замечаний + 5 моих блокеров. После дедуп = **14 unique items**, из которых **10 решаются точечными scripted fixes без GW prompt change** (per Правило 6 — медленно без откатов).

**Универсальный подход:** все fixes — generic algorithms + subject-specific configs. Никакой Каракулино-конкретики в коде или промптах.

**4 items отложены в backlog** (требуют GW prompt-bump — отдельные дисциплинированные волны по Правилу 6):
- ch_03 «Гостеприимство и кулинария» раздел — отдельный prompt-bump v63
- Epilogue extend 676 → ~900 без stop phrases — отдельный prompt-bump v64
- historical_notes inline restoration (vs v59 9 inline) — отдельный prompt-bump v65
- Грибы/ягоды эпизод — investigation (был не в v59 — расширение pin-list events)

---

## Universality check

- [x] Промпт без конкретики — **0 prompt changes в v62a**, чисто scripted
- [x] Subject-specific конкретика — в JSON/MD конфигах per subject
- [x] Алгоритм generic — все 10 fixes применимы к любому subject
- [x] Subject-replacement test — для Корольковой/Дмитриева работает без правок ✅

---

## 10 точечных fixes + 1 meta

### 044d — Render bug `?: ?` в bio_data.family

**Проблема:** в v61 text_FULL.md первые строки:
```
#### Семья
- **Соседка, любила грибы/ягоды** — "тётя" (по обращению) (НЕ в family. ...)
- **Свекровь рассказчика...** — _(НЕ в family Валентины. ...)_
- **Подруга"** — "знакомая\ (врач, авторитет ...)
### Дополнительный текст ch_01
## Основные даты жизни
```

Это **render bug** `build_gate1_full_text.py`:
1. Records с `in_bio_data_family: false` (override entries) рендерятся как `?: ?` вместо skip
2. Дубль `## Основные даты жизни` (sectional + ch_01.content markdown)

**Fix:**
- В `build_gate1_full_text.py`:
  - При render `bio_data.family[]` — **skip** записи где `in_bio_data_family == false` ИЛИ `label == "?"` ИЛИ value pусто
  - Удалить sectional рендер если ch_01.content уже содержит structured paspart

**Универсально:** generic check per subject.

### 044e — Бабушка Марфа force-add в bio_data.family

**Проблема:** в v61 bio_data.family отсутствует Бабушка Марфа. Pin-list v3 содержит `Марфа` в required_persons (task 044b). Cherry-pick task 044b неполный или enforce не применил.

**Fix:**
- Debug в `pipeline_utils.py`: почему `enforce_bio_data_completeness` + `apply_relation_overrides` + required_persons pass не добавили Марфу
- Возможно: confidence фильтр (Марфа имеет `confidence: low` в fact_map)
- Решение: required_persons (из pin-list) — force-add even with confidence low, с `needs_verification: true` flag

**Универсально:** required_persons из `known_episodes_<subject>.md` секции «Прямые родственники».

### 044f — Внук Никита / Внучка Даша notes preservation

**Проблема:** в v61 bio_data.family:
```
11. Внук: Никита | note: (empty)
12. Внучка: Даша | note: (empty)
```
В v59 было «сын Татьяны» / «дочь Татьяны» как note. Потеряно при cherry-pick task 044b persona_notes.

**Fix:**
- В `persona_notes_<subject>.json` (если есть, или в pin-list parser): explicit notes для Никиты и Даши
- `enforce_persona_notes` применяет эти notes — текущая логика, но persona_notes_karakulina.json возможно не имеет этих entries

**Универсально:** generic mechanism, subject config.

### 049c — Discourse markers validator fix

**Проблема:** v61 `discourse_markers.json` show ch_02=0, но ручной grep по `вспомина|по словам|отмеч|говор.*дочь` = 10 hits + Татьяна mentioned 13 раз в тексте. Validator **overstrict**.

**Fix:**
- В `validate_discourse_markers` (`pipeline_utils.py`):
  - Использовать **rapporteurs** из config `discourse_markers_<subject>.json` (`rapporteurs: [Татьяна, Никита, ...]`)
  - Match patterns включают **aliases** rapporteur'а (Татьяна / дочь / по её словам / она вспоминает)
  - Не требовать **точное** имя rapporteur'а — generic patterns тоже match

**Универсально:** rapporteurs config per subject.

### 051c — Paspart-only temporal name (Тверь → Калинин для 1956)

**Проблема:** в v61 bio_data.family value Татьяны: «родилась в 1956 году в Твери». В 1956 город назывался Калинин (переименован обратно в Тверь только в 1990). Task 051 (полное temporal naming) NOT cherry-picked v61 (был broken). Нужен **paspart-only minimum fix**.

**Fix:**
- Минор: новая функция `apply_temporal_naming_to_paspart_only(book, gazeteer.temporal_place_names)`:
  - Применяется **только** к `bio_data.family[].value/note` и `bio_data.timeline[].title/text`
  - НЕ применяется к narrative chapters (ch_02-04, epilogue)
  - Для каждого topo в paspart с year в context: если year < transition_1 → use historical_alternate
- Конфиг `gazeteer_<subject>.json.temporal_place_names` (есть в v60 task 051, можно reuse, но **только** для paspart)
- Multi-rename history support: Калинин 1931-1990 (до — Тверь; после — Тверь обратно)

**Универсально:** subject config + generic algorithm.

### 048c — Chronology check «year + grandchild before parent's marriage»

**Проблема:** v61 содержит line 229 «В 1973 году дочь Татьяна попросила Валентину уйти с работы, чтобы встречать внучку Дашу после школы». Даша not born in 1973 (Татьяна замужем за Маргось 1977 → Даша после 1977). task 048b (grandchildren chronology) **false negative** — не отловил.

**Fix:**
- В `validate_chronological_consistency`:
  - Для grandchild persons (relation_to_subject ∈ {внук, внучка}): inferred min birth = max(parent.marriage_year + 1, parent.birth_year + 16)
  - Если year упомянут в context with «внук/внучка» И year < inferred_min → flag error
  - Pattern: `\b(встреча\w*|воспит\w*|играл\w*|видел\w*|школ\w*)\s+\w*\s+(внук\w*|внучк\w*)` near year mention

**Универсально:** generic algorithm на fact_map.persons + marriage events.

### 052c — Contributors раздел как чистый скрипт из pin-list v3

**Проблема:** task 052 v60 — галлюцинация «Наталья Каракулина», только 2 из 4 контрибьюторов. Rogue config Курсора.

**Fix:**
- **Чистый скрипт** в `build_gate1_full_text.py`:
  - Читает `known_episodes_<subject>.md` секцию **Contributors**
  - Парсит таблицу `| contributor_id | full_name | relation_to_subject | interview_role | notes |`
  - Append section в конце text_FULL:
    ```markdown
    ---

    ## Кто работал над этой Главой

    - **Каракулина-Маргось-Кужба Татьяна Дмитриевна** — дочь, основной рассказчик
    - **Кужба Олег [отчество]** — второй муж дочери
    - **Маргось Никита Владимирович** — внук, со-интервьюер
    - **Маргось Даша Владимировна** — внучка
    ```
- **БЕЗ GW prompt change** — чистый post-process
- НЕ использовать `contributors_karakulina.json` (rogue config) — только pin-list v3 (=v4)

**Универсально:** pin-list per subject Contributors раздел.

### 043d — narrative_stop_phrases расширение для Class 1 confabulations

**Проблема:** v61 содержит:
- «специальность, которая определила всю её дальнейшую жизнь» (line 181) — Class 1: акушерство не определило её жизнь
- «помогая женщинам в самые важные моменты их жизни» (line 183) — Class 1: в TR1 нет, GW выдумал

**Fix:**
- Расширить `narrative_stop_phrases.json` (task 043b) с **categorical** patterns:

```json
{
  "category": "speciality_defined_life",
  "pattern": "(специальност\\w+|профессия|обучение)[\\s\\S]{0,30}(определ\\w+|стал\\w+)[\\s\\S]{0,20}(всю|её|его|их)?\\s*(дальнейш\\w+|жизн\\w+|карьер\\w+|судьб\\w+)",
  "scope": ["epilogue", "ch_02"],
  "severity": "warning"
},
{
  "category": "helping_at_important_moments",
  "pattern": "(помога\\w+|оказыва\\w+\\s+помощ\\w+)\\s+\\w+\\s+в\\s+(самы\\w+\\s+)?важн\\w+\\s+момент\\w+\\s+\\w+\\s+жизн\\w+",
  "scope": ["ch_02", "ch_03"],
  "severity": "error"
}
```

**Универсально:** categorical patterns, без subject-конкретики. Применимо к любым биографиям.

- Также: `enforce_narrative_stop_phrases` (опционально) — delete_sentence для error severity, warn для warning

### 045e — Timeline anchors Widowhood enforce as separate period

**Проблема (Никитин уточнение):** в v61 ch_01.content «Основные периоды жизни» содержит 6 разделов вместо 7. Возможно «Жизнь в Химинституте 1962-1994» **поглотил** Вдовство (1978-1996). `validate_timeline_anchors` отчитал 7/7 found, но это **fuzzy match** на keywords — реально periods overlap.

**Fix:**
- В `validate_timeline_anchors`:
  - Strict period separation check: для каждого pair (anchor_A, anchor_B) с `year_range` overlap >0:
    - Проверить что в `ch_01.content` markdown оба periods **присутствуют** как **отдельные** `**YYYY-YYYY. Title**` blocks
    - Если только один block покрывает overlap range → flag `anchor_absorbed`
  - Конкретно для `widowhood` (1978-1996): должен быть отдельным от `khim_institute` (1962-1978)
- **БЕЗ enforce auto-split** (риск выдумывания контента); только flag

**Универсально:** generic algorithm + anchors config per subject.

### 043e — Anti-facts pin-list секция + scripted check

**Проблема:** v61 содержит «Валентина украшала салаты вареньем — необычный способ» (line 360). В TR2 контекст: «салаты делала + варенья всякие» — **два разных** продукта, GW **склеил**.

Это **Class 1 predicate-object confabulation** — generic class когда GW создаёт seemingly logical связку между X и Y которые в источнике **отдельны**.

**Generic fix:**
- В `known_episodes_<subject>.md` новая секция `Anti-facts` (do not combine):
  ```markdown
  ## Anti-facts (do not combine in narrative)

  | anti_fact_id | item_A | item_B | reason |
  |---|---|---|---|
  | af_001 | салаты | варенье | в TR2 упомянуты как **отдельные** блюда, не «украшение салата вареньем» |
  | af_002 | акушерка (специальность) | определила всю жизнь | акушерство — образование, не карьера; работала медсестрой |
  | af_003 | акушерка | помощь женщинам в важные моменты | в TR нет данных о работе акушеркой |
  ```

- Скрипт `validate_anti_facts(book, anti_facts) -> report`:
  - Для каждого anti_fact: grep `item_A` и `item_B` в **одном paragraph** (≤2 sentences distance)
  - Если оба совпали → flag `anti_fact_combination` warning
  - Не enforce (риск false positive), только flag для human/Опус review

**Универсально:** anti_facts per subject pin-list — generic mechanism.

### meta — gate1_product_checklist target update

**Никитино решение:** target объёма **20K+** (заменяет 14-18K).

**Fix:**
- В `collab/context/gate1_product_checklist.md` section «1. Объём текста»:
  - Total chars target: **20 000+ chars** (вместо 14-18K)
  - ch_02 chars: ≥7K (вместо ≥5K) — наибольшая глава
  - ch_03 chars: ≥4K
  - ch_04 chars: ≥2.5K
  - epilogue chars: 800-1500 (расширить от 700)

**Универсально:** target generic для всех биографий 90-минутного интервью.

---

## Backlog после v62a (по одной GW правке за раз, Правило 6)

| Volna | Trigger | GW change |
|---|---|---|
| v63 | ch_03 «Гостеприимство и кулинария» раздел | GW prompt-bump (1 правило: section anchor в ch_03) |
| v64 | Epilogue extend 676 → ~900 без stop phrases | GW prompt-bump (1 правило: depth target epilogue без шаблонов) |
| v65 | historical_notes inline restoration (vs v59 9 inline) | Investigation — scripted reclassify или GW prompt-bump (1 правило) |
| v66 | Подключение Корольковой (task 053 generic runners) | NO GW change (refactor scripts) |

Каждая = $2-3, отдельный verify.

---

## Финансово v62a

1 прогон $2-3. **NO GW prompt change** = безопасный по Правилу 6.

---

## Universality verification (4 вопроса + trap warning)

- [x] **Промпт без конкретики subject?** ДА — 0 prompt changes в v62a
- [x] **Subject-specific конкретика — в JSON/MD конфигах per subject?** ДА — pin-list, gazeteer, anti_facts, persona_notes, anchors per subject
- [x] **Алгоритм/mechanism не привязан к Каракулиной?** ДА — все 10 fixes generic
- [x] **Subject-replacement test:** ДА — для Корольковой будут свои pin-list (включая anti_facts, contributors) + свой gazeteer.temporal_place_names

**Trap warning:** При реализации Курсор должен делать mental test «работает ли это для Корольковой?». Если ловит искушение зашить «Татьяна» или «Калинин» в код — это red flag, через placeholder/config.

---

## Dev Review

**Статус:** ожидает

**[TECH]** — pre-answer от Опуса:
- 044d render: prefer skip override entries (clean output); если value=None и note содержит «from pin-list required_persons» → skip
- 044e Марфа: debug confidence filter — required_persons из pin-list **bypass** confidence
- 045e widowhood: strict period separation — не auto-split (только flag)
- 043e anti_facts: scripted check, не enforce — flag warning
- 051c paspart-only temporal: **только** bio_data секция, не narrative

**[PRODUCT]** — нет (все продактовые решения мои)

**Сложность:** все `xs` (по одной задаче); общий sprint ~`s` (1-3 ч × 10 = ~6-10 ч Курсору)
**Риск:** `low` (нет GW change, only scripted)

---

## Verified-on-run v62 (после прогона)

Опус откроет text_FULL.md v62 + reports independent observation на каждую задачу:

- **044d:** «text_FULL начало без `?: ?` строк; нет дубля «Основные даты жизни»»
- **044e:** «bio_data.family содержит «Бабушка: Марфа» с note `мать отца Валентины`»
- **044f:** «Внук: Никита (сын Татьяны)», «Внучка: Даша (дочь Татьяны)» — notes present
- **049c:** «discourse_markers.json ch_02 ≥ 5 (вместо false 0)»
- **051c:** «Дочь: Татьяна (родилась в 1956 году в Калинине)» — Калинин, не Тверь
- **048c:** «chronology_check.json: «1973 + внучка Даша» flagged error»
- **052c:** «text_FULL в конце имеет раздел «Кто работал над этой Главой» — 4 имени из pin-list v4 Contributors»
- **043d:** «style_checks: «определило всю её жизнь» flagged + «помогая женщинам в важные моменты» flagged»
- **045e:** «timeline_anchors.json: widowhood (1978-1996) found as separate period от khim_institute»
- **043e:** «anti_facts_check.json: af_001 «салаты + варенье» triggered if combined; af_002/003 если 043d не auto-removed»

---

## История

| Дата | Статус | Кто |
|---|---|---|
| 2026-05-18 | `new` | Опус |
