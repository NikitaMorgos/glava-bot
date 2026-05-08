# Architecture audit — Glava pipeline — 2026-05-08

**Автор:** Опус
**Цель:** перед волной 1.4 — увидеть слепые пятна **проактивно**, не реактивно (как было до сих пор). Дать план волн 1.4–1.6 с фокусом «довести Каракулину до конца + готовность к Корольковой/Дмитриеву».

**Метод:** прошёл по всем 14 активным промптам, всем Stage-скриптам, всем валидаторам в коде, всем 32 task'ам в `collab/tasks/`. Классифицировал каждого агента по input/output контракту и наличию post-validator на коде.

---

## TL;DR

- **14 агентов в пайплайне.** Из них **3 имеют post-validators на коде** (GW, LD, FE через Completeness Auditor). **11 — без post-validator** (Cleaner, Historian, FC, **Literary Editor**, Proofreader, Photo Editor, Cover Designer, Art Director, QA Layout, Interview Architect, Completeness Auditor).
- **Это означает 11 слепых пятен.** Каждое из них — потенциальная мутация которая прокатится через защиту.
- **v53b — пример первого срабатывания.** Stage 3 LE удалил эпизод тихо, потому что в LE-промпте «устранение дублей» прямо разрешено, и **на коде нет проверки fact preservation**. Это не баг агента — это пробел архитектуры.
- **Текущие 6 защит на коде покрывают только GW (revision) и LD.** За пределами — терра инкогнита.
- **Для перехода Каракулина → Королькова → Дмитриев** нужны 3 архитектурных шага: **Сustom-проверки на каждый агент** (волна 1.4), **универсализация имён/данных** (волна 1.5), **schema validation** (волна 1.6).
- **План волн 1.4-1.6** ниже, в порядке приоритета. Стоимость в днях моей работы — реалистичная.

---

## 1. Pipeline overview

```
                ┌─ STAGE 1 (Stage 1) ─────────────────────────────────┐
                │                                                      │
   transcript → Cleaner (01) → Fact Extractor (02) → Completeness    │
                                  ↓                       Auditor (16)│
                              fact_map_full ──→ clean fact_map ───────┘
                                                          ↓
                ┌─ STAGE 2 (Stage 2) ──────────────────────────────────────────┐
                │                                                               │
                │   Historian (12) ─────────────────────┐                       │
                │                                       ↓                       │
                │   Ghostwriter pass1 (03) → Ghostwriter pass2 (03) → Fact     │
                │                                                      Checker  │
                │                                                      (04)     │
                │                                                       ↓       │
                │   ←──── revision loop (FC errors → GW revision) ←─────┘       │
                │                                                               │
                │   [✅ scope merge guardrail (волна 1.3.3)]                   │
                │   [✅ validate_revision_volume (волна 1.2.2)]                │
                │   [✅ evidence verification (волны 1.2.3+1.3.x)]             │
                └───────────────────────────────────────────────────────────────┘
                                                          ↓
                                                  book_FINAL_stage2
                                                          ↓
                ┌─ STAGE 3 ───────────────────────────────────────────┐
                │                                                      │
                │   Literary Editor (05) → Proofreader (06)           │
                │                                                      │
                │   [❌ НЕТ fact preservation check]                  │
                │   [❌ НЕТ post-validator]                           │
                │   [⚠️ v53b: Stage 3 LE удалил эпизод]               │
                └─────────────────────────────────────────────────────┘
                                                          ↓
                                                  book_FINAL_stage3
                                                          ↓
                ┌─ STAGE 4 ──────────────────────────────────────────────┐
                │                                                         │
                │  Photo Editor (07) ─────┐                              │
                │  Cover Designer (13) ───┤→ Art Director (15) → Layout │
                │                          │                  Designer  │
                │                          │                     (08)    │
                │                          │                      ↓      │
                │                          │              QA Layout (09) │
                │                          │                      ↓      │
                │  [✅ validate_layout_fidelity (волна 1.1)]      PDF    │
                │  [⚠️ photos_dir leak — task 021 partial]              │
                └────────────────────────────────────────────────────────┘
```

Параллельно: **Interview Architect (11)** запускается после Stage 2, готовит уточняющие вопросы для клиента (для Phase B).

---

## 2. Agent inventory — input/output контракты + риски

> Для каждого агента: что получает, что отдаёт, есть ли post-validator на коде, какие soft-contract violations возможны (наблюдаемые из истории).

### 2.1 Cleaner (01_cleaner_v1.md) — РИСК: **LOW**

- **Input:** raw transcript + `subject_name`, `narrator_name`
- **Output:** cleaned transcript (text)
- **Защиты на коде:** ❌ нет
- **Soft contract violations:**
  - Может «исправить» имя собственное неправильно (например, исказить редкое имя). Промпт: «если не уверен — оставь как есть и добавь [?]».
  - Может укоротить транскрипт (тёмный truncation), особенно при больших input — т.к. max_tokens ограничен. Уже было: cleaner обрезал на 16000 → подняли на 32000.
- **Что специфично Каракулине:** пара топонимов (Старобельск, Кировоград), редкие имена.
- **Для генерализации:** надо смотреть на разных субъектов, разные имена, разные топонимы.
- **Слепое пятно:** **нет проверки длины output vs input.** Если cleaner снова потеряет хвост (max_tokens переполнение) — мы не увидим.
- **Предлагаемая защита:** `validate_cleaner_volume(input_text, output_text)` — `len(output) >= 0.85 * len(input)` (не строже, потому что cleaner может выкинуть мусор).

### 2.2 Fact Extractor (02_fact_extractor_v3.4.md) — РИСК: **MEDIUM**

- **Input:** cleaned transcript + subject context + Phase A/B + existing_facts (Phase B)
- **Output:** fact_map JSON: persons[], events/timeline[], locations[], character_traits[], quotes[]
- **Защиты на коде:** ❌ нет (но Completeness Auditor работает после, см. 2.3)
- **Soft contract violations (наблюдаемые):**
  - **Регрессия #5 (Татьяна missing в bio_data.family) — недо-извлечение persons.** FE пропускает упоминания родственников.
  - Cross-person aliases pollution (Полина/Пелагея/Марфа) — закрыто Name Normalizer (task 016).
  - ASR variants без обоснования (расширили схему в v3.4 — confidence + reasoning).
- **Что специфично Каракулине:** известный субъект, 17-19 персон, ~30-40 events.
- **Для генерализации:** **stability score 82% на v37 двойном прогоне** — на других субъектах может быть и хуже.
- **Слепое пятно:** **нет проверки что FE не пропустил ключевые персоны/эпизоды.** Completeness Auditor закрывает это частично, но он сам — LLM, может сам пропустить.
- **Предлагаемая защита:** `validate_fact_map_pin_list` — если есть pin_list от предыдущего прогона, все pinned persons должны быть в текущем fact_map (или явно объяснено в rejected_pairs).

### 2.3 Completeness Auditor (16_completeness_auditor_v1.1.md) — РИСК: **LOW** (он сам — защита)

- **Input:** cleaned transcript + fact_map + (опционально) pin_list
- **Output:** auto_enrich (мержится в fact_map) + log_only_gaps (только warning)
- **Защиты на коде:** ✅ это сам валидатор для FE
- **Soft contract violations:**
  - Может пропустить gap (LLM-bias).
  - Может завысить confidence для auto_enrich (тогда мерж добавит спорный факт).
- **Что специфично Каракулине:** 17→19 персон при двойном прогоне, 2 rejected_pairs (Полина/Пелагея, тётя Маня/тётя Маша).
- **Для генерализации:** для других субъектов pin_list нужен от первого прогона. Сейчас pin_list работает только intra-Каракулина.
- **Слепое пятно:** **CA сам ничем не валидируется.** Если CA добавит ложный auto_enrich — fact_map испорчен, сквозит в Stage 2.

### 2.4 Historian (12_historian_v3.md) — РИСК: **MEDIUM**

- **Input:** fact_map (timeline, locations)
- **Output:** historical_context[] + era_glossary[] + suggested_insertions[]
- **Защиты на коде:** ❌ нет (но FC v2.13 теперь принимает historical_context как 3-й валидный источник)
- **Soft contract violations (наблюдаемые):**
  - **Галлюцинации малых населённых пунктов** — частично закрыто промптом (confidence: high/medium/low). Но low-confidence факты всё равно в output.
  - Может предложить мировое событие без связи (защита в промпте, но LLM-bias).
- **Что специфично Каракулине:** Кировоград (medium confidence), сельские локации (low confidence) — много low-confidence материала в output.
- **Для генерализации:** для городских субъектов (Москва, Питер) high-confidence, меньше галлюцинаций. Для сельских/эмигрантских (Дмитриев?) — может быть катастрофа.
- **Слепое пятно:** **нет проверки фактической верифицируемости historical_context.** Сейчас доверяем confidence от самого Historian. Может быть scripted check: «event X в году Y в локации Z — есть в Wikipedia/архив?»
- **Предлагаемая защита:** `validate_historian_confidence_gates` — если ratio low-confidence > 50%, warning. Если > 70%, block (для сельских — может быть ложно сложно).

### 2.5 Ghostwriter (03_ghostwriter_v2.16.md) — РИСК: **HIGH** (но защищён)

- **Input:** fact_map + historical_context (pass2/revision) + current_book (revision) + revision_scope (revision)
- **Output:** book.chapters[], callouts[], historical_notes[], bio_data
- **Защиты на коде:** ✅ `validate_revision_volume` (волна 1.2.2) + ✅ `merge_revision_out_of_scope_chapters` (волна 1.3.3) + ✅ `enforce_bio_data_completeness` (task 027)
- **Soft contract violations (наблюдаемые):**
  - **Регрессия #3 v43 — удаление эпизода вместо корректировки даты.** Закрыто волной 1.2.2.
  - **v52 — out-of-scope deletion при revision.** Закрыто волной 1.3.3.
  - **err_004 — historical_note дублирован в body нарратива.** В backlog, не закрыто.
  - **Регрессия #6 — галлюцинированная медаль.** Не закрыто.
- **Что специфично Каракулине:** 5 глав, ~16K символов, 2 итерации revision на v53b.
- **Для генерализации:** GW prompt v2.16 универсален (не упоминает Каракулину). bio_data структура может быть сломана для субъектов без явных родителей/детей в fact_map.
- **Слепое пятно:** **галлюцинации hallucinated facts (не в transcript+fact_map+historical_context).** Сейчас FC ловит post-factum; GW сам может выдавать. Регрессия #6 (медаль) — этот класс.
- **Покрытие:** GW — самый защищённый агент. Волны 1.2-1.3.3 на нём.

### 2.6 Fact Checker (04_fact_checker_v2.13.md) — РИСК: **MEDIUM**

- **Input:** book + fact_map + transcript + historical_context
- **Output:** verdict (pass/fail) + errors[] (legitimate_deletion, fix_instruction, evidence_in_other_chapter)
- **Защиты на коде:** ✅ `validate_revision_volume` ловит phantom legitimate_deletion + `_evidence_topic_overlap` + object markers
- **Soft contract violations (наблюдаемые):**
  - **5 итераций мутаций регрессии #3** (волны 1.2.3, 1.3, 1.3.1, 1.3.2). Закрыты.
  - **FC bias «адвокат удаления»** — даже после защит, FC находит ошибки охотнее чем не находит.
  - **Регрессия #6 — недо-выявление hallucination (медаль).** Открыто.
- **Что специфично Каракулине:** v52 показал 8 ошибок iter1 → PASS iter2 после fact_correction.
- **Для генерализации:** prompts/04_fact_checker_v2.13.md универсален. Object markers test работает для русского.
- **Слепое пятно:** **FC может промолчать про реальную галлюцинацию.** insufficient detection — другая сторона калибровки.
- **Покрытие:** FC — второй самый защищённый агент. Object markers test (волна 1.3.2) — структурная защита.

### 2.7 Literary Editor (05_literary_editor_v3.md) — РИСК: **HIGH** ⚠️ (НЕ ЗАЩИЩЁН)

- **Input:** book_FINAL_stage2 + fact_checker_warnings + phase A/B
- **Output:** book.chapters[] (обновлённые) + edits_log + verdict (pass/return_to_writer)
- **Защиты на коде:** ❌ только `validate_literary_editor_output` в `test_stage3.py:192` — проверяет что **главы по id не пропали** (chapter count preserved). НЕ проверяет:
  - Volume preservation
  - Fact preservation (event_id из timeline сохранены)
  - Callouts/historical_notes preservation
- **Soft contract violations (наблюдаемые):**
  - **v53b: удалил эпизод об огурцах.** Это новый класс мутации — Stage 3 silent deletion.
  - **Промпт прямо разрешает удалять «повторы»:** Направление 3 «ПОВТОРЫ — устранение дублей (одна история рассказана дважды)». LE счёл огурцы дублем темы «конфликт с зятем» и удалил.
  - Может «улучшать» текст до неузнаваемости (8 направлений работы → агрессивный rewrite).
- **Что специфично Каракулине:** 5 глав, эпизоды могут перекрываться по теме (огурцы vs счётчик — оба про зятя).
- **Для генерализации:** **этот класс мутации проявится у любого субъекта** — везде есть тематически близкие эпизоды.
- **Слепое пятно:** **самое опасное в пайплайне.** Между Stage 2 (защищённым) и Stage 4 (защищённым layout fidelity) есть Stage 3 LE — слепая зона.
- **Предлагаемая защита (волна 1.4.0):** см. раздел 7.

### 2.8 Proofreader (06_proofreader_v1.md) — РИСК: **LOW**

- **Input:** book после LE
- **Output:** book + style passport
- **Защиты на коде:** ❌ нет (есть `run_proofreader_per_chapter` без validator)
- **Soft contract violations:**
  - Промпт чёткий: «НЕ меняешь содержание, структуру, стиль или тон».
  - Может пропустить опечатки (LLM bias).
- **Что специфично Каракулине:** ничего особо.
- **Для генерализации:** универсален.
- **Слепое пятно:** теоретически Proofreader может «исправить» что-то семантическое. Не наблюдалось.
- **Покрытие:** в task 030 есть spec на скриптование (LanguageTool). Это закроет класс целиком.

### 2.9 Photo Editor (07_photo_editor_v1.md) — РИСК: **MEDIUM**

- **Input:** photos + fact_map.timeline
- **Output:** processed_photos[] + captions + timeline_period привязки
- **Защиты на коде:** ❌ нет
- **Soft contract violations:**
  - **task 018 — phase boundaries:** в gate2c фото не должны попадать. Защита в скриптах: `photos_mode: none` на gate2c. **task 021 — partial leak:** `--photos-dir` в основном flow Stage 4 не gate-фильтрован.
  - Может неправильно привязать фото к timeline_period.
- **Что специфично Каракулине:** на пилоте gate3 ещё не делали (нет фото загруженных).
- **Для генерализации:** для других субъектов с фото — будем тестировать.
- **Слепое пятно:** **photos_dir leak — task 021 в open backlog.** Нужно довести до полного gating.

### 2.10 Layout Designer (08_layout_designer_v3.22.md) — РИСК: **MEDIUM** (защищён)

- **Input:** book + photos + page_plan + cover
- **Output:** layout JSON для PDF renderer
- **Защиты на коде:** ✅ `validate_layout_fidelity.py` (волна 1.1) — paragraphs/callouts/historical_notes uniqueness + order + ref-architecture
- **Soft contract violations (наблюдаемые):**
  - **Регрессия #1, #2 v43 — потеря historical_notes, дубли callouts.** Закрыты волной 1.1.
  - **Регрессия #3 v45 — order_strict false-positive.** Закрыта волной 1.1.6 (per ref-type).
  - **task 022 — hybrid loop.** Counter не учитывает paragraph_ref vs paragraph_id. Открыто.
- **Что специфично Каракулине:** 5 глав, 79 paragraphs, 5 callouts, 4 historical_notes (на v53).
- **Для генерализации:** ref-architecture универсальна.
- **Слепое пятно:** task 022 (hybrid loop counter mismatch) — проявится при auto-patch на других субъектах.

### 2.11 QA Layout (09_qa_layout_v1.md) — РИСК: **LOW**

- **Input:** PDF + layout JSON
- **Output:** verdict (pass/fail) + issues[]
- **Защиты на коде:** ❌ это сам визуальный validator
- **Soft contract violations:**
  - Может пропустить визуальный баг (LLM vision bias).
  - Может сообщить ложный fail.
- **Что специфично Каракулине:** на пилоте gate2c всегда PASS.
- **Для генерализации:** Vision-агент, работает на любом PDF.
- **Слепое пятно:** **QA сам не валидируется.** Если он скажет PASS на проблемный PDF — мы не узнаем.

### 2.12 Cover Designer (13_cover_designer_v2.6.md) — РИСК: **LOW**

- **Input:** photos + subject metadata
- **Output:** cover composition JSON
- **Защиты на коде:** ❌ нет
- **Soft contract violations:**
  - **Усилено правило death_year (v2.6):** только явно из данных. Был класс галлюцинаций по year of death.
- **Что специфично Каракулине:** на пилоте обложку ещё не делали (gate4).
- **Для генерализации:** субъекты с неизвестным death_year — потенциальные галлюцинации.

### 2.13 Layout Art Director (15_layout_art_director_v1.8.md) — РИСК: **LOW**

- **Input:** photos + book text
- **Output:** page_plan для LD
- **Защиты на коде:** ❌ нет (есть `structural_layout_guard` в `pipeline_quality_gates.py` — частично)
- **Soft contract violations:**
  - **v1.8: микс вертикальных и горизонтальных фото запрещён** — это волна-фикс прошлая.
- **Что специфично Каракулине:** ещё не тестировано на gate3+.

### 2.14 Interview Architect (11_interview_architect_v4.1.md) — РИСК: **LOW**

- **Input:** fact_map + book + blitz_questions
- **Output:** уточняющие вопросы для клиента
- **Защиты на коде:** ❌ нет
- **Soft contract violations:**
  - Может задать вопрос на тему которая уже в blitz_questions (защита в промпте — дедупликация).
- **Что специфично Каракулине:** не блокирующий, фоновый агент.

---

## 3. Stage transitions — где данные ломаются

### 3.1 Stage 1 → Stage 2 (fact_map → book_draft)

- **Что передаётся:** clean fact_map (persons, timeline, locations, character_traits) + cleaned transcripts
- **Защиты:** ❌ нет schema validation. fact_map JSON может быть с любой структурой, GW не упадёт но интерпретирует криво.
- **Риск whack-a-mole:** **HIGH для других субъектов.** Каракулинский fact_map хорошо структурирован (timeline events с object markers «огурцы», «чемодан»). Если у Корольковой timeline events будут с минимальными source_quotes — FC v2.13 object markers test может не сработать (мало маркеров).

### 3.2 Stage 2 (revision loop) — внутри Stage

- **Что передаётся:** book_draft v1 → FC iter1 → GW revision → book_draft v2 → FC iter2 ...
- **Защиты:** ✅ `validate_revision_volume` + ✅ `merge_revision_out_of_scope_chapters` + ✅ evidence verification
- **Покрытие:** **самое защищённое место в пайплайне.**

### 3.3 Stage 2 → Stage 3 (book_FINAL_stage2 → LE) ⚠️

- **Что передаётся:** book_FINAL_stage2 + fc_warnings
- **Защиты:** ❌ нет fact preservation check. ❌ нет volume check. ❌ нет post-LE validator (только chapter-id-presence).
- **Риск whack-a-mole:** **HIGH.** v53b — пример. **Это priority #1 для волны 1.4.0.**

### 3.4 Stage 3 (LE → Proofreader) — внутри Stage

- **Что передаётся:** book после LE → Proofreader
- **Защиты:** ❌ нет
- **Риск:** Proofreader пишет «не меняй содержание», но он LLM. Низкий риск, но не нулевой.

### 3.5 Stage 3 → Stage 4 (book_FINAL_stage3 → LD)

- **Что передаётся:** финальный текст → LD + page_plan от AD
- **Защиты:** ✅ `validate_layout_fidelity` (волна 1.1)
- **Покрытие:** ОК.

### 3.6 Stage 4 → PDF (layout JSON → renderer)

- **Что передаётся:** layout.json → `pdf_renderer.py`
- **Защиты:** ✅ ref-architecture в renderer (волна 1.1) + photos_dir gating (task 018, частично)
- **Слепое пятно:** task 022 (hybrid loop counter). Открыто.

---

## 4. Слепые пятна — risk-ranked

### 4.1 HIGH — следующая волна должна закрыть

| # | Класс | Где | Проявился? | Кандидат закрытия |
|---|---|---|---|---|
| 1 | **Stage 3 LE silent deletion** | LE (агент 05) | ✅ v53b | **волна 1.4.0**: `validate_le_fact_preservation` + LE v3.1 anti-deletion |
| 2 | **Cleaner truncation на больших input** | Cleaner (01) | Один раз на 16K → 32K | волна 1.5.0: `validate_cleaner_volume` |
| 3 | **err_004: historical_note дубль в body нарратива** | GW (03) | На всех v45+ прогонах | волна 1.4.1: GW v2.16 → v2.17 рулевое + код проверка |
| 4 | **Регрессия #6: hallucinated medal (FC недо-выявление)** | FC (04) | v43 | волна 1.5.0: **Кандидат C из stocktake** или промпт-усиление |

### 4.2 MEDIUM — волна 1.5

| # | Класс | Где | Кандидат закрытия |
|---|---|---|---|
| 5 | **task 022 hybrid loop counter** | LD/auto-patch | Доделать существующую задачу |
| 6 | **Photo Editor photos_dir leak** | task 021 partial | Доделать gating в основном flow |
| 7 | **Регрессия #5: Татьяна missing в bio_data.family** | FE/CA | Расширить pin_list mechanism |
| 8 | **CA hallucinations в auto_enrich** | CA (16) | Confidence threshold gating |
| 9 | **Historian low-confidence pollution** | Historian (12) | volume-ratio gate |

### 4.3 LOW — волна 1.6 / backlog

| # | Класс | Где | Кандидат закрытия |
|---|---|---|---|
| 10 | **Cover Designer death_year hallucinations** | CD (13) | Уже частично закрыто в v2.6 |
| 11 | **QA Layout сам не валидируется** | QA (09) | scripted checks (после Photo Editor scripted) |
| 12 | **Proofreader semantic changes** | Proofreader (06) | task 030: scripted Proofreader |
| 13 | **Schema validation между stages** | All transitions | волна 1.6.0: `book_schema.py` validation |

### 4.4 STRUCTURAL — backlog (не делаем сейчас)

- **Кандидат A** (запрет cross-chapter `legitimate_deletion`) — упрощение, не закрытие нового класса
- **Кандидат B** (scripted revision FC→GW patches) — после Каракулины пилотного прогона
- **Кандидат D** (holistic скриптование 7 агентов) — после Каракулины

---

## 5. Generalization — Каракулина → Королькова → Дмитриев

### 5.1 Что специфично Каракулине

- **Транскрипты:** TR1 (Никита+Татьяна), TR2 (Никита+Татьяна разные эпизоды). Дочь рассказывает.
- **Эпохи:** 1920-2005 (война, послевоенное восстановление, 1990-е). Много исторического контекста.
- **Локации:** Старобельск, Кировоград, Тверь — medium/low confidence для Historian.
- **bio_data:** структурированные родители, дети, муж — все есть в fact_map.
- **Объём:** ~16K chars в book_FINAL, 5 глав.

### 5.2 Что универсально в коде/промптах

- **Все 14 промптов** — упоминают Каракулину только как пример (или вообще не упоминают). Но GW v2.15-v2.16 негативные примеры — на v52 кейсе Каракулины. Это **минорное отклонение**, не блокер.
- **Все 6 защитных функций** — параметризованы (`min_ratio`, `affected_chapters`, `topic_overlap_threshold`). Не Каракулина-специфичны.
- **Все 98 unit-тестов** — на синтетических данных, не на Каракулиной.
- **Stage-скрипты `test_stage1_karakulina_full.py` / `test_stage2_pipeline.py`** — содержат `CHARACTER_NAME = "Каракулина Валентина Ивановна"` в hardcode. **Это нужно параметризовать** перед Корольковой.

### 5.3 Риски при переходе

| Риск | Что произойдёт | Mitigation |
|---|---|---|
| **CHARACTER_NAME hardcoded в Stage скриптах** | Прогон Корольковой запустится с именем Каракулиной в логах | волна 1.5.0: параметризация |
| **DEFAULT_FACT_MAP / DEFAULT_TRANSCRIPT в скриптах** | Аналогично | волна 1.5.0: параметризация |
| **Object markers test (FC v2.13)** | Если у субъекта эпизоды описаны в fact_map с минимальными деталями, маркеров мало → FC будет ложно блокировать | Тестировать на Корольковой с увеличенным `EVIDENCE_MIN_SHARED_TOKENS` (с 2 на 3 если нужно) |
| **Historian low-confidence для нестандартных локаций** | Если у Дмитриева сёла — много low-confidence material | волна 1.5.0: confidence-ratio gate (не блок, но warning) |
| **bio_data.family для нестандартных семей** | Сирота / эмигрант / неполная семья — bio_data.family может быть пустым → enforce_bio_data_completeness может ложно блокировать | Расширить strict mode на opt-in |
| **Photos для субъектов без фото** | Уже закрыто (gate2c photos_mode=none). | OK |

### 5.4 Стратегия универсализации (волна 1.5.0)

1. Все hardcoded references на Каракулину в Stage-скриптах → параметризация через `--subject-name`, `--fact-map`, `--transcript`.
2. Промпты GW и FC — добавить позитивные примеры на других субъектах (если у нас будут v54+ прогоны Корольковой).
3. Конфигурируемые thresholds: `EVIDENCE_MIN_SHARED_TOKENS`, `min_ratio`, `EVIDENCE_TOPIC_OVERLAP_MIN` — вынести в pipeline_config.json (сейчас они в коде как константы).

---

## 6. Текущие защиты — inventory

### 6.1 Code-level (волны 1.1-1.3.3 + старее)

| Функция | Защищает | Покрытие |
|---|---|---|
| `validate_layout_fidelity.py` | LD output: paragraphs/callouts/notes uniqueness + order | ✅ |
| `validate_revision_volume` | GW revision volume drop | ✅ |
| `_verify_evidence_in_book` + `_evidence_topic_overlap` + `_topic_tokens` | FC `legitimate_deletion=true` evidence реальности | ✅ |
| `merge_revision_out_of_scope_chapters` | GW out-of-scope при revision | ✅ |
| `enforce_bio_data_completeness` | bio_data.family заполнен (task 027) | ✅ |
| `pipeline_quality_gates`: 7 функций | Stage 2/3 text checks (non_empty, required_entities, repetition, bio_not_empty, phase_b_volume_growth, structural_layout_guard, pdf_preflight) | ✅ |

### 6.2 Тесты

98 unit-тестов в 6 файлах:
- `test_revision_volume.py` (25)
- `test_validate_layout_fidelity.py` (24)
- `test_pdf_renderer_refs.py` (17)
- `test_quality_gates.py` (4)
- `test_fact_checker_historical_context.py` (9)
- `test_merge_revision_scope.py` (19)

**0 интеграционных тестов на Stage 1→4.** Интеграция тестируется только живыми прогонами Курсора.

### 6.3 Что НЕ покрыто

- LE post-validator (см. 4.1)
- Cleaner volume check (см. 4.1)
- Photo Editor photos_dir leak (см. 4.2)
- CA hallucinations gating (см. 4.2)
- Historian low-confidence ratio (см. 4.2)
- Schema validation между stages (см. 4.3)

---

## 7. План волн 1.4 → 1.6

### Волна 1.4.0 — Stage 3 LE protection (HIGH priority)

**Что закрывает:** регрессия #7 LE silent deletion (v53b).

**Стоимость:** ~2 дня.

**Состав:**
1. **Код (главное):** `validate_le_fact_preservation` в `pipeline_utils.py`
   - Snapshot: после Stage 2 выписываем все `event_id` из `fact_map.timeline` + 2-4 object markers для каждого
   - После LE: для каждого event проверяем что ≥2 маркеров в `book_FINAL_stage3` chapter content
   - Verdict: `blocked_event_lost_in_le` (если 0 маркеров) / `warning_event_significantly_modified` (если 1 маркер) / `ok` (≥2)
2. **Промпт:** LE v3 → v3.1
   - Top-priority правило: «не удаляй эпизоды (event_id из timeline). Можешь рефразировать, сокращать предложения внутри эпизода — но эпизод целиком должен остаться»
   - Различение «стилистический повтор фразы» vs «повтор сюжетного эпизода»
   - Negative example: огурцы из v53b (FC counter и огурцы — РАЗНЫЕ эпизоды, оба остаются)
3. **Интеграция в `test_stage3.py`:** между LE и Proofreader call → validate_le_fact_preservation. На FAIL — block + diagnostic JSON.
4. **Тесты:** ~15 unit-тестов, включая v53b регрессионный.

### Волна 1.4.1 — err_004 (historical_note duplication) (HIGH priority, маленькая)

**Что закрывает:** дубль текста historical_note в body нарратива (видно глазами на v45/v46 page-06).

**Стоимость:** ~0.5 дня.

**Состав:**
1. **Промпт:** GW v2.16 → v2.17 — правило «не вставляй текст historical_notes в body chapter content. Hist_notes только в `book.historical_notes[]`».
2. **Код:** `validate_no_historical_note_duplication` — сравнить text каждой historical_note против всех chapter contents. Если note text full match в body → block с verdict.
3. **Тест:** 5-7 unit, включая err_004 регрессионный.

### Волна 1.4.2 — Кандидат A из stocktake (упрощение)

**Что закрывает:** упрощение Stage 2 защит. Не новый класс — рефакторинг.

**Стоимость:** ~0.5 дня.

**Состав:**
1. **FC v2.13 → v2.14:** запрет `legitimate_deletion=true` для `framing_distortion` (cross-chapter). Только `hallucination` allowed.
2. **`validate_revision_volume`:** verdict `blocked_phantom_evidence` теперь применяется только для hallucinations. Для cross-chapter — severity=warning.
3. **Тесты:** регрессия закрытых классов (огурцы v50, счётчик v49, фельдшер v48) должны продолжать работать.

**Можно делать параллельно с 1.4.0/1.4.1** — независимый слой.

### Волна 1.5.0 — Generalization + remaining MEDIUM

**Что закрывает:** готовность к Корольковой/Дмитриеву + 5 классов из MEDIUM.

**Стоимость:** ~3-4 дня.

**Состав:**
1. Параметризация Stage скриптов (`--subject-name`, `--fact-map`, `--transcript`, etc).
2. Конфигурируемые thresholds (вынести в `pipeline_config.json`).
3. `validate_cleaner_volume` (Cleaner truncation guard).
4. `validate_historian_confidence_gates` (low-confidence ratio warning).
5. Pin-list расширение для регрессии #5 (Татьяна missing).
6. CA confidence threshold gating.
7. Доделать task 021 (photos_dir gating) и task 022 (hybrid loop counter).

**После 1.5.0 — verified на Корольковой/Дмитриеве (отдельный полный прогон).**

### Волна 1.6.0 — Schema validation + Proofreader script (LOW priority)

**Что закрывает:** schema drift между stages + scripted Proofreader (task 030).

**Стоимость:** ~3-5 дней.

**Состав:**
1. `book_schema.py` — JSON schema validation для каждого Stage transition.
2. task 030 Proofreader → script (LanguageTool + style_passport).

### Волны 2.0+ — после Каракулины (полный gate4)

- Кандидат B (scripted revision FC→GW patches).
- Кандидат C (FC source-scope preprocessing — NER + n-gram).
- Кандидат D (holistic скриптование остальных 6 агентов из 7).

---

## 8. Что НЕ делаем сейчас

- v53/v53b prog — **верификация на новом коде после волны 1.4.0** (Курсор повторит).
- Кандидат B/C из stocktake — **в волну 2.0+, после Каракулины полностью готова.**
- Любые точечные правки fact_map / book_FINAL руками.

---

## 9. Открытые задачи в backlog (32 task'а в `collab/tasks/`)

Беглый inventory статусов:

- **`done`:** 015 (Каракулина пилот), 019 (v37/v38 rerun), 016, 017, 018, 020, 021 (partial), 022 (open), 023, 024, 025, 026, 027, 028.
- **`new` или `in-progress`:** 030 (Proofreader spec, blocked-on-product), 031 (v52→v53→v53b verified, продолжается), 032 (волна 1.3.3 verified).
- **Backlog (фоновые баги, упоминания в handoff):** err_004, регрессия #5 (Татьяна), регрессия #6 (медаль).

**После аудита приоритеты должны измениться:**
- 030 → ждёт Дашин ответ (не блокирующее)
- err_004 → волна 1.4.1
- регрессии #5, #6 → волна 1.5.0
- task 022 → волна 1.5.0

---

## 10. Что я не покрыл в этом аудите

Признаю ограничения:

1. **n8n workflow.** Не смотрел `scripts/_build_n8n_phase_b.py`, не смотрел node connections. Если там есть слепые пятна — этот аудит их не нашёл.
2. **Telegram bot integration.** Не смотрел backend интеграцию (как Stage results доходят до клиента).
3. **YuKassa / payment flow.** Намеренно — Никита просил не трогать `_user_has_paid`.
4. **Stage 1 secondary persons instability** — есть task 026, я не разбирал глубоко.
5. **Cover Designer / Image generation.** Не смотрел SD интеграцию.

Если хотите расширить аудит на эти зоны — отдельный document `architecture-audit-extension-2026-05.md`. Стоимость +1-2 дня.

---

## 11. Рекомендация по порядку волн

**Сразу (после аудита):**
- **Волна 1.4.0** — Stage 3 LE protection (2 дня). Самый высокий приоритет — открытое слепое пятно подтверждено v53b.
- **Волна 1.4.1** — err_004 (0.5 дня). Маленькая, видна глазами Даше, важно для качества.
- **Волна 1.4.2** — Кандидат A (0.5 дня). Параллельно с 1.4.0.

**Затем (после v54 verified):**
- **Волна 1.5.0** — Generalization + MEDIUM (3-4 дня). Готовит к Корольковой.

**Затем (после Каракулины полного gate4):**
- **Волна 1.6.0** — Schema + Proofreader script (3-5 дней).
- **Волны 2.0+** — Кандидаты B/C/D из stocktake.

**Общая трудоёмкость волн 1.4-1.5 (до перехода на Королькову):** ~6-8 дней моей работы. Курсор не блокирован — он запускает прогоны параллельно.

---

## 12. Открытые вопросы команде

**Никита:**
1. Согласен с приоритетами 1.4.0 → 1.4.1 → 1.4.2?
2. Делать 1.4.0 и 1.4.2 параллельно (я могу) или последовательно?
3. После волны 1.5.0 — сразу Королькова или сначала довести Каракулину до gate4 (с фото)?
4. Аудит расширить (n8n / TG / payment) — сейчас или после 1.4-1.5?

**Даша:**
1. err_004 (видно на v45/v46 page-06) — критично или допустимо?
2. На сценарий C v53b (огурцы пропали в LE) — твоё видение про удаление эпизодов: НИКОГДА vs «допустимо если дубль с другой главой»?
3. Регрессия #6 (медаль hallucinated) — насколько критична? Двигать в волну 1.4 или оставить в 1.5.0?

---

## Что предлагаю делать прямо после твоего одобрения

1. Если Никита одобряет приоритеты — стартую **волну 1.4.0** (Stage 3 LE protection) сразу. ~2 дня моей работы, всё могу делать сам — это код + промпт + тесты, не прогон.
2. Параллельно — **волну 1.4.2** (Кандидат A, ~0.5 дня).
3. После 1.4.0 + 1.4.2 → **Курсор запускает v54** на TR2 для verified-on-run обоих волн.
4. Если v54 = scenario A → волна 1.4.1 (err_004) → дальше.

Жду решения.
