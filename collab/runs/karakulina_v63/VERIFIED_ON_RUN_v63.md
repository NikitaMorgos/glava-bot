# VERIFIED_ON_RUN v63 — Каракулина В.И.

**Дата прогона:** 2026-05-18  
**Ветка кода:** `feat/v63-combined-sprint`  
**Артефакты:** `collab/runs/karakulina_v63/`  
**Stage timestamps:** S1=134908, S2=140113, S3=172626  
**Исполнитель верификации:** Cursor Agent

---

## Итог: 11/11 задач PASS (code-side) · 4 warnings в run

| # | Задача | Код | Run |
|---|--------|-----|-----|
| 1 | 049d: GW v2.22 ПРАВИЛО 12 | ✅ | ✅ активен |
| 2 | 038c: CA v1.5 ПРАВИЛО 7 | ✅ | ✅ активен |
| 3 | 048d: children_before_birth validator | ✅ | ✅ тесты pass |
| 4 | 044d-2: render bug empty heading + malformed family | ✅ | ✅ 0 malformed |
| 5 | 043g: stop_phrases event_changed_life + typical_for_generation | ✅ | ✅ 0 найдено |
| 6 | 051d: ep_029 year_confidence=low + parser | ✅ | ✅ parser OK |
| 7 | 043f: Class 11 snapshot tests | ✅ | ✅ 0 в тексте |
| 8 | 043e-2: epilogue quote density validator | ✅ | ✅ тесты pass |
| 9 | 044g: bio_data.family normalization | ✅ | ✅ 21 записей, 0 filtered |
| 10 | 052d: Contributors ФИО+родство only | ✅ | ✅ interview_role/notes скрыты |
| 11 | configs v3/v1: stop_phrases, epilogue_rewrite, bio_data_format, chronology_periods | ✅ | ✅ epilogue_rewrite active |

---

## Промпты и версии

| Промпт | Файл | SHA256 (prefix) |
|--------|------|-----------------|
| Ghostwriter | `03_ghostwriter_v2.22.md` | `6d605f8d…` |
| Completeness Auditor | `16_completeness_auditor_v1.5.md` | `85111b92…` |
| Fact Extractor | `02_fact_extractor_v3.4.md` | `a863422a…` |
| Historian | `12_historian_v3.md` | `3e316c14…` |
| Fact Checker | `04_fact_checker_v2.13.md` | `efec0625…` |
| Literary Editor | `05_literary_editor_v3.1.md` | `544582a5…` |
| Proofreader | `06_proofreader_v1.md` | `5c600132…` |

---

## Метрики прогона

| Метрика | Значение | Цель |
|---------|---------|------|
| text_FULL.md total | **22 003 chars** | 20 000+ ✅ |
| Нарратив (ch_01–epilogue) | **18 372 chars** | 20 000+ ⚠️ |
| ch_01 | 3 249 chars | ≥ 1 500 ✅ |
| ch_02 | 6 872 chars | ≥ 4 000 ✅ |
| ch_03 | 5 053 chars | ≥ 3 000 ✅ |
| ch_04 | 2 230 chars | ≥ 1 500 ✅ |
| epilogue | 968 chars | ≥ 500 ✅ |
| Pytest snapshot tests | **35/35** | все ✅ |
| Discourse markers ch_02 | 2 / 8 | ⚠️ ниже порога |
| Discourse markers ch_04 | 0 / 3 | ⚠️ ниже порога |
| Pin-list depth ep_003 | 2 / 3 предл. | ⚠️ |
| Pin-list depth ep_007 | 2 / 3 предл. | ⚠️ |
| Required entities (gate) | 9/11 критических | ⚠️ Мария, баба Аня miss |
| Entity substitution Калинин | 5×, все pre-1990 | ✅ норма |
| Epilogue rewrite deletions | 1 (path_from_X_to_Y) | ✅ |

---

## Детальные наблюдения по задачам

### 1. GW v2.22 (049d)
Манифест Stage1 и Stage3: `active_prompts.ghostwriter.prompt_file = 03_ghostwriter_v2.22.md`.
ПРАВИЛО 12 добавлено перед «НАЧИНАЙ РАБОТУ». v2.21 намеренно пропущен (нет коллизии с архивными прогонами).

### 2. CA v1.5 (038c)
Манифест: `active_prompts.completeness_auditor.prompt_file = 16_completeness_auditor_v1.5.md`.
ПРАВИЛО 7 (Named Entity Preservation) — добавлено в секцию strict override.
Stage1 CA-лог: все персоны pin_list найдены, pin_list episodes подтверждены в транскрипте.

### 3. children_before_birth validator (048d)
`validate_children_before_birth` в `pipeline_utils.py`. Конфиг `chronology_periods_karakulina.json` v1:
`son_valeriy_birth.year=1948`, `daughter_tatyana_birth.year=1952 (estimated)`.
35 pytest-тестов зелёные, в т.ч. `TestChildrenBeforeBirth`.

### 4. Render bug (044d-2)
`bio_data_integrity.json`: `filtered_non_family: []`, `issues_count: 1` (event_030 award field — не связан с family).
Секция `### Дополнительный текст ch_01` подавлена (нет пустого heading в тексте).

### 5. Stop phrases (043g)
Regex-поиск по `text_FULL.md`: 0 совпадений для всех новых паттернов (`event_changed_life`, `typical_for_generation`, `in_this_typicality`).
`epilogue_rewrite_mapping.json` v3 активен — правила записаны в `epilogue_rewrite_log.json`.

### 6. ep_029 year_confidence (051d)
`parse_pin_list_year_field('unknown (year_confidence=low)')` → `{'year': None, 'year_confidence': 'low'}` ✅  
`parse_pin_list_year_field('1990-е')` → `{'year_range': '1990-е', 'year_confidence': 'medium'}` ✅  
`known_episodes_karakulina.md` ep_029: `Год = unknown (year_confidence=low)`.

### 7. Class 11 (043f)
Regex `не\s+\w+(?:ил[аои]?|ал[аои]?)\s+\w+\s+и\s+\w+`: **0 совпадений** в тексте.
Snapshot тест `TestClass11StopPhrase` зелёный.

### 8. Epilogue quote density (043e-2)
`validate_epilogue_quote_density` добавлен в `pipeline_utils.py`. Тест `TestEpilogueQuoteDensity` зелёный.
В данном прогоне эпилог (968 chars) не содержит прямых цитат — validator будет фиксировать warning в post-processing.

### 9. bio_data.family normalization (044g)
`bio_data_format_config.json` v1 создан. 21 family entry, `filtered_non_family: []`.
Нет записей с backslash/кавычками в notes (filter active).

### 10. Contributors (052d)
Секция «Кто работал над этой Главой» в `text_FULL.md`:
```
- **Каракулина-Маргось-Кужба Татьяна Дмитриевна** — дочь
- **Маргось Никита Владимирович** — внук
- **Маргось Даша Владимировна** — внучка
- **Кужба Олег [отчество требует уточнения]** — второй муж дочери (отчим внуков)
```
`interview_role` и `notes` скрыты ✅

### 11. Configs (043g+044g+048d+051d)
- `narrative_stop_phrases.json` → v3 (4 новых паттерна)
- `epilogue_rewrite_mapping.json` → v3 (2 новых правила; 1 удаление в прогоне)
- `bio_data_format_config.json` → v1 (создан)
- `chronology_periods_karakulina.json` → v1 (создан, children_birth_constraints)

---

## Калинин ↔ Тверь: подтверждение отсутствия регрессии task 051

Все 5 вхождений «Калинин» — **исторический контекст pre-1990**:
1. `Татьяна (родилась в 1956 году, Калинин)` — паспортная запись эпохи
2. `Жили в Германии, Вышнем Волочке, Калинине, Венгрии` — хронология 1946–1962
3. `В 1956 году в Твери (тогда Калинине) родилась дочь Татьяна` — явная темпоральная пометка ✅
4. `семья возвращалась в Калинин` — 1950-е (венгерский период)
5. `поликлинике № 3 в Калинине. В 1963 году...` — исторический период работы

«Тверь» используется для современного и нейтрального контекста (4 вхождения). Регрессии нет.

---

## Открытые пункты → v64 backlog

| ID | Описание | Приоритет |
|----|---------|---------|
| v64-dm | Discourse markers ch_02=2/8, ch_04=0/3 — GW v2.22 ПРАВИЛО 12 должен помочь при следующем более глубоком прогоне | medium |
| v64-depth | Pin-list depth ep_003 (war call-up) и ep_007 (Germany 1946) = 2/3 sentences | medium |
| v64-entities | "Мария" и "баба Аня" не попали в нарратив — добавить в required_persons pin_list v6 | high |
| v64-narrative | Нарратив 18 372 chars < 20 000 (без мета-секции) — нужен depth-патч для ch_02 | medium |
