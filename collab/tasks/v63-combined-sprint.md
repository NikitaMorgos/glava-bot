# v63 sprint: combined (9 scripted + 1 CA minor + 1 GW prompt-bump)

**Статус:** `new`
**Sprint ID:** v63
**Автор:** Опус (роль архитектор+продакт)
**Дата создания:** 2026-05-18
**Триггер:** v62a verified (10/11 scripted PASS, но 3 моих + 8 Никитиных items) → Никитино go на Опцию X (combined sprint)
**Связано:** run_registry v62a; handoff-opus-2026-05-18-pre-v63.md; v62a-pointed-fixes-sprint.md; правила 1-6 архитектора

---

## Контекст

После v62a (10/11 scripted fixes PASS, NO GW change) — Никита прочитал text_FULL.md живьём:
- **Мои 3 блокера:** M1 объём 17 750 < 20K, M2 pin-list depth 5 errors, M3 discourse markers all 3 chapters below threshold
- **Никитины 8 items** из live review: chronology (Германия+дети), render bug (дубль), narrative пафос (событие изменило), pin-list year (дача), Class 11 awkward (электричество+поездки), огурцы Молдавия, epilogue overcrowded quotes, bio_data format inconsistency
- **Дополнительный impl item** от Никиты: Contributors раздел simplify

**После дедуп:** 11 items для v63 sprint.

**Никитино решение 2026-05-18:** Опция X (combined v63, $2-3 один прогон).

---

## Universality check (по всему sprint)

- [x] **Промпт без конкретики** — GW v2.22 ПРАВИЛО 12 использует placeholders `[Субъект]`, `[Рассказчик]`, `[Город_канон]`; subject-replacement test пройден построчно
- [x] **Subject-specific конкретика — в configs** — pin-list (ep_029 dacha year unknown), discourse_markers rapporteurs, persona_notes, gazeteer locative cases
- [x] **Алгоритм generic** — все 11 fixes применимы к любому subject
- [x] **Subject-replacement test** — для Корольковой/Дмитриева config меняется, code/prompt не меняется ✅

**Trap warning soft-applied:** все 11 items имеют **класс**, а не только конкретный эпизод:
- N1 «Германия+дети» = Class 12 chronology (children mentioned before first_child_birth)
- N3 «событие, которое изменило» = Class 6 narrative пафос (framing-фраза)
- N5 «электричество+поездки» = Class 11 awkward (X-по-Y listing) recurring
- N6 «огурцы Молдавия» = Class 1 CA confabulation (location generalisation) recurring
- N7 «epilogue overcrowded quotes» = Class 6 epilogue density
- M2 «pin-list depth» = Class 14 (GW narrative depth)
- M3 «discourse markers» = Class 13 (GW voice instruction)
- N2, N8, 052d, 044d-2 — render layer / format (узкие fixes)

---

## 11 tasks

### A. Scripted fixes (9 tasks, no LLM prompt changes)

| # | Task | Файл | Класс | Mitigates |
|---|------|------|-------|-----------|
| 1 | **048d** | `tasks/048d-chronology-children-general-context.md` | Class 12 chronology | N1 «Германия+дети» (children mentioned before first_child_birth) |
| 2 | **044d-2** | `tasks/044d-2-render-bug-residual-duplicates.md` | render layer | N2 «много текста перед Личные данные» + malformed Нинвана override |
| 3 | **043g** | `tasks/043g-narrative-event-changed-life-pattern.md` | Class 6 narrative пафос | N3 «событие, которое изменило» + «типичной для поколения» |
| 4 | **051d** | `tasks/051d-pinlist-dacha-year-uncertain.md` | pin-list edit + generic convention `year_confidence` | N4 «дача 1990-е» (год неточен) |
| 5 | **043f** | `tasks/043f-class11-awkward-not-loved-x-by-y-z.md` | Class 11 awkward recurring | N5 «электричество и поездки» (recurring v59/v60/v61/v62a) |
| 6 | **043e-2** | `tasks/043e-2-epilogue-overcrowded-quotes.md` | Class 6 epilogue density | N7 «overcrowded quotes» (>4 cited phrases в одном абзаце) |
| 7 | **044g** | `tasks/044g-bio-data-family-format-consistency.md` | Class 2 format consistency | N8 «формат непоследователен» (единый `**Родство** — Имя (note)` + locative case) |
| 8 | **052d** | `tasks/052d-contributors-simplify-fio-relation-only.md` | render layer | (impl) Contributors simplify ФИО+родство |

### B. CA minor prompt patch (1 task)

| # | Task | Файл | Класс |
|---|------|------|-------|
| 9 | **038c** | `tasks/038c-ca-pinlist-event-strict-source-location.md` | Class 1 CA description drift (location preservation) |

CA v1.4 → **CA v1.5** (+ ПРАВИЛО 7 — named entity preservation в description). Per Правило 6 — 1 правило per bump.
Mitigates N6 огурцы «из Молдавии» (recurring v56/v60/v62a).

### C. GW prompt-bump (1 task, главный driver объёма)

| # | Task | Файл | Класс |
|---|------|------|-------|
| 10 | **049d** | `tasks/049d-gw-v222-rule12-narrative-depth-voice-volume.md` | M1 объём + M2 pin-list depth + M3 discourse markers (Class 13+14 + volume) |

GW v2.20 → **GW v2.22** (+ ПРАВИЛО 12 — narrative depth + voice + объём ≥20K).

Per Правило 6 — одно правило per bump (3 metrics одной семьи «как разворачивать narrative»).

**v2.21 номер пропускается** — это файл откатанной версии из v60 sprint (rules 9/10/11 показали регрессию). Чтобы избежать collision — **v2.22**.

---

## Drivers объёма в v63

Цель — поднять total chars с 17 750 (v62a) до ≥20 000.

| Драйвер | Эффект |
|---------|--------|
| **GW v2.22 ПРАВИЛО 12** | direct target ≥20K + per-chapter floors (ch_02 ≥8K) + proof-of-attention в writing_notes — главный driver |
| 048d chronology | flag-only, neutral эффект на объём |
| 044d-2 render | format-only, neutral |
| 043g narrative пафос | удалит «событие изменило» (warning) + epilogue 2 sentences delete — **минус ~150 chars** epilogue (acceptable, epilogue range 800-1500) |
| 051d pin-list year | pin-list edit, нейтрален; может **добавить** chars если ep_029 теперь раскрывается (v62a missed) |
| 043f Class 11 awkward | flag-only |
| 043e-2 epilogue density | warning-only, neutral |
| 044g bio_data format | render-only, может добавить +50-100 chars (locative case + единый формат) |
| 052d Contributors simplify | удалит «основной рассказчик» etc — минус ~30 chars (insignificant) |
| 038c CA Молдавия | factual fix, не объёмный |

**Net эффект объёма:** GW ПРАВИЛО 12 — primary driver (+2-3K chars от v62a). Scripted fixes — neutral / minor + (Contributors simplify −30) / − (epilogue rewrite −150). Net прирост ожидается ~2K → 19-20K range.

**Risk объёма:** stochastic LLM variance может дать <20K даже с rule 12 (v62a показала 17K vs v61 20K без изменений). Mitigation:
1. Explicit target в промпте
2. Proof-of-attention writing_notes
3. **Backlog v64** если v63 даёт <20K — GW revision loop (volume-based revision pass)

---

## Финансово v63

1 прогон $2-3 (один Stage1+2+3 + verify).

---

## Решение о версионировании

- **GW: v2.20 → v2.22** (skip v2.21 collision)
- **CA: v1.4 → v1.5** (1 правило per bump per Правило 6)
- **pin-list (known_episodes_karakulina.md): v4 → v5** (ep_029 year_confidence=unknown)
- **configs:**
  - `narrative_stop_phrases.json: v2 → v3` (+ categories: event_that_changed_life, typical_for_generation, in_this_typicality_uniqueness, class11_not_loved_x_by_y_and_z)
  - `epilogue_rewrite_mapping.json: v2 → v3` (+ rules typical_for_generation, in_this_typicality_uniqueness)
  - `bio_data_format_config.json: v1` (новый, generic)
  - `chronology_periods_karakulina.json: v1` (новый, optional per subject)

---

## Что НЕ делаем в v63 (явный список, per Правило 6 + НЕ-делаем discipline)

- ❌ GW revision loop (volume-based) — backlog v64, если v63 не достигнет 20K
- ❌ task 037 (GW prompt refactor ≥2 000 lines) — backlog, не блокер
- ❌ Новые prompt-bumps для CA / LE / FC (single CA minor patch достаточно)
- ❌ Подключение Корольковой (task 053 generic runners) — после RP-1
- ❌ Этап 2 (Proofreader scripted, task 030) — после Ворот 1 PASS
- ❌ Bundle 2+ GW rules — Правило 6 violation

---

## Стратегия Verify (v63 прогон)

1. Stage 1 → Stage 2 (GW v2.22) → Stage 3 (LE v3.1 + post-processing scripts)
2. `scripts/build_gate1_full_text.py` → `karakulina_v63_text_FULL.md`
3. Курсорский verify-on-run отчёт:
   - Total chars ≥ 20K (build_gate1 own counter, не file_size — lesson v62a)
   - ch_02 ≥ 8K / ch_03 ≥ 4K / ch_04 ≥ 2.5K / epilogue 800-1500
   - discourse_markers.json: ch_02 ≥ 8 / ch_03 ≥ 5 / ch_04 ≥ 3
   - pin_list_depth.json: 0 errors (все события ≥ 3 sentences)
   - chronology_check.json: «Германия+дети» flagged как error
   - style_checks.json: «событие, которое изменило» warning; «типичной для поколения» error; «не любил X по Y и Z» error; «определило жизнь» (043d hold) warning
   - bio_data.family: единый формат, locative case, Нинвана не рендерится, нет дубля «Личные данные»
   - Contributors раздел: 4 строки только ФИО+родство
   - CA: ep_024 description содержит «Молдавия»; ch_04 narrative «из Молдавии»
   - writing_notes.rule12_* fields filled
   - Stage 2 manifest: ghostwriter_version=v2.22, completeness_auditor_version=v1.5
4. Опус independent verify — открыть text_FULL.md, посмотреть epilogue + ch_04 огурцы + ch_02 Германия + bio_data.family первые 5 строк
5. Никита live review → decision:
   - ✅ PASS Ворот 1 → RP-1 tag → Этап 2 (Proofreader scripted, task 030 unblocked)
   - ❌ <20K (volume regression) → v64 sprint = GW revision loop (1 rule prompt-bump)
   - ⚠️ Партculate items missing → точечные fixes v64 без GW change

---

## Per Правило 6 — strategic continuation

Если v63 PASS → backlog продолжается **по одной GW prompt-bump за раз**:
- v64: backup для volume risk (revision loop) ИЛИ ch_03 «Гостеприимство и кулинария» раздел
- v65: epilogue extend без пафоса (если 043g + 043e-2 недостаточны)
- v66+: task 053 generic Stage runners → Королькова

---

## Универсальная сохранность работы (для будущих subjects)

После v63 PASS:
- pin-list `known_episodes_<subject>.md` schema поддерживает `year_confidence`
- `chronology_periods_<subject>.json` — optional config для period-based chronology checks
- `bio_data_format_config.json` — generic, all subjects
- GW v2.22 ПРАВИЛО 12 — Subject-independent, applies к любым 90-минутным интервью
- CA v1.5 ПРАВИЛО 7 — Subject-independent

При подключении Корольковой:
- Заполнить `known_episodes_korolkova.md` (включая anti_facts если есть, contributors)
- `discourse_markers_korolkova.json` (rapporteurs списки)
- `relation_overrides_korolkova.json` (если CA mis-classifies)
- `gazeteer_korolkova.json` (если есть subject-specific locations)
- `chronology_periods_korolkova.json` (optional)
- Code/prompts **не меняются**.

---

## Открытые вопросы

1. **Volume risk mitigation** — достаточно ли explicit target в промпте + per-chapter floors + writing_notes proof? Если v63 даёт <20K — нужен v64 revision loop. **Решение откладывается** до v63 verified.

2. **Class 6 narrative пафос — балансировка** — pattern «событие, которое изменило» — warning-only (не enforce delete, чтобы не потерять fact Валерия 1961). Альтернатива — error+rewrite-hint. **Решение:** warning в v63, observe; если pattern recur → escalate.

3. **GW нумерация версий** — GW v2.21 файл существует (откатанный v60), v2.22 — новый bump. Принято решение **skip** v2.21 num во избежание confusion. Если в pipeline_config.json удобнее inline edit v2.21 (переписать) — обсуждаемо, но **default — отдельный файл v2.22**.

---

## История

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-18 | `new` | Опус |
