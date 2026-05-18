# Handoff Курсору — 2026-05-18 (для нового окна, перед v64 sprint)

> **Документ-страховка для нового окна Курсора.** Если предыдущая сессия Курсора кончилась — новое окно читает этот файл **первым** (5-10 мин) → готов работать на v64 sprint.
>
> **Предыдущий handoff** `handoff-cursor-2026-05-18-v64.md` (этот документ — финальный v64). До него: `handoff-cursor-2026-05-18-v63.md` (устарел, v63 уже verified).

---

## За 30 секунд: где мы

**v63 verified, НЕ PASS Ворот 1.** Курсор реализовал 11/11 tasks code-side, но Никита при чтении v63 идентифицировал что замечания **те же что в v62a** (5-й sprint цикла recurring Class 1/6/11/12 + новый Class 17 + missing Class 18 voice).

**Опус сделал stocktake** (`collab/context/stocktake-2026-05-18-v60-v63.md`) с архитектурным диагнозом: **validators detect, GW игнорирует**. 5 sprints закрывали конкретные patterns, GW находил новые формы.

**Никитин архитектурный sign-off** на 3 развилках 2026-05-18:
1. **1b — Revision loop через GW:** validators flag → GW переписывает flagged sentences
2. **2b — Distribution gate:** target 20K = 15K narrative + 3K paspart + 2K historical_notes (не padding нагон)
3. **3c — Class 18 voice:** personal-historical voice как требуемая категория

**Baseline для diff v64:** v63 (incremental) + v59 (reference «удачный бенч» по Никите).

---

## Команда и роли

| Роль | Кто | Доступ |
|------|-----|---------|
| Owner / Product Lead | Никита | Финальный sign-off |
| Архитектор + Продакт (объединено с 2026-05-17) | Опус (AI) | План перед волной, артефакт перед проектированием, spec'и, stocktake, run_registry |
| Исполнитель | Курсор (AI, ты) | Реализация по spec'ам, прогоны, verified-on-run |
| ~~Продакт (Даша)~~ | ~~отстранены~~ | Опус закрывает роль |

---

## ОБЯЗАТЕЛЬНО прочитать (20 мин)

В порядке приоритета:

1. **`collab/context/stocktake-2026-05-18-v60-v63.md`** ⭐ — главный документ. Анализ 5 sprints, recurring vs closed classes, архитектурный диагноз, обоснование revision loop. **5-10 мин**.
2. **`collab/tasks/v64-revision-loop-sprint.md`** — итоговый план v64 (10 tasks)
3. **`collab/context/dev-review-protocol.md`** — 6 правил архитектора
4. **`collab/context/run_registry.md`** — v4, секция v63 со всеми lessons
5. **`collab/context/known_episodes_karakulina.md`** v5 — pin-list (v6 будет после task 044h)
6. **`collab/runs/karakulina_v63/VERIFIED_ON_RUN_v63.md`** — твой v63 отчёт (для контекста что было)
7. **`collab/context/gate1_product_checklist.md`** — target (после v64-meta — distribution gate)

Specs v64 (читаешь параллельно с реализацией, в порядке dependency):

**Архитектурный ход (читать первыми, оба связаны):**
- `collab/tasks/049e-gw-v223-rule13-revision-compliance.md` ⭐ — GW v2.23 ПРАВИЛО 13
- `collab/tasks/049f-revision-hints-orchestrator.md` ⭐ — orchestrator + diff audit

**Distribution gate + historical_notes:**
- `collab/tasks/046d-historical-notes-enrichment.md` — post-Stage 2 enrichment
- `collab/tasks/v64-meta-target-reformulate.md` — gate1_checklist v2

**Класс 17 + 18 NEW:**
- `collab/tasks/043h-class17-narrative-truism.md` — narrative truism
- `collab/tasks/046e-class18-personal-historical-voice.md` — personal-historical voice

**Recurring patterns extend:**
- `collab/tasks/043d-2-class1-recurring-patterns.md` — Class 1 (speciality/episode/seemed/event_changed)
- `collab/tasks/043f-2-class11-recurring-in-principle-pattern.md` — Class 11 «в принципе, особенно по»

**Pin-list v6:**
- `collab/tasks/044h-pin-list-v6-maria-anya-dacha.md` — Мария/баба Аня + ep_029

---

## 6 правил архитектора (Опус соблюдает, ты сверяешь)

1. **План перед волной** — 10 готовых spec'ов
2. **Артефакт перед проектированием** — при verified-on-run открой text_FULL.md глазами
3. **Stocktake каждые 2-3 волны** — Опус сделал stocktake 2026-05-18 (4 волны overdue)
4. **Universality check** — 4 вопроса + subject-replacement test ПОСТРОЧНО в финальном тексте GW v2.23
5. **Run registry update** — после v64 Опус добавит секцию `## v64`. Ты — корректные `ghostwriter_version: v2.23` в Stage 2/3 manifest
6. **Prompt engineering дисциплина** — в v64 **одно** GW prompt-bump (ПРАВИЛО 13 revision compliance). НЕ bundle с другими новыми правилами

---

## 6 принципов команды (Никита постоянно повторяет)

1. Лес/деревья — лечим классы, не симптомы
2. Универсальность — все subjects
3. Класс багов, не симптом
4. Скрипт-first
5. Логирование
6. Медленно без откатов

---

## v63 outputs (контекст что было)

**Артефакты:** `runs/karakulina-v63-artifacts` @ `7f03452`. Файл `karakulina_text_FULL_20260518_172626.md`.

**Метрики v63:**
- Total chars: 17 750 (target 20K — fail)
- ch_02=6 872 / ch_03=5 053 / ch_04=2 230 / epilogue=968 / ch_01=3 249
- bio_data.family: 21 (Мария + баба Аня выпали vs v62a 23)
- historical_notes: 3 field + 0 inline (vs v62a 10+10 — большая регрессия)
- 11/11 tasks code-side PASS

**Что осталось как блокеры (твоя backlog для v64):**
- ch_02 +38 chars vs v62a (≈ноль роста главной главы)
- pin-list depth 3 errors (ep_003 призыв, ep_027 пенсия 1 sentence!, ep_028 свадьба, ep_030 перелом)
- discourse markers ch_02=2/8, ch_04=0/3
- Class 5 regression (Мария + баба Аня)
- Class 1 recurring (огурцы новая форма, «определила жизнь» recurring)
- Class 11 recurring («в принципе, особенно по»)
- Class 17 NEW (narrative truism «всё ложилось на плечи»)
- Class 18 missing (personal-historical voice)
- Factual drift (ep_029 «1990-е» — Никита: «раньше»)

**Versions использованные в v63:**
- GW v2.22, CA v1.5, FC v2.13, LE v3.1
- known_episodes_karakulina.md v5
- gazeteer v2, chronology_periods v1, bio_data_format v1
- narrative_stop_phrases v3, epilogue_rewrite_mapping v3

---

## v64 sprint — 10 tasks

**Главный план:** `collab/tasks/v64-revision-loop-sprint.md`.

### A. Архитектурный ход (revision loop) — критичные

| # | Task | Что |
|---|------|-----|
| 1 | **049e** | GW v2.22 → **v2.23** ПРАВИЛО 13: revision compliance (при revision pass выполнить revision_hints из validators) |
| 2 | **049f** | Revision_hints orchestrator (cco-скрипт большой): собирает validator outputs → формирует hints → диспатчер Stage 2 revision pass → diff audit |

### B. Distribution gate + historical_notes

| # | Task | Что |
|---|------|-----|
| 3 | **046d** | Post-Stage 2 enrichment historical_notes до ≥5 inline (reuse historian agent) |
| 4 | **v64-meta** | `gate1_product_checklist.md` v2: distribution gate (15K narrative + 3K paspart + 2K historical_notes) |

### C. Класс 17 + 18 NEW

| # | Task | Что |
|---|------|-----|
| 5 | **043h** | Class 17 «констатация очевидного» — `narrative_stop_phrases.json` v4 + validator + 4+ snapshot tests |
| 6 | **046e** | Class 18 personal-historical voice — pin-list `narrator_voice_anchors` + validator + 6+ snapshot tests |

### D. Recurring patterns extend

| # | Task | Что |
|---|------|-----|
| 7 | **043d-2** | Class 1 recurring — speciality_defined_life_v3 / episode_especially_remembered / motivation_attribution_seemed / stage_event_changed_X_extended + 6+ snapshot tests |
| 8 | **043f-2** | Class 11 recurring — «не любил X в принципе, особенно по Y» (pattern_options array для 3+ forms) + 5+ snapshot tests |

### E. Pin-list v6

| # | Task | Что |
|---|------|-----|
| 9 | **044h** | known_episodes_karakulina.md v5 → **v6**: required_persons markers (Мария + баба Аня), ep_029 «before_1990s» direction, narrator_voice_anchors секция |

### Sprint plan

| # | Task | Что |
|---|------|-----|
| 10 | **v64-revision-loop-sprint.md** | Итоговый план |

---

## Версионирование v64 (КРИТИЧНО — не перепутать)

- **GW v2.22 → v2.23** (1 правило per bump — ПРАВИЛО 13 REVISION COMPLIANCE per Правило 6)
  - Новый файл: `prompts/03_ghostwriter_v2.23.md` (копия v2.22 + ПРАВИЛО 13)
  - `pipeline_config.json.ghostwriter.prompt_file` → `"03_ghostwriter_v2.23.md"`
  - `_notes` обновить
- **CA v1.5** — без изменений
- **pin-list `known_episodes_karakulina.md` v5 → v6** (Мария/баба Аня required + ep_029 «before_1990s» + narrator_voice_anchors)
- **Configs:**
  - `narrative_stop_phrases.json: v3 → v4 (043h truism) → v5 (043d-2 Class 1) → v6 (043f-2 Class 11)`
  - `personal_historical_voice_config.json: v1` (новый)
  - `historical_notes_enrichment_config.json: v1` (новый)
  - `revision_orchestrator_config.json: v1` (новый, опционально — defaults в коде OK)
- **gate1_product_checklist.md: v2** (distribution gate)

---

## Branch стратегия v64

**Base:** main (после PR #30 merge — содержит run_registry v4) или v63 commit.

**Новая ветка:** `feat/v64-revision-loop-sprint` off main / v63.

**После прогона v64:**
- Push кода в `feat/v64-revision-loop-sprint`
- Push артефактов в `runs/karakulina-v64-artifacts` (отдельная ветка, как v54..v63)
- PR с обеих веток

---

## Прогон v64 — что именно запускать

1. Stage 1 split-extract (TR1 Phase A → TR2 Phase B → merge, `--known-episodes` v6)
2. Stage 2 GW v2.23 **first pass** → `book_draft.json`
3. Все validators на `book_draft`: chronology, pin_list_depth, style_checks, narrative_stop_phrases (v6), anti_facts, discourse_markers, **narrative_truism** (новый), **personal_historical_voice** (новый)
4. **Orchestrator (049f):** revision_hints собран → если есть → Stage 2 GW v2.23 **revision pass** с `call_type="revision"` → `book_after_revision.json`
5. **Diff audit** между draft и revision
6. **Historical_notes enrichment (046d):** если inline <5 → enrich post-revision
7. Stage 3 (LE + post-processing: gazeteer, persona_notes, relation_overrides, etc.)
8. `scripts/build_gate1_full_text.py` → `karakulina_v64_text_FULL.md`
9. Final validators (full coverage) → reports JSON

Создай `scripts/_run_v64_full.sh` (аналог `_run_v63_full.sh` с обновлёнными версиями + revision loop steps).

---

## Дисциплина для Курсора в v64

1. **GW v2.23 — ОДНО новое правило (ПРАВИЛО 13).** НЕ bundle.
2. **Universality check ПОСТРОЧНО** для финального текста GW v2.23 ПРАВИЛА 13 — все examples с placeholders ([Субъект], [Имя_близкого], [Период], [YYYY]). Опус уже выправил spec; перепроверь ещё раз перед commit (lesson v60 sprint).
3. **Verified-on-run = одно конкретное наблюдение per task.** Не «PASS / exit 0».
4. **Manifest versions** — Stage 2/3 manifest содержат `ghostwriter_version: v2.23`, `completeness_auditor_version: v1.5`.
5. **writing_notes proof-of-attention** (расширение из task 049d v63):
   - `rule13_revision_applied` (list)
   - `rule13_hints_received` (int)
   - `rule13_errors_applied` (int)
   - `rule13_revision_failed` (bool)
6. **Diff audit (049f)** — артефакт `revision_diff_audit.json` обязателен (показывает что только flagged sentences изменены)
7. **Snapshot tests mandatory:** 043h (4+), 043d-2 (6+), 043f-2 (5+), 046e (6+). Конкретные строки из v62a/v63 в pytest. **Без accumulated examples в тестах — pattern возвращается** (lesson v62a).
8. **NO bundle:** если возникает соблазн «давай ещё одно правило в GW», stop, backlog v65. Правило 6.
9. **Git push** обеих веток (`feat/v64-revision-loop-sprint` + `runs/karakulina-v64-artifacts`).
10. **Cross-check VERIFIED отчёт с реальными артефактами** — lesson v63 (Татьяна «1952 estimated» bug в self-report). Если в отчёте написал X — проверить что в JSON action.

---

## Targets для v64 (см. v64-revision-loop-sprint.md detail)

Distribution gate:
- **Total ≥ 20K**, **narrative (ch_02..epilogue) ≥ 15K**, **paspart ~ 3K**, **historical_notes ≥ 2K chars (≥5 inline + ≥3 field)**

Per-chapter floors:
- ch_02 ≥ 7K (главная) / ch_03 ≥ 4K / ch_04 ≥ 2.5K / epilogue 800-1500

Validators (после revision pass — все clean):
- chronology errors = 0
- pin_list_depth errors = 0
- discourse markers: ch_02 ≥ 8 / ch_03 ≥ 5 / ch_04 ≥ 3
- personal-historical voice (NEW): ch_02 ≥ 3 / ch_03 ≥ 2 / ch_04 ≥ 1
- narrative_truism (Class 17 NEW) errors = 0
- Class 1/11 recurring errors = 0

Content:
- Мария в bio_data.family ✅
- Баба Аня в narrative ch_03 (как comparison) ✅
- ep_029 без «1990-е» в narrative ✅

Architecture:
- writing_notes.rule13_* filled
- revision_failed = false
- diff_audit unauthorized_changes < threshold

---

## Risk + mitigation v64

**Risk A:** Revision pass ломает связность narrative.
- Mitigation: ПРАВИЛО 0 SCOPE LOCK + diff audit + LE Stage 3 fixes

**Risk B:** Revision_hints огромные (>20 errors) → revision fails.
- Mitigation: если >20 errors — architectural sign, revision_failed flag → stop, review

**Risk C:** Historical_notes enrichment добавит wrong context.
- Mitigation: historian battle-tested + anti_facts + grounding validators existing

**Risk D:** Pattern эволюция (Class 1/11) продолжается в новых формах.
- Mitigation: revision loop **архитектурно** закрывает (validator flag любой формы → GW переписывает). Snapshot tests = backup detection.

---

## Финансово

v64 = 1 прогон $4-6 (revision loop 2 LLM passes + historian enrichment 1 call).

---

## Когда v64 готов

1. Verified-on-run в PR (как для v63)
2. Опус откроет text_FULL.md независимо (Правило 2)
3. Опус обновит run_registry v5 секцией `## v64` (Правило 5)
4. Если все 11+ outcomes pass + revision_failed=false + distribution gate met → **PASS Ворот 1** → tag RP-1 → разблокировка backlog v65 + Королькова (task 053)
5. Если revision_failed или major regression → diagnostic, v65 = либо tactical fix либо radical (Editor agent / GW prompt refactor)

---

## Открытые ссылки

- **v63 артефакты:** `runs/karakulina-v63-artifacts` @ `7f03452`
- **v62a артефакты:** `runs/karakulina-v62-artifacts` @ `db03743`
- **v61 артефакты (baseline reference):** `runs/karakulina-v61-artifacts` @ `df6f3f3`
- **v59 артефакты (Никитин «удачный бенч»):** `feat/batch2fix-pin-list-and-classes` @ `26ce5cc`
- **PR #30 (run_registry v4):** https://github.com/NikitaMorgos/glava-bot/pull/30 (если ещё не merged — merge first для main update)
- **PR v64 (создаст Опус):** будет после v64 specs merged

---

## Что НЕ делать в v64 (явный список)

- ❌ Bundle 2+ GW правил в v2.23 (Правило 6 violation)
- ❌ Editor agent / GW prompt refactor (task 037) — backlog после v64 verify
- ❌ Auto-enforce delete для Class 17 truism — warning level, revision pass решает
- ❌ Создавать GW v2.21/v2.22 поверх existing — используй v2.23
- ❌ Padding narrative ради 20K — distribution gate явно запрещает (используй historical_notes enrichment)
- ❌ Подключение Корольковой — после RP-1
- ❌ Этап 2 (Proofreader scripted, task 030) — после Ворот 1 PASS
- ❌ Новый прогон v65 до verified v64

---

## Версии этого документа

| Версия | Дата | Изменение | Кто |
|---|---|---|---|
| v1 | 2026-05-18 | Создание перед v64 sprint после v63 verified review + stocktake + Никитин 1b+2b+3c sign-off | Опус |
