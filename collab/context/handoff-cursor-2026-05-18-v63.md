# Handoff Курсору — 2026-05-18 (для нового окна, перед v63 sprint)

> **Документ-страховка для нового окна Курсора.** Если предыдущая сессия Курсора кончилась — новое окно читает этот файл **первым** (5-10 мин) → готов работать на v63 sprint.
>
> **Предыдущий handoff** `handoff-cursor-2026-05-18.md` (перед v62a) — устарел; v62a реализован, verified. Этот — текущий.

---

## За 30 секунд: где мы

**v62a verified, НЕ PASS Ворот 1.** 10/11 scripted tasks PASS (Марфа в bio_data, Contributors раздел, paspart Калинин, anti_facts af_002 fired, render bug `?: ?` ушёл и т.д.). Но **3 блокера** остаются:

1. **Объём 17 750 chars < 20K target** (vs v61 20 272 и v59 19 930 — регрессия)
2. **Pin-list depth 5 errors** (свадьба, операция, Кирсанов, пенсия, Капошвара, перелом — все 2 sentences вместо ≥3)
3. **Discourse markers all 3 chapters below threshold** (ch_02=0/8, ch_03=2/5, ch_04=0/3)

Все 3 — **GW behaviour issues**, не скриптами лечатся.

После Никитиного live review v62a + мои 3 блокера = **11 items для v63 sprint** (combined, Опция X).

**Baseline для diff:** v59 (Никитино решение «v59 самый удачный бенч»).

---

## Команда и роли

| Роль | Кто | Доступ |
|------|-----|---------|
| Owner / Product Lead | Никита | Финальный sign-off на все архитектурные ходы |
| **Архитектор + Продакт (объединено с 2026-05-17)** | **Опус** (AI) | План перед волной, артефакт перед проектированием, spec'и, stocktake, run_registry |
| Исполнитель | **Курсор** (AI, ты) | Реализация по spec'ам, прогоны на сервере, verified-on-run отчёты |
| ~~Продакт (Даша)~~ | ~~Даша + Дашин Клод~~ | **Отстранены с 2026-05-17** (временно). Опус закрывает их роль. |

---

## ОБЯЗАТЕЛЬНО прочитать (15-20 мин)

В порядке приоритета:

1. **`collab/tasks/v63-combined-sprint.md`** — главный план v63 (11 tasks)
2. **`collab/context/architecture-stocktake-2026-05-17.md`** — состояние, 16+ классов, тренды v54→v62a, backlog
3. **`collab/context/dev-review-protocol.md`** — **6 правил архитектора** (Правило 4 Universality, Правило 6 prompt engineering)
4. **`collab/context/run_registry.md`** — реестр версий всех прогонов v54-v62a (v63 секцию Опус добавит после прогона)
5. **`collab/context/known_episodes_karakulina.md`** v4 — pin-list source of truth (Anti-facts, Contributors). Будет → v5 в task 051d
6. **`collab/runs/karakulina_v62/VERIFIED_ON_RUN_v62.md`** — твой собственный verified отчёт v62a (что закрылось, что нет)
7. **`collab/context/handoff-opus-2026-05-18-pre-v63.md`** — для context: что Опус видит и что планировал

Specs v63 (читаешь параллельно с реализацией):
- `collab/tasks/048d-chronology-children-general-context.md`
- `collab/tasks/044d-2-render-bug-residual-duplicates.md`
- `collab/tasks/043g-narrative-event-changed-life-pattern.md`
- `collab/tasks/051d-pinlist-dacha-year-uncertain.md`
- `collab/tasks/043f-class11-awkward-not-loved-x-by-y-z.md`
- `collab/tasks/038c-ca-pinlist-event-strict-source-location.md`
- `collab/tasks/043e-2-epilogue-overcrowded-quotes.md`
- `collab/tasks/044g-bio-data-family-format-consistency.md`
- `collab/tasks/052d-contributors-simplify-fio-relation-only.md`
- `collab/tasks/049d-gw-v222-rule12-narrative-depth-voice-volume.md` ⭐ (главный driver объёма)

---

## 6 правил архитектора (Опус соблюдает, ты сверяешь)

1. **План перед волной** — у тебя 11 готовых spec'ов в PR #29. Реализация по ним.
2. **Артефакт перед проектированием** — при verified-on-run открой text_FULL.md глазами, не proxy-метрики.
3. **Stocktake каждые 2-3 волны** — после v63 (после v60/v61/v62a — это 4-я волна) обязательный stocktake (Опус ведёт).
4. **Universality check (для каждой задачи)** — 4 вопроса в template `_template.md`: Промпт без конкретики subject? Subject-specific в JSON конфигах? Алгоритм generic? Subject-replacement test пройден?
5. **Run registry update** — после v63 прогона Опус добавит секцию `## v63` со всеми версиями. Ты — корректные `ghostwriter_version: v2.22` + `completeness_auditor_version: v1.5` в Stage 2/3 manifest.
6. **Prompt engineering дисциплина** — **в v63 ОДИН GW prompt-bump** (ПРАВИЛО 12, 3 metrics одной семьи) + один CA minor patch (ПРАВИЛО 7). Остальные 9 — scripted. НЕ bundle лишних правил.

---

## 6 принципов команды (Никита постоянно повторяет)

1. Лес/деревья — лечим классы багов, не точечные эпизоды
2. Универсальность — пайплайн для всех биографий
3. Класс багов, не симптом
4. Скрипт-first
5. Логирование (run_registry + Правило 5)
6. Медленно без откатов

---

## v62a outputs (что было, чтобы ты не повторял)

**Артефакты:** ветка `runs/karakulina-v62-artifacts` @ `db03743`. Файл `collab/runs/karakulina_v62/karakulina_v62_text_FULL_final.md`.

**Книга:** Total chars 17 750 (build_gate1 own counter, **НЕ** file_size — lesson v62a:
file_size = 22 927 включает paspart markdown + Contributors + decorations; реальный
book content = build_gate1 «Total chars» в сводке = source of truth для gate1 metrics).

**Per-chapter:** ch_01=3 354 / ch_02=6 834 / ch_03=4 450 / ch_04=2 327 / epilogue=785.

**Versions использованные в v62a:**
- GW v2.20, CA v1.4, FC v2.13, LE v3.1
- known_episodes_karakulina.md v4 (+ Anti-facts, Contributors)
- gazeteer_karakulina.json v2 + paspart-only temporal
- pin-list-bypass для CA strict (task 038b)

**FC verdict:** PASS iter1 (0 critical, 0 major)

**10/11 PASS:**
- 044d render bug чистый
- 044e Бабушка Марфа в family
- 044f Внук Никита/Внучка Даша notes
- 049c discourse_markers validator работает (но GW не пишет markers → блокер v63)
- 051c paspart Тверь→Калинин
- 048c chronology grandchildren (Даша 1973 пример сработал в детекторе)
- 052c Contributors раздел (4 имени из pin-list)
- 043d narrative stop phrases warning «определило жизнь»
- 045e timeline anchors widowhood separate
- 043e anti_facts af_002 акушерство fired

**Bugs found & fixed during sprint (твои бонусы Курсора):**
1. `narrative_stop_phrases.json`: `speciality_defined_life` + `helping_at_important_moments` не были в `scoped_to_narrative_and_epilogue` → fix
2. `narrative_stop_phrases.json`: `\\s+` → `\\s*` в pattern (не матчил «специальность,»)
3. `test_stage3.py`: `build_gate1_text()` без `pin_list_path` → Contributors skipped, fix
4. Локально `known_episodes_karakulina.md` v2 → обновил до v4

---

## v63 sprint — 11 tasks

**Главный план:** `collab/tasks/v63-combined-sprint.md`.

### A. Scripted fixes (9 tasks)

| # | Task | Что |
|---|------|-----|
| 1 | **048d** | Chronology «дети» general context (Class 12; «В Германии Валентина сидела с детьми 1946-48» когда дети ещё не родились) |
| 2 | **044d-2** | Render bug дубль перед «Личные данные» + malformed Нинвана override entry |
| 3 | **043g** | Class 6 narrative пафос «событие, которое изменило» + «типичной для поколения» + «в этой типичности своя уникальность» |
| 4 | **051d** | Pin-list ep_029 продажа дачи → year=unknown + generic `year_confidence` convention |
| 5 | **043f** | Class 11 awkward «не любил X (особенно)? по Y и Z» recurring + **mandatory snapshot test** |
| 6 | **043e-2** | Epilogue overcrowded quotes detection (>4 cited phrases per paragraph) |
| 7 | **044g** | Bio_data.family единый формат «**Родство** — Имя_полное (note)» + locative case (Калинин → Калинине) |
| 8 | **052d** | Contributors раздел simplify — только ФИО + родство (без «основной рассказчик / со-интервьюер / реплики») |

### B. CA minor prompt patch (1 task)

| # | Task | Что |
|---|------|-----|
| 9 | **038c** | CA v1.4 → **v1.5** ПРАВИЛО 7 named entity preservation (location/name/year) — огурцы «из Молдавии», не «из командировок» |

### C. GW prompt-bump (1 task, главный driver объёма)

| # | Task | Что |
|---|------|-----|
| 10 | **049d** | GW v2.20 → **v2.22** ПРАВИЛО 12 narrative depth + voice + объём ≥20K |

### Sprint plan: 11-й документ

- **`collab/tasks/v63-combined-sprint.md`** — итоговый план с targets, версионированием, что НЕ делаем

---

## Версионирование (КРИТИЧНО — не перепутать)

- **GW v2.20 → v2.22** (skip v2.21!)
  - v2.21 = откатанная v60 версия с ПРАВИЛАМИ 9/10/11 (temporal/contributors/chapter_sections) — она показала регрессию, в v61 откатились на v2.20
  - **v2.22 = v2.20 + ПРАВИЛО 12** (новое). НЕ переписывать существующий `prompts/03_ghostwriter_v2.21.md` — он archived
  - Новый файл: `prompts/03_ghostwriter_v2.22.md`
  - `pipeline_config.json.ghostwriter.prompt_file` → `"03_ghostwriter_v2.22.md"`
  - `_notes` обновить: «v2.22 (2026-05-18, task 049d, v63 sprint): добавлено ПРАВИЛО 12 narrative depth + voice + объём ≥20K. Per Правило 6 — одно правило per bump (3 metrics одной семьи)»

- **CA v1.4 → v1.5** (1 правило per bump, Правило 6)
  - Найди CA prompt файл (вероятно `prompts/04_completeness_auditor_v1.4.md` или похожий)
  - Новый файл `prompts/04_completeness_auditor_v1.5.md` = v1.4 + ПРАВИЛО 7
  - `pipeline_config.json.completeness_auditor.prompt_file` → новая версия
  - `_notes` обновить

- **pin-list `known_episodes_karakulina.md` v4 → v5**
  - ep_029 year → `unknown`, описание уточняется
  - Шапка версии обновляется (см. формат в файле)

- **Configs обновления:**
  - `narrative_stop_phrases.json: v2 → v3` (+ categories: event_that_changed_life, typical_for_generation, in_this_typicality_uniqueness, class11_not_loved_x_by_y_and_z)
  - `epilogue_rewrite_mapping.json: v2 → v3` (+ rules typical_for_generation, in_this_typicality_uniqueness)
  - `bio_data_format_config.json: v1` (новый, generic)
  - `chronology_periods_karakulina.json: v1` (новый, optional per subject)

---

## Branch стратегия v63

**Base:** v62a final commit (`feat/v62a-pointed-fixes` @ `db03743`).

**Новая ветка:** `feat/v63-combined-sprint` off `db03743` (после merge'а v62a в основную линию — координируй с Никитой; если v62a ещё в feature branch, бранчуй из неё).

**После прогона v63:**
- Push кода в `feat/v63-combined-sprint`
- Push артефактов в `runs/karakulina-v63-artifacts` (отдельная ветка, как v54..v62a)
- PR с обеих веток (или комбинированный)

---

## Прогон v63 — что именно запускать

1. Stage 1 split-extract (TR1 Phase A → TR2 Phase B → merge, with `--known-episodes=collab/context/known_episodes_karakulina.md`)
2. Stage 2 (GW v2.22) — здесь главное место где ПРАВИЛО 12 должен сработать
3. Stage 3 (LE v3.1 + post-process: gazeteer морфо, persona_notes, relation_overrides, etc.)
4. `build_gate1_full_text.py` → `karakulina_v63_text_FULL.md`
5. Validators: discourse_markers, pin_list_depth, chronology_check, timeline_anchors, anti_facts, style_checks, **epilogue_density_check** (новый task 043e-2)

Если есть `scripts/_run_v62_full.sh` — создай аналогичный `_run_v63_full.sh` с обновлёнными версиями prompts и configs.

---

## Дисциплина для Курсора в v63

1. **GW v2.22 — ОДНО новое правило (ПРАВИЛО 12)** + 3 metrics одной семьи (depth/voice/volume). НЕ добавляй другие правила в этот bump.
2. **CA v1.5 — ОДНО новое правило (ПРАВИЛО 7)** named entity preservation. НЕ bundle.
3. **Universality check построчно** для финальных текстов GW v2.22 + CA v1.5 — все examples с placeholders (`[Субъект]`, `[Рассказчик]`, `[Город_канон]`, `[конкретная_страна]`), **без** «Каракулина»/«Татьяна»/«Молдавия»/«1946». Опус уже выправил specs (lesson v60 sprint: проскочил «Татьяна 1956 Тверь» в финальный prompt → регрессия). Перепроверь ещё раз перед commit.
4. **Verified-on-run = одно конкретное наблюдение** про артефакт. Не «PASS / exit 0», а «открыл text_FULL.md ch_04 line N: «привёз из Молдавии», не «из командировок»».
5. **Manifest versions** — Stage 2/3 manifest должны содержать `ghostwriter_version: "v2.22"`, `completeness_auditor_version: "v1.5"`.
6. **writing_notes proof-of-attention** (новое в task 049d) — GW output должен содержать:
   - `writing_notes.rule12_chars_estimate` (number)
   - `writing_notes.rule12_pin_list_depth_pass` (boolean)
   - `writing_notes.rule12_voice_count_per_chapter` (dict)
   Если эти поля missing — flag warning в style_checks.
7. **Snapshot tests mandatory** для recurring patterns (Class 11 task 043f, Class 1 task 038c) — конкретные strings из v62a/v59 в pytest. **Без accumulated examples в тестах — pattern возвращается** (lesson v62a).
8. **NO bundle:** если по ходу реализации возникает соблазн «давай ещё одно правило в GW», stop, добавь в backlog v64. Правило 6 архитектора.
9. **Git push** обеих веток (`feat/v63-combined-sprint` + `runs/karakulina-v63-artifacts`). Не забывай.

---

## Targets для v63 (что должно получиться)

| Metric | Target | Validator |
|--------|--------|-----------|
| Total chars (build_gate1 counter) | **≥ 20 000** | build_gate1 «Total chars» |
| ch_02 chars | ≥ 8 000 | build_gate1 per-chapter |
| ch_03 chars | ≥ 4 000 | build_gate1 |
| ch_04 chars | ≥ 2 500 | build_gate1 |
| epilogue chars | 800–1 500 | build_gate1 |
| Discourse markers ch_02 | ≥ 8 | `validate_discourse_markers` |
| Discourse markers ch_03 | ≥ 5 | `validate_discourse_markers` |
| Discourse markers ch_04 | ≥ 3 | `validate_discourse_markers` |
| Pin-list depth errors | **0** (все events ≥ 3 sentences) | `validate_pin_list_depth` |
| Timeline anchors | 7/7 found | `validate_timeline_anchors` |
| Chronology check «Германия+дети» | flagged error | `validate_chronological_consistency` (task 048d) |
| Style checks «событие изменило» | warning | task 043g |
| Style checks «типичной для поколения» | error + auto-delete | task 043g |
| Style checks «не любил X по Y и Z» | error | task 043f |
| Epilogue quote density | warning if >4 quotes/para | task 043e-2 |
| Bio_data.family format | единый «**Родство** — Имя (note)» | task 044g |
| Bio_data Калинин → Калинине | locative case | task 044g |
| Render bug `?: ?` / dup heading | 0 | task 044d-2 |
| Contributors раздел | 4 строки только ФИО+родство | task 052d |
| CA description ep_024 | содержит «Молдавия» | task 038c |
| Narrative ch_04 огурцы | «из Молдавии», не «из командировок» | task 038c effect on GW input |
| writing_notes.rule12_* | filled | task 049d schema |
| Stage 2 manifest | `ghostwriter_version: v2.22`, `completeness_auditor_version: v1.5` | manifest |
| FC verdict | PASS iter1-iter2 | FC |

---

## Risk и mitigation

**Risk A: Stochastic LLM variance** — v62a vs v59/v61 показала ±18% chars без изменений config. GW может outputs 18-19K даже с ПРАВИЛОМ 12.

**Mitigation:**
- Explicit target в промпте (главный сигнал LLM)
- Per-chapter floors (ch_02 ≥8K препятствует «всё в ch_02 ничего в ch_04»)
- writing_notes proof-of-attention
- **Backlog v64:** если v63 даёт <20K → GW revision loop (volume-based revision pass). НЕ в v63 scope.

**Risk B: Cognitive overhead** — ПРАВИЛО 12 в длинном промпте (≥2 000 строк). LLM может «забыть» предыдущие правила.

**Mitigation:**
- ПРАВИЛО 12 дополняет, не конфликтует с existing
- Per Правило 6 — после v63 verify: если предыдущие правила деteriorировали → откат

---

## Финансово

v63 = 1 прогон $2-3.

---

## Когда v63 готов

1. Verified-on-run в PR #29 (или новом PR `feat/v63-combined-sprint`)
2. **Опус откроет text_FULL.md сам** (Правило 2 архитектора, posture-forcing observation на каждый из 11 outcomes)
3. Опус **обновит run_registry.md** секцией `## v63` (Правило 5)
4. Если 11 outcomes PASS + объём ≥20K → **PASS Ворот 1** → tag RP-1 → разблокировка backlog v64 (если что-то осталось) + параллельная Королькова (task 053 generic runners)
5. Если объём <20K → v64 = GW revision loop spec (1 правило prompt-bump). Если другие items missing → точечные fixes v64.

---

## Открытые ссылки

- **PR #29** (v63 sprint specs, главный): https://github.com/NikitaMorgos/glava-bot/pull/29
- **PR #28** (v62a + ранее): https://github.com/NikitaMorgos/glava-bot/pull/28
- **v62a артефакты:** ветка `runs/karakulina-v62-artifacts` @ `db03743`
- **v61 артефакты** (baseline reference): `runs/karakulina-v61-artifacts` @ `df6f3f3`
- **v59 артефакты** (Никитин «самый удачный бенч»): `feat/batch2fix-pin-list-and-classes` @ `26ce5cc`, файл `collab/runs/karakulina_v59/karakulina_v59_text_FULL.md`

---

## Что НЕ делать в v63 (явный список)

- ❌ Bundle 2+ GW правил в v2.22 (Правило 6 violation)
- ❌ Bundle 2+ CA правил в v1.5
- ❌ Создавать `prompts/03_ghostwriter_v2.21.md` поверх откатанной версии (collision — используй v2.22)
- ❌ Trying to fix volume **через выдумку фактов** для добивки объёма — ПРАВИЛО 12 явно запрещает
- ❌ Подключение Корольковой (task 053) — до RP-1
- ❌ Этап 2 (Proofreader scripted, task 030) — до Ворот 1 PASS
- ❌ Новый прогон v64 до verified v63
- ❌ Финал text_FULL.md без `writing_notes.rule12_*` proof — это test schema, обязательно

---

## Версии этого документа

| Версия | Дата | Изменение | Кто |
|---|---|---|---|
| v1 | 2026-05-18 | Создание перед v63 sprint после v62a verified review | Опус |
