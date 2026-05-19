# Universality audit 2026-05-19 — готовность пайплайна к подключению других subjects

> **Триггер:** Никитин запрос «проанализируешь все спеки/промпты/код на специфические каракулинские задачи? хочется удостовериться, что наш пайплайн универсально будет работать».
>
> **Методика:** Audit-checkpoint (Правило 2 архитектора) — read + classify, не правим код. Делегировано трём general-purpose агентам параллельно по зонам ответственности.
>
> **Ветка для audit:** `origin/feat/v64-revision-loop-sprint` (актуальное production состояние; main отстаёт — только спецификации merged без code).
>
> **Дата:** 2026-05-19, Опус (роль архитектор+продакт).

---

## TL;DR (за 30 секунд)

**Pipeline НЕ готов к подключению Корольковой/Дмитриева без серии фиксов.** Найдено **42 CRITICAL** + **18 BUG** в трёх зонах:

| Зона | CRITICAL | BUG | Готовность | Главная проблема |
|------|----------|-----|------------|------------------|
| **LLM prompts** (GW v2.23, CA v1.5, FC v2.13) | 21 | 9 | ❌ блокер | Большие блоки subject-specific examples в правилах. LLM на Корольковой может галлюцинировать «огурцы Молдавия», «выковыривал», «Власьево» |
| **Pipeline code** (pipeline_utils.py + scripts) | 17 | 7 | ❌ блокер | 2 critical: validate_children_before_birth hardcodes «valeriy»/«tatyana», validate_entity_substitution pairs hardcoded. Sprint runners (`_v64_*.py`, `_run_v64_full.sh`) полностью karakulina-only с assertions «Мария / баба Аня» в коде |
| **Generic configs + tests** | 0 | 2 | ✅ practically clean | Все 7 generic configs subject-agnostic ✅. Production logic tests чисты ✅. Snapshot tests с subject-specific examples — OK by design |

**Хорошие новости:**
- Configs архитектурно правильные (per-subject suffixed файлы + generic configs без захардкоженной конкретики)
- Тесты на production logic не делают subject-specific assertions
- LE v3.1, Historian v3, Cleaner v1, Proofreader v1 — clean
- `build_gate1_full_text.py` — clean (полностью параметризованный CLI)
- pipeline_utils.py validate_*/parse_pin_list_*/enrich_* — **все 27 функций** принимают `fact_map / pin_list / config` как параметр, нет `if subject == "karakulina"` branches

**Плохие новости:**
- 3 главных LLM-промпта (GW, CA, FC) содержат **большие связные блоки** Каракулино-конкретики как «illustrative examples» в правилах. Это **то же самое что мы исправляли в task 049h** (ПРАВИЛО 2 GW), но в **остальных 9+ правилах** того же файла + во всех 4 ПРАВИЛАХ CA + в FC test block ~150 строк.
- Sprint runner scripts (`_v64_*.py`, `_run_v64_full.sh`) содержат **subject-name в asserts на содержание книги** (например `assert "Мария" in family`, `assert "баба Аня" in text`) — это блокер для прогона на Корольковой даже без правки кода.
- 2 валидатора в pipeline_utils.py **silently не работают** для других subjects: validate_children_before_birth (хардкодит имена детей субъекта), validate_entity_substitution (хардкодит 3 пары топонимов/учреждений).

---

## Phase 1 — критические fixes (до подключения Корольковой)

### A. LLM prompts (один prompt-bump на каждый, per Правило 6 = ~6 sprints)

| # | Spec | Файл | Что делать |
|---|------|------|------------|
| **A1** | (после v65) | GW v2.24 → v2.25 | Universality refactor ПРАВИЛ 3, 8, 9, 10 + PIN_LIST антитриггеры (lines 260-460, 2010-2014). Все examples → placeholders ([Имя_близкого], [Локация_X], [YYYY], [объект_X]). Task 049h v65 покрыл только ПРАВИЛО 2 |
| **A2** | (после A1) | CA v1.5 → v1.6 | Universality refactor ПРАВИЛ 1, 2, 4, 6, 7 + JSON schema example. Lines 14, 64, 94-96, 134-136, 284-306, 329-336, 374-379, 391-400. Большой кластер «огурцы Молдавия» в ПРАВИЛЕ 2 → placeholder example |
| **A3** | (после A2) | FC v2.13 → v2.14 | Universality refactor: **block lines 853-1031** (~150 строк «огурцы Молдавия Object Markers Test») + 6 BUG examples (lines 62, 324, 545-546, 775-776, 1037-1039). Это **самый большой связный** subject-specific блок в активных промптах |
| **A4** | (после A3) | FE v3.4 → v3.5 | Minor fix: lines 343-358, 547 — пример «противоречие внутри транскрипта» с Германия/1946/Вышний Волочёк → placeholders |

**Принципы при fix:** placeholder pattern (как уже сделано в GW v2.24 ПРАВИЛО 13 + Правило 12) — `[Субъект]`, `[Период]`, `[Имя_близкого]`, `[Локация_X]`, `[YYYY]`, `[объект_X]`, `[характерное_слово]`. Pin-list characteristic_words per subject уже подключается через input (после A1).

### B. Pipeline code (validators которые silently не работают)

| # | Файл / строки | Issue | Fix |
|---|---------------|-------|-----|
| **B1** | `pipeline_utils.py:4692-4695` `validate_children_before_birth` | Hardcoded `if "valeriy" in pid: ["валери"]; elif "tatyana": ["татьян"]`. Для Корольковой validator silently NOOP. | Извлекать `child_name_stem` поле из `chronology_periods_<subject>.json`. Validator data-driven. |
| **B2** | `pipeline_utils.py:4900-4904` `validate_entity_substitution` | Hardcoded 3 пары: Калинин/Тверь, Молдавия/Молдова, Химинститут/РХТУ. | Перенести `substitution_pairs` в `entity_substitution_<subject>.json` либо расширить `fact_map.place_canonical`. |
| **B3** | `pipeline_utils.py:4977` `NOMINATIVE_CITY_RE` | `r"\bв\s+(Калинин\|Москва\|Ленинград\|Тверь)\b"` — hardcoded список городов для locative-case проверки. | Generic check на любой топоним либо расширить из gazeteer config. |

### C. Stage runners (task 053 generic — уже в backlog)

| # | Файл / Issue | Fix |
|---|--------------|-----|
| **C1** | `scripts/test_stage1_karakulina_full.py` — subject в filename + 5 hardcoded module constants | task 053 `scripts/test_stage1_subject.py --subject=<name>` + per-subject defaults config |
| **C2** | `scripts/test_stage2_pipeline.py` — module consts + fallback на `known_episodes_karakulina.md` если файла нет | Убрать silent fallback (fail-fast с ошибкой), параметризовать через CLI |
| **C3** | `scripts/test_stage3.py` — module constants `PROJECT_ID`/`SUBJECT_NAME` | CLI override (есть частично) + убрать defaults на karakulina |

---

## Phase 2 — sprint scripts cleanup (опционально, можно с каждым sprint)

| # | Файл | Issue |
|---|------|-------|
| D1 | `scripts/_v64_revision_pass.py` | 6 hardcoded `karakulina_*` paths + `'subject': 'Каракулина Валентина Ивановна'` |
| D2 | `scripts/_v64_run_validators.py` | 3 hardcoded paths |
| D3 | `scripts/_v64_stage3_final.py` | **8 critical** — содержит `assert 'Мария' in family`, `assert 'баба Аня' in text` — это **проверки на содержание книги Каракулиной** в production-style asserts |
| D4 | `scripts/_run_v64_full.sh` | Полностью karakulina-specific (50+ paths, assertions). Sprint-specific bash — приемлемо, но накапливает technical debt |

**Принципиальное решение для D1-D4:** при создании v65 / v66 sprint runner — использовать generic template (env-vars + parameters), не копировать v64 как есть. Иначе каждый прогон Корольковой потребует копировать и редактировать.

---

## Phase 3 — DOCS clarity (не блокеры)

| # | Файл / строки | Issue | Fix |
|---|---------------|-------|-----|
| E1 | `pipeline_utils.py:4673` docstring | `chronology_config — chronology_periods_karakulina.json` | Заменить на `_<subject>.json` (как уже сделано в gazeteer:4465 и discourse_markers:4043) |
| E2 | `pipeline_utils.py:1634` error message | «v49: огурцы vs счётчик; v50: общий токен валентина» — subject-specific исторический комментарий в production error | Перефразировать generic либо вынести в docstring |
| E3 | Несколько mentions Каракулиной в комментариях/docstrings как «training case» | Acceptable, но при подключении Корольковой может вводить в заблуждение | Опционально — заменить на `[training case]` placeholder |

---

## Что точно НЕ проблема

- **Все 7 generic configs subject-agnostic ✅** (`narrative_stop_phrases.json`, `epilogue_stop_phrases.json`, `epilogue_rewrite_mapping.json`, `bio_data_format_config.json`, `historical_notes_enrichment_config.json`, `personal_historical_voice_config.json`, `revision_orchestrator_config.json`)
- **Per-subject configs** правильно naming + правильно содержат subject-specific data (это **по дизайну**)
- **pipeline_utils.py 27 validate_/parse_/enrich_ функций** — все параметризованные. Нет `if subject == "karakulina"` branches.
- **Production logic tests** — 0 subject-specific assertions в логике
- **Snapshot tests** — subject-specific examples acceptable (lesson v62a — без них recurring patterns возвращаются)
- **LE v3.1, Historian v3, Cleaner v1, Proofreader v1** — clean

---

## Verdict: BLOCKER status для Корольковой

**Текущее состояние:** подключение Корольковой = **гарантированные регрессии**:
1. GW/CA/FC прочитают захардкоженные Каракулино examples → возможны galлюцинации
2. validate_children_before_birth silently вернёт OK без проверки (если у Корольковой дети с другими именами)
3. validate_entity_substitution не поймает её subject-specific подстановки (если есть)
4. Sprint runner скрипты не отработают (assertions «Мария / баба Аня» fail)

**Минимальный набор fixes для unblocked Корольковой:**
- A1+A2+A3 (LLM prompts universality refactor — 3 sprints)
- B1+B2 (children + entity_substitution параметризация — 1 sprint)
- C1 (generic Stage 1 runner — 1 sprint, task 053 уже в backlog)

**Оценочно:** 4-5 sprints + 1-2 verify прогона. Стоимость **~$25-40** total (по принципу 7 «не экономим на тестовых прогонах»).

**Альтернатива (radical):** один большой sprint «universality refactor» который делает A1+A2+A3+B+C за раз. Per Правило 6 это нарушение (3 GW prompt-bumps в один заход), но если каждое изменение чисто declarative (только replace examples) и нет новой логики — может быть acceptable. **Не рекомендую** — combined sprint v63 как раз показал что bundled changes теряют диагностику (Правило 7).

---

## Когда делать (приоритизация)

**Сейчас (v65 sprint у Курсора):** не lezem. v65 закрывает другое (orchestrator coverage + recurring classes).

**После v65 verify:**
- Если v65 PASS Ворот 1 на Каракулиной → tag RP-1 → **Phase 1 universality refactor sprints v66-v70** (A1, A2, A3, A4, B1+B2+B3, C1 — по одному per sprint) → потом подключение Корольковой
- Если v65 НЕ PASS → сначала v66 fix Ворот 1 на Каракулиной, **Phase 1 после**

**Не делаем сейчас:**
- ❌ Phase 1 fixes **до** PASS Ворот 1 на Каракулиной — приоритет качества текущего subject
- ❌ Подключение Корольковой до Phase 1 завершения
- ❌ Phase 2 (sprint script cleanup) — это technical debt, не блокер; делаем при каждом новом sprint
- ❌ Phase 3 (DOCS) — низкий приоритет

---

## Лог делегирования

Audit проведён через 3 параллельных general-purpose агента (`Agent` tool), длительность ~20 минут каждый, общий вывод ~1500 слов суммарно. Финальная классификация и приоритизация — Опус (этот документ).

**Распределение зон:**
1. Agent 1: 8 active LLM prompts (GW, CA, FE, FC, LE, Historian, Cleaner, Proofreader)
2. Agent 2: pipeline_utils.py + 8 файлов scripts/
3. Agent 3: 7 generic configs + 8 per-subject configs + tests/

**Все 3 agent reports консолидированы** в этот doc.

---

## История

| Дата | Изменение | Кто |
|------|-----------|-----|
| 2026-05-19 | Audit перед подключением Корольковой; 42 CRITICAL + 18 BUG; 3-phase fix plan; BLOCKER verdict | Опус |
