# Handoff Курсору — 2026-05-19 (для нового окна, перед v65 sprint)

> **Документ-страховка для нового окна Курсора.** Если предыдущая сессия Курсора кончилась — новое окно читает этот файл **первым** (5-10 мин) → готов работать на v65.
>
> **Предыдущий handoff** `handoff-cursor-2026-05-18-v64.md` (устарел, v64 verified).

---

## За 30 секунд: где мы

**v64 verified, НЕ PASS Ворот 1, но архитектурно революционно.** Revision loop (GW v2.23 ПРАВИЛО 13 + orchestrator) **физически работает** — paragraph p_02_011 был переписан per revision_hint. Это **первый sustained revision pass в истории**.

**Но реализация partial:**
- Orchestrator подключил только 6 из 10+ валидаторов
- Warnings отфильтрованы (3 personal_historical_voice warnings потерялись)
- GW вернул `writing_notes.revision_applied: "string"`, spec требовал `rule13_revision_applied: [list]`
- Chronology 5 errors — 4 false positives на factual summaries
- LE удалил writing_notes — diff_audit видит applied=[]
- Total chars 18 242 (Курсор отчитал 21 697 — lesson v62a/v63 chars metric ambiguity повторился **3-й раз**)

**Никитин live review v64** идентифицировал:
- Class 12 в новой форме (Толя/Коля/Витя в context 1933)
- Class 11 recurring (новая форма «—особенно по X, Y и другим Z»)
- Class 19 NEW (cross-paragraph дубль Власьево/крещения)
- Class 5 regression (грибы/ягоды, тётя Маша, дача потерялись)
- Factual error (улица Капошвара — должна быть площадь)
- Class 9 distribution (мало hist_notes в портрете)
- **Universality recurring моя ошибка** (выковыривал захардкожен в GW v2.23 ПРАВИЛО 2)

**Опус сделал stocktake-like analysis** (см. постмортем v63 в чате). Никита sign-off на 7 принципов команды + 2 новых правила архитектора (7 — не экономим на тестах, 8 — класс лечится семантикой не regex).

**v65 = bugfix sprint** (не новая архитектура). Цель — закрыть 4 bugs реализации v64 + Никитин feedback + universality fix.

---

## Команда и роли — без изменений

| Роль | Кто |
|------|-----|
| Owner / Product Lead | Никита |
| Архитектор + Продакт | Опус (AI) |
| Исполнитель | Курсор (AI, ты) |
| ~~Даша + Дашин Клод~~ | отстранены |

---

## ОБЯЗАТЕЛЬНО прочитать (20-25 мин)

### Принципы (обновлено 2026-05-19)

1. **`collab/context/dev-review-protocol.md` v2** ⭐ — теперь **8 правил** архитектора. Новые/изменённые:
   - **Правило 3 УСИЛЕНО:** жёсткий триггер счётчика «после каждого 3-го verified-on-run — обязательный stocktake до проектирования следующего sprint»
   - **Правило 7 НОВОЕ:** «Не экономим на тестовых прогонах» — каждый GW/CA prompt-bump + архитектурное изменение — **отдельный** прогон. Combined OK только для узких bugfixes известного эффекта
   - **Правило 8 НОВОЕ:** «Класс багов лечится семантикой, не regex» — regex = детектор конкретной формы, не лечение класса; лечение через семантический suggestion в revision_hint
2. **`collab/tasks/_template.md`** — pre-sprint checklist (новый раздел в шапке шаблона). Архитектор заполняет в шапке каждого sprint plan'а перед commit'ом

### Sprint v65

3. **`collab/tasks/v65-bugfix-sprint.md`** ⭐ — итоговый план (14 tasks)
4. **`collab/context/stocktake-2026-05-18-v60-v63.md`** — stocktake актуален (v65 — следующая волна после него)

### v64 контекст (что было, чтобы не повторять)

5. **`collab/runs/karakulina-v64-artifacts/VERIFIED_ON_RUN_v64.md`** — твой v64 self-report (см. Lesson v64 ниже про accuracy)
6. **`collab/runs/karakulina-v64-artifacts/revision_hints.json`** — что orchestrator передал (только 1 hint — bug)
7. **`collab/runs/karakulina-v64-artifacts/revision_diff_audit.json`** — schema mismatch issue
8. **`collab/runs/karakulina-v64-artifacts/validators_on_draft.json`** — какие 6 validators запустились (другие 4+ missing)

### Specs v65 (читаешь параллельно с реализацией, в порядке dependency)

**Архитектурный bugfix v64 (critical, читать первыми):**
- `collab/tasks/049f-2-orchestrator-coverage-extend.md` ⭐ — подключить все 10+ валидаторов + не фильтровать warnings
- `collab/tasks/049g-le-preserve-writing-notes.md` ⭐ — root-level metadata preservation post-LE
- `collab/tasks/049e-2-gw-v224-schema-fix.md` ⭐ — GW v2.24 schema fix `rule13_revision_applied` как list
- `collab/tasks/048e-chronology-fp-factual-summary.md` — chronology FP fix (ch_01 паспортичка + epilogue generic family)

**Никитин feedback v64 — классы багов:**
- `collab/tasks/048f-class12-extend-descendants-in-early-context.md` — Толя/Коля/Витя в context 1933 generic class
- `collab/tasks/043f-3-class11-snapshot-v64-and-lesson.md` — Class 11 recurring snapshot + lesson про Правило 8
- `collab/tasks/048g-class19-cross-paragraph-duplication.md` — Class 19 NEW (дубль абзаца)
- `collab/tasks/044i-pin-list-v7-required-narrative.md` — required_in_narrative markers + Капошвара verify
- `collab/tasks/046f-historical-notes-per-chapter-distribution.md` — per-chapter validator
- `collab/tasks/044i-2-characteristic-words-universality-verify.md` — verification report (closure через 049h)

**Universality + GW v2.24 (combined в одном файле prompt):**
- `collab/tasks/049h-gw-rule2-universality-fix.md` ⭐ — Правило 2 placeholders + pin-list characteristic_words input wire

**Build_gate1 enhancement:**
- `collab/tasks/v65-meta-build-gate1-pinlist-coverage.md` — required vs optional clear breakdown

---

## 8 правил архитектора (обновлено 2026-05-19, ты сверяешь)

| # | Правило | Status v65 |
|---|---------|------------|
| 1 | План перед волной | ✅ 14 готовых spec'ов |
| 2 | Артефакт перед проектированием | ✅ Опус открыл все v64 артефакты |
| 3 | **Stocktake каждые 2-3 волны** УСИЛЕНО | ✅ stocktake-2026-05-18 актуален (v65 — следующая волна; v66 потребует новый) |
| 4 | Universality построчно | ⚠️ **обязательная grep команда** перед commit'ом GW v2.24 (см. ниже) |
| 5 | Run registry update | После v65 прогона Опус добавит секцию `## v65` |
| 6 | Prompt engineering 1 правило per bump | ✅ v65 — 2 hot-fix existing rules (НЕ новые правила) |
| 7 | **Не экономим на тестовых прогонах** НОВОЕ | ✅ v65 = 1 прогон $4-6 (revision loop) — НЕ скупимся; combined OK потому что bugfixes |
| 8 | **Класс лечится семантикой, не regex** НОВОЕ | ✅ применено в task 043f-3 (semantic suggestion в hint) и 049f-2 (semantic per-validator suggestions) |

---

## 7 принципов команды (Никита постоянно повторяет, обновлено 2026-05-19)

1. Лес/деревья — лечим классы, не симптомы
2. Универсальность — все subjects
3. Класс багов, не симптом
4. Скрипт-first
5. Логирование
6. Медленно без откатов
7. **НЕ экономим на тестовых прогонах** (НОВОЕ 2026-05-19) — «сейчас нам важней результат стабильный получить. экономить можно начать позже»

---

## v64 outputs (что было)

**Артефакты:** в feat ветке `collab/runs/karakulina-v64-artifacts/` (Курсор не запушил отдельную `runs/karakulina-v64-artifacts` ветку — небольшое нарушение handoff disciplinы, в v65 push **обязательно** в `runs/karakulina-v65-artifacts`).

Метрики v64:
- Total chars: **18 242** (НЕ 21 697 как ты отчитал — lesson chars metric ambiguity)
- ch_02=6964 / ch_03=4898 / ch_04=2109 / epilogue=862 / ch_01=3409
- bio_data.family: 24 (Мария ✅ есть)
- historical_notes: 2 field + 8 inline = 10 ✅
- Pin-list: full 14, partial 7, skipped 46 / 67 (legacy метрика)
- Stage 2 manifest: ghostwriter_version=v2.23, completeness_auditor_version=v1.5
- revision_failed=false, unauthorized_changes=1

**11/11 tasks code-side PASS**, но 4 bugs реализации + 5 классов багов из live review.

---

## Версионирование v65 (КРИТИЧНО)

- **GW v2.23 → v2.24** — **2 hot-fix existing rules** (НЕ новые правила per Правило 6):
  - Hot-fix ПРАВИЛО 13: schema `rule13_revision_applied` как **list of dicts**, не string (task 049e-2)
  - Hot-fix ПРАВИЛО 2: **replace hardcoded** characteristic words «выковыривал/...» на **placeholders**; wire `pin_list.characteristic_words` через Stage 2 input (task 049h)
  - **Новый файл** `prompts/03_ghostwriter_v2.24.md` (копия v2.23 + 2 fixes)
  - `pipeline_config.json.ghostwriter.prompt_file` → `"03_ghostwriter_v2.24.md"`
- **CA v1.5** — без изменений
- **pin-list `known_episodes_karakulina.md` v6 → v7** (`required_in_narrative` markers + Капошвара verify)
- **dev-review-protocol.md v2** (уже обновлено в моих commits — стянуть с main)
- **Configs:**
  - `narrative_stop_phrases.json v6 → v7` (Class 11 расширение, task 043f-3)
  - `chronology_check_config.json v1` (новый, generic — skip_chapters, sentence_birth_self_declaration_skip)
  - `chronology_periods_karakulina.json v1 → v2` (descendants relation patterns для 048f)
  - `cross_paragraph_duplication_config.json v1` (новый, generic)
  - `historical_notes_distribution_config.json v1` (новый, generic per-chapter)

---

## Branch стратегия v65

**Base:** main (после PR с v65 specs merge).

**Новая ветка:** `feat/v65-bugfix-sprint` off main.

**После прогона v65:**
- Push кода в `feat/v65-bugfix-sprint`
- **Push артефактов в `runs/karakulina-v65-artifacts`** (отдельная ветка, как для v54..v63 ДЕЛАЛОСЬ; в v64 ты не создал — в v65 **обязательно**)
- PR с обеих веток

---

## Прогон v65 — что именно запускать

1. **Stage 1** split-extract с pin-list v7 (`--known-episodes=collab/context/known_episodes_karakulina.md`)
2. **Stage 2 first pass** GW v2.24 → `book_draft.json`
3. **Все ~12 валидаторов** на book_draft (orchestrator 049f-2 подключает их все):
   - chronology_check (с 048e + 048f FP fix и extend)
   - pin_list_depth
   - discourse_markers
   - narrative_stop_phrases (v7 — Class 11 расширен)
   - anti_facts
   - epilogue_stop_phrases
   - personal_historical_voice
   - epilogue_quote_density
   - narrative_truism (Class 17 v64)
   - **cross_paragraph_duplication** (Class 19 v65 NEW — task 048g)
   - **historical_notes_distribution** (v65 NEW — task 046f)
   - **required_episodes_coverage** (v65 NEW — task 044i)
4. **Orchestrator 049f-2** соберёт hints от всех (warnings включены) → передаст GW Stage 2 revision pass
5. **Stage 2 revision pass** GW v2.24 → `book_after_revision.json` со схемой `rule13_revision_applied: [list]`
6. **Schema validation** (новый — task 049e-2) + diff_audit
7. **046d historical_notes enrichment** post-revision (если <5 inline либо distribution неравномерное)
8. **Stage 3** + **049g preserve writing_notes** + post-processing
9. **build_gate1 v65** (task v65-meta — required vs optional clear breakdown)
10. **Final validators** (full coverage) → reports JSON

Создай `scripts/_run_v65_full.sh` (extend `_run_v64_full.sh` с новыми validators + revision loop full coverage).

---

## Дисциплина для Курсора в v65

1. **GW v2.24 — 2 hot-fixes existing rules (НЕ новые правила).** Не добавляй ничего ещё в v2.24.

2. **Universality построчно ОБЯЗАТЕЛЬНАЯ grep команда** перед commit'ом prompt v2.24:
   ```bash
   grep -in "Каракулин\|Татьян\|Валентин\|Химинститут\|выковырив\|зарубить\|зажиточн\|движуха\|рукаст\|бабульно\|Молдави\|1946 год\|две недели" prompts/03_ghostwriter_v2.24.md
   ```
   Допустимы matches **только** в шапке (version history), в **body правил** — 0 matches. Если найдены — переделать на placeholder. Это **закрытие моей recurring ошибки** (v60, v63, v64) — см. memory `architect_universality_check.md`.

3. **Verified-on-run = одно конкретное наблюдение per task.** Не «PASS / exit 0».

4. **Cross-check VERIFIED отчёт с реальными артефактами** (lesson v63 Татьяна «1952», lesson v64 Total chars «21697»). Если в отчёте написал X — открой JSON и убедись что реально X.

5. **Chars metric — build_gate1 Total** (sum content всех глав), НЕ file_size. Это **3-й раз** lesson v62a/v63/v64. Не повтори.

6. **Manifest versions** — Stage 2/3 manifest: `ghostwriter_version: v2.24`, `completeness_auditor_version: v1.5`.

7. **writing_notes proof-of-attention** (schema fix task 049e-2):
   - `rule13_revision_applied` — **list of dicts**, не string
   - Каждый dict: `hint_id`, `action` ("rewritten"|"deleted"|"skipped"), `diff_summary` либо `reason`
   - `rule13_hints_received`, `rule13_errors_applied`, `rule13_warnings_applied` — int
   - `rule13_revision_failed` — bool
   - Schema validation в коде после GW response — если schema нарушена, STOP

8. **diff_audit (049f-2 расширен) — артефакт `revision_diff_audit.json`** с unauthorized_changes context

9. **LE writing_notes preservation (049g)** — после Stage 3 проверить что `book_FINAL_stage3.json` содержит непустой `writing_notes`

10. **Snapshot tests mandatory:**
    - 043h Class 17 — расширить existing v64 tests
    - 043f-3 Class 11 — добавить v64 form
    - 048f Class 12 extend — Толя/Коля/Витя test
    - 048g Class 19 — Власьево duplicate test
    - 049e-2 schema test — list vs string detect
    - 049h universality — grep test + Stage 2 input wire test

11. **NO bundle:** не добавляй новые правила в v2.24 (только 2 hot-fixes). Если соблазн — backlog v66.

12. **Git push** обеих веток (`feat/v65-bugfix-sprint` + **`runs/karakulina-v65-artifacts`** отдельной). Обязательно.

---

## Targets для v65 (см. v65-bugfix-sprint.md detail)

Distribution gate:
- **Total ≥ 20 000**, **narrative ≥ 15 000**, **paspart ~ 3 000**, **historical_notes ≥ 2 000** (≥5 inline + ≥3 field) с per-chapter distribution

Per-chapter:
- ch_02 ≥ 7K / ch_03 ≥ 4K / ch_04 ≥ 2.5K / epilogue 800-1500
- discourse markers: ch_02 ≥8 / ch_03 ≥5 / ch_04 ≥3
- personal_historical_voice: ch_02 ≥3 / ch_03 ≥2 / ch_04 ≥1
- historical_notes per chapter: ch_02 ≥3 / ch_03 ≥2 / ch_04 ≥1

Validators clean после revision pass:
- chronology errors = 0 (FP fix + real errors closed)
- pin_list_depth = 0 errors
- narrative_truism Class 17 = 0
- Class 1/11/12 recurring/extend = 0
- cross_paragraph_duplication Class 19 = 0
- required_episodes_coverage missing = 0

Content:
- Мария в bio_data.family ✅
- Баба Аня в narrative ch_03 ✅
- Грибы/ягоды + тётя Маша в narrative ✅
- Продажа дачи в narrative (без «1990-е») ✅
- Капошвара = **площадь** (не улица) ✅
- Полина без потомков в context 1933 ✅
- Нет дубля Власьево/крещения ✅

Architecture:
- writing_notes.rule13_revision_applied — list of dicts ✅
- writing_notes preserved в book_FINAL_stage3 ✅
- revision_diff_audit applied != [] ✅
- revision_failed = false
- Stage 2 manifest ghostwriter_version=v2.24

Universality:
- Grep по subject-specific terms в `prompts/03_ghostwriter_v2.24.md` body = 0 ✅
- characteristic_words из pin-list input используются в narrative

---

## Risk + mitigation v65

**Risk A:** Revision loop full coverage → много hints → GW не справляется.
- Mitigation: warnings filtered must_apply=false (GW решает); max 1 revision pass

**Risk B:** GW v2.24 ПРАВИЛО 2 placeholders → теряются characteristic words если input wire не работает.
- Mitigation: tests на Stage 2 input wire + verify в v65 narrative ≥3 characteristic words

**Risk C:** Class 12 extend (048f) — false positive на legitimate generic «семья» mentions.
- Mitigation: severity warning; require named descendant (не generic «дети»)

**Risk D:** Combined v65 (14 tasks) рискует одной из них сломать что-то.
- Mitigation: per Правило 7 — combined OK для bugfixes известного эффекта. Snapshot tests + diff audit.

---

## Финансово

v65 = **1 прогон $4-6** (revision loop 2 LLM passes + historian enrichment 1 call).

**НЕ экономим** per Правило 7. Если потребуется второй прогон — делаем без дискуссии.

---

## Когда v65 готов

1. Verified-on-run в PR + push артефактов в **`runs/karakulina-v65-artifacts`**
2. Опус откроет text_FULL.md независимо (Правило 2)
3. Опус обновит run_registry v5 секцией `## v65` (Правило 5)
4. Если PASS distribution gate + 0 errors validators + content present → **PASS Ворот 1** → tag RP-1 → разблокировка backlog v66 (ch_03 sections) либо Королькова (task 053)
5. Если не PASS — diagnostic + v65b либо radical (task 037 GW refactor)

---

## Открытые ссылки

- **v64 артефакты:** `feat/v64-revision-loop-sprint:collab/runs/karakulina-v64-artifacts/` (within feat branch)
- **v63 артефакты:** `runs/karakulina-v63-artifacts` @ `7f03452`
- **v62a артефакты:** `runs/karakulina-v62-artifacts` @ `db03743`
- **v59 артефакты (Никитин "удачный бенч"):** `feat/batch2fix-pin-list-and-classes` @ `26ce5cc`

---

## Что НЕ делать в v65 (явный список)

- ❌ Новые GW правила (только 2 hot-fix existing)
- ❌ ch_03 «Гостеприимство и кулинария» — backlog v66 (ПРАВИЛО 14 prompt-bump)
- ❌ Editor agent / GW prompt refactor (task 037) — backlog v66+
- ❌ Auto-enforce delete для Class 17/19 — warning, revision pass решает
- ❌ Subject-specific patterns в Class 18 — generic only в v65
- ❌ Подключение Корольковой (task 053) — после RP-1
- ❌ Этап 2 (Proofreader scripted, task 030) — после Ворот 1 PASS
- ❌ Bundle новых правил в v2.24 — только 2 hot-fixes existing
- ❌ Экономия на тестовых прогонах per Правило 7
- ❌ Skip universality grep команды перед commit'ом v2.24

---

## Версии этого документа

| Версия | Дата | Изменение | Кто |
|---|---|---|---|
| v1 | 2026-05-19 | Создание перед v65 sprint после v64 verified + Никитин feedback + stocktake-style анализ + sign-off на принципы 7+8 | Опус |
