# v64 sprint: Revision loop architecture + Class 17/18 + distribution gate

**Статус:** `new`
**Sprint ID:** v64
**Автор:** Опус (роль архитектор+продакт)
**Дата создания:** 2026-05-18
**Триггер:** v63 верифицирован (НЕ PASS), Никитин feedback идентифицировал 5-й sprint цикла (recurring Class 1/6/11/12 в новых формах). Никитино решение по 3 архитектурным развилкам: **1b (revision loop) + 2b (distribution gate) + 3c (Class 18 voice)**
**Связано:** stocktake-2026-05-18-v60-v63.md (полный диагноз); run_registry v4 (v63 verification); правила 1-6 архитектора

---

## Контекст

После 5 sprints (v60→v63) — **diminishing returns** на тактике добавления GW правил под каждый recurring pattern. Validators detect, GW игнорирует. Niki: «те же замечания что в v62».

**Архитектурное решение v64:**
1. **Revision loop** — GW v2.23 ПРАВИЛО 13 + orchestrator → validators flag → GW переписывает (закрывает класс «validators висят в воздухе»)
2. **Distribution gate** — 20K target = 15K narrative + 3K paspart + 2K historical_notes (закрывает class «GW нагон объёма»)
3. **Class 18 voice** — personal-historical voice как требуемая категория (Niki feedback «нет исторических вкраплений рассказчика»)

**Per принципы:**
- ✅ Лес/деревья: один архитектурный ход (revision loop), не точечно
- ✅ Универсальность: revision loop generic + Class 17/18 patterns generic
- ✅ Класс багов: Class 17 NEW + Class 18 NEW, не точечные правки
- ✅ Скрипт-first: 8 скриптовых задач + 1 GW prompt (revision compliance — необходимо для архитектуры)
- ✅ Логирование: run_registry v5 + stocktake-2026-05-18 + handoffs
- ✅ Медленные шаги: одно GW правило (per Правило 6), snapshot tests, mitigation для revision loop

---

## Universality check (по всему sprint)

- [x] **Промпт без конкретики:** GW v2.23 ПРАВИЛО 13 использует placeholders ([Субъект], [Имя_близкого], [Период], [YYYY])
- [x] **Subject-specific в configs:** pin-list v6 (Мария/баба Аня + ep_029), narrator_voice_anchors per subject, narrative_stop_phrases v6 generic, chronology_periods generic
- [x] **Алгоритм generic:** revision loop, historical_notes enrichment, Class 17/18 validators — все применимы к любому subject
- [x] **Subject-replacement test:** для Корольковой меняются configs/pin-list, code/prompts не меняются ✅

---

## 10 tasks

### A. Архитектурный ход (revision loop) — 2 tasks

| # | Task | Тип | Mitigates |
|---|------|-----|-----------|
| 1 | **049e** | GW prompt-bump (1 rule) | Архитектурный класс «validators detect, GW игнорирует» (5 sprints цикл) |
| 2 | **049f** | cco-скрипт большой (orchestrator) | Архитектурный класс — собирает hints, dispatch GW revision, diff audit |

### B. Distribution gate + historical_notes (2 tasks)

| # | Task | Тип | Mitigates |
|---|------|-----|-----------|
| 3 | **046d** | cco-скрипт + historian reuse | Class 9 historical_notes underutilization + M1 объём через objective context |
| 4 | **v64-meta** | docs | Product-decision (Никита 2b) — distribution gate format |

### C. Класс 17 + 18 NEW (2 tasks)

| # | Task | Тип | Mitigates |
|---|------|-----|-----------|
| 5 | **043h** | конфиг + скрипт + snapshot | Class 17 NEW «констатация очевидного» (v63 feedback) |
| 6 | **046e** | конфиг + скрипт + pin-list | Class 18 NEW «personal-historical voice» (v63 feedback 3c) |

### D. Recurring patterns extend (2 tasks)

| # | Task | Тип | Mitigates |
|---|------|-----|-----------|
| 7 | **043d-2** | конфиг + snapshot | Class 1 recurring patterns (3 новые формы v63) |
| 8 | **043f-2** | конфиг + snapshot | Class 11 recurring «в принципе, особенно по X» |

### E. Pin-list v6 + meta (1 task)

| # | Task | Тип | Mitigates |
|---|------|-----|-----------|
| 9 | **044h** | pin-list edit + parser ext | Мария/баба Аня Class 5 regression + ep_029 «дача раньше 1990-х» уточнение |

### Sprint plan (этот document)

| # | Task | Тип |
|---|------|-----|
| 10 | **v64-revision-loop-sprint.md** | sprint plan |

---

## Версионирование v64

- **GW: v2.22 → v2.23** (1 правило per bump — ПРАВИЛО 13 revision compliance)
- **CA: v1.5** (без изменений)
- **pin-list `known_episodes_karakulina.md`: v5 → v6** (Мария/баба Аня required + ep_029 уточнение + narrator_voice_anchors секция)
- **configs:**
  - `narrative_stop_phrases.json: v3 → v6` (043g v3 → 043h v4 truism → 043d-2 v5 Class 1 → 043f-2 v6 Class 11)
  - `personal_historical_voice_config.json: v1` (новый)
  - `historical_notes_enrichment_config.json: v1` (новый)
  - `revision_orchestrator_config.json: v1` (новый, опционально)
- **gate1_product_checklist.md: v2** (distribution gate)

---

## Стратегия v64 verify

1. Stage 1 split-extract (TR1 → TR2 → merge) с pin-list v6
2. Stage 2 GW v2.23 first pass → `book_draft.json`
3. **Все validators** на book_draft (chronology, pin_list_depth, style_checks, narrative_stop_phrases, anti_facts, discourse_markers, **narrative_truism новый**, **personal_historical_voice новый**)
4. **Orchestrator (049f):** соберёт revision_hints → передаст в Stage 2 second pass с `call_type="revision"`
5. Stage 2 GW v2.23 revision pass → `book_after_revision.json`
6. **Diff audit:** сравнить draft vs revision, flag unauthorized_changes
7. **Historical_notes enrichment (046d):** если inline <5 → enrich post-revision
8. Stage 3 (LE + post-processing — gazeteer, persona_notes, relation_overrides и т.д.)
9. `scripts/build_gate1_full_text.py` → `karakulina_v64_text_FULL.md`
10. Final validators (full coverage)

**Финансово:** $4-6 per прогон (revision loop 2 LLM-passes + historian enrichment 1 LLM call).

---

## Targets для v64 (per distribution gate + new validators)

| Metric | Target | Validator/check |
|--------|--------|-----------------|
| **Total chars (build_gate1)** | ≥ 20 000 | build_gate1 |
| **Narrative (ch_02..epilogue)** | ≥ 15 000 | build_gate1 sum |
| **Paspart (ch_01.content)** | ~ 3 000 | build_gate1 ch_01 |
| **Historical_notes total chars** | ≥ 2 000 | sum from field + inline |
| **Historical_notes inline (`***...***`)** | ≥ 5 | task 046d enrichment |
| **Historical_notes field** | ≥ 3 | existing |
| ch_02 chars | ≥ 7 000 | build_gate1 |
| ch_03 chars | ≥ 4 000 | build_gate1 |
| ch_04 chars | ≥ 2 500 | build_gate1 |
| epilogue chars | 800–1 500 | build_gate1 |
| **Pin-list depth errors** | 0 | task 050 |
| **Chronology errors** | 0 (after revision) | task 048 + 048d |
| **Discourse markers ch_02** | ≥ 8 | task 049 |
| **Discourse markers ch_03** | ≥ 5 | task 049 |
| **Discourse markers ch_04** | ≥ 3 | task 049 |
| **Personal-historical voice ch_02** | ≥ 3 | task 046e NEW |
| **Personal-historical voice ch_03** | ≥ 2 | task 046e NEW |
| **Personal-historical voice ch_04** | ≥ 1 | task 046e NEW |
| **Narrative truism (Class 17) errors** | 0 (after revision) | task 043h NEW |
| **Class 1 recurring errors** | 0 (after revision) | task 043d-2 |
| **Class 11 recurring errors** | 0 (after revision) | task 043f-2 |
| **Mary in bio_data.family** | ✅ present | task 044h |
| **Баба Аня в narrative ch_03** | ✅ present (как comparison) | task 044h |
| **ep_029 «1990-е» в narrative** | ❌ absent (или с маркером «до 1990-х») | task 044h |
| **Stage 2 manifest** | `ghostwriter_version: v2.23`, `completeness_auditor_version: v1.5` | manifest |
| **writing_notes.rule13_***  | filled | task 049e schema |
| **revision_failed** | false | task 049e + 049f |
| **FC verdict** | PASS iter1-2 | FC |

---

## Drivers объёма (для distribution gate)

Цель — выйти на 20K Total = 15K narrative + 3K paspart + 2K historical_notes.

| Драйвер | Эффект |
|---------|--------|
| **GW v2.23 ПРАВИЛО 13 revision compliance** | depth ≥3 sentences per pin-list event при revision (если flagged) → +800-1200 chars в ch_02 |
| **046d historical_notes enrichment** | +5 inline notes × ~150 chars = +750 chars в historical_notes (closes Class 9) |
| **046e Class 18 voice markers** | +3-5 personal-historical markers × ~80 chars = +400 chars (часть narrative) |
| **043h Class 17 truism removal** | −300-500 chars (удаление лишнего, ОК — компенсируется historical enrichment) |
| **044h pin-list v6 Мария/баба Аня** | restoration content (+200-400 chars где-то в narrative ch_03) |

**Чистый эффект объёма:** +1500-2000 chars vs v63 (18 372 → ~20K). Дополнительно distribution становится здоровее (historical_notes restored, narrative quality up).

---

## Risk и mitigation

**Risk A: Revision pass ломает связность.**

**Mitigation:**
- ПРАВИЛО 13 explicit «только flagged sentences» + ПРАВИЛО 0 SCOPE LOCK
- Diff audit (049f) — flag unauthorized changes
- LE Stage 3 + post-processing fix минор issues
- Если major breakage — revision_failed flag → STOP, Опус review

**Risk B: GW v2.23 cognitive overload — ПРАВИЛО 12 (объём) + 13 (revision) + existing 1-11.**

**Mitigation:**
- ПРАВИЛО 13 applies **только** при revision pass (call_type="revision"), не при first draft
- First draft использует ПРАВИЛО 12, не 13
- Revision pass — focused (только revision_hints), меньше cognitive load
- Per Правило 6 — одно правило per bump

**Risk C: Revision_hints огромные (50+ flags) → revision pass fails.**

**Mitigation:**
- Severity filter: только errors must_apply (warnings — optional)
- Если errors >20 — это **архитектурный** sign (что-то фундаментально not работает) → revision_failed flag, stop, review
- Max 1 revision pass в v64 (avoid loop forever)

**Risk D: Historical_notes enrichment добавит wrong context.**

**Mitigation:**
- Historian agent battle-tested
- Anti_facts validator + historical_note_grounding (existing) проверяют добавленный content

**Risk E: Distribution gate сложнее в восприятии (vs single number).**

**Mitigation:**
- Build_gate1 summary показывает distribution breakdown
- Checklist v2 содержит таблицу + tolerance

---

## Что НЕ делаем в v64 (явный список)

- ❌ GW prompt refactor (task 037) — backlog после v64 verify
- ❌ Editor agent (Опция c развилка 1) — backlog
- ❌ Subject-specific patterns в Class 18 (только generic в v64; subject-specific anchors в pin-list для GW guidance)
- ❌ Auto-enforce delete для Class 17 (warning level, revision pass решает; backlog v65 если revision insufficient)
- ❌ Bundle 2+ GW rules — Правило 6 violation
- ❌ Подключение Корольковой — после RP-1
- ❌ Этап 2 (Proofreader scripted, task 030) — после Ворот 1 PASS

---

## Открытые вопросы

1. **Revision pass max iterations:** в v64 = 1. Backlog v65 если single pass недостаточен (e.g. revision переписал, но создал новые flags). Уточнить логику — отдельный документ.

2. **Validator coverage гарантии:** что если validator имеет false negative (не нашёл pattern которое реально присутствует)? GW игнорирует non-flagged. Mitigation: snapshot tests + Опусов independent verify (после каждого прогона открыть text_FULL и сравнить с expected).

3. **Historian agent stability:** historian battle-tested в production, но при enrichment вызывается на коротких inputs. Backlog: проверить quality enrichment notes на v64 артефактах.

4. **Distribution gate tolerance:** 14-15K narrative — warning или strict fail? Default warning, calibrate per v64.

---

## История

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-18 | `new` | Опус |
