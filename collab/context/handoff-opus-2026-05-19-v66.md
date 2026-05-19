# Handoff Опуса — 2026-05-19 (после RP-1 Каракулины, перед v66a verify)

> **Документ-страховка для следующей сессии Опуса.** Если контекст текущей сессии заполнился — новая сессия читает этот файл первым (5 мин) + 6-7 связанных документов (15-20 мин) → готова к работе.
>
> **Предыдущий handoff** `handoff-opus-2026-05-18-pre-v63.md` (после v62a, перед v63) — устарел; v63→v64→v65→v65c прошли, **Ворота 1 на Каракулиной взяты** в v65c.

---

## За 30 секунд: где мы

**🎯 MILESTONE: Каракулина PASS Ворот 1 в v65c.** Tag `rp-1-karakulina-gate1-pass` на commit `2cb5394`. Total chars build_gate1 = **20 042** (target ≥20K), все 3 Никитины content blockers закрыты (Капошвара = площадь, Баба Аня в ch_03, дача без 1990-е), validators clean.

**Сейчас:** v66a sprint у Курсора в работе — **universality refactor на test bed Каракулиной**. Никитин принцип «убрать каракулинские темы и посмотреть на следующем прогоне что получается» — Каракулина = test bed для proof универсальности pipeline. v66a первый из 3 sub-sprints (Опция B split per Правилу 7 «не экономим на тестах»).

**Сразу после v66a verify** — пишешь v66b spec → v66c → tag RP-2 → подключение Корольковой (task 053 generic Stage runner будет готов в v66c).

---

## Команда и роли — без изменений

- **Никита** — owner + продакт+техлид. Финальный sign-off.
- **Опус (ты)** — архитектор + продакт (с 2026-05-17, Даша/Клод отстранены).
- **Курсор** — единственный исполнитель.

---

## ОБЯЗАТЕЛЬНО прочитать (15-20 мин)

В порядке приоритета:

1. **`collab/context/dev-review-protocol.md` v2** ⭐ — **8 правил архитектора** (особенно усиленное Правило 3 stocktake триггер счётчика; УЖЕСТОЧЕННОЕ Правило 4 B procedural enforcement; новые Правила 7 «не экономим» и 8 «класс лечится семантикой»). Прочитай **всё**, не только новые правила.

2. **`collab/context/universality-audit-2026-05-19.md`** — audit (42 CRITICAL + 18 BUG в active prompts). Roadmap v66a/b/c.

3. **`collab/tasks/v66a-universality-test-infra-gw-rule3-8910.md`** — текущий sprint в работе у Курсора.

4. **`collab/context/handoff-cursor-2026-05-19-v66a.md`** — что именно Курсор делает.

5. **`collab/context/stocktake-2026-05-18-v60-v63.md`** — анализ цикла v60-v63 (для понимания почему мы здесь).

6. **Артефакты v65c** для reference RP-1:
   - `runs/karakulina-v65-artifacts:collab/runs/karakulina-v65-artifacts/karakulina_v65c_text_FULL.md`
   - commit `2cb5394`, tag `rp-1-karakulina-gate1-pass`

7. **`collab/context/architecture-stocktake-2026-05-17.md`** — структурные классы багов (закрытые vs recurring).

В моей памяти (auto-memory) — критично для cold-start:
- `architect_universality_check.md` — **recurring моя ошибка** + procedural grep команда защита
- `principle_no_test_run_economy.md` — Правило 7 (не экономим)
- `principle_class_semantic_not_regex.md` — Правило 8 (класс лечится семантикой)
- `recurring_patterns_unittest.md` — snapshot tests для recurring classes
- `run_registry_discipline.md` — Правило 5 (run registry после каждого прогона)
- `prompt_engineering_discipline.md` — Правило 6 (1 правило per bump)
- `feedback_script_first.md` — Никитины 4 принципа
- `user_role_nikita.md` — стиль работы Никиты

---

## 8 правил архитектора (соблюдать)

1. **План перед волной** — spec до code
2. **Артефакт перед проектированием** — open file, не верь Курсорскому self-report (recurring lesson v63/v64/v65)
3. **Stocktake каждые 2-3 волны** УСИЛЕНО — после 3-го verified-on-run обязательно
4. **Universality** УЖЕСТОЧЕНО — A мысленный test + **B procedural enforcement** (grep + pytest CI gate + pre-sprint checklist)
5. **Run registry** — после каждого прогона обновить (ВНИМАНИЕ: текущий main лишился v63/v64/v65 секций из-за squash merges — restoration в backlog)
6. **Prompt engineering** — 1 правило per GW/CA bump; новые features → скрипты
7. **Не экономим на тестовых прогонах** — каждый prompt-bump = отдельный прогон; combined OK только для bugfixes
8. **Класс лечится семантикой, не regex** — regex = детектор формы, не лечение класса

---

## 7 принципов команды (Никита постоянно повторяет)

1. Лес/деревья — лечим классы багов
2. Универсальность — все subjects (test bed Каракулина → Королькова → Дмитриев)
3. Класс багов, не симптом
4. Скрипт-first
5. Логирование
6. Медленно без откатов
7. **Не экономим на тестовых прогонах** (новое 2026-05-19)

---

## Карта прогонов (где мы)

```
v54 ──► v55 ──► v56 ──► v57 ──► v58 ──► v59 ──► v60 ──► v61 (Hybrid rollback)
        │
        v62a ──► v63 ──► v64 ──► v65 ──► v65c ── [RP-1 ✅] ──► v66a ──► v66b ──► v66c ── [RP-2?] ──► Королькова
                                              │              │
                                              PASS           universality refactor на test bed Каракулиной
                                              Ворот 1        (Опция B split: $4-6 × 3 = $12-18)
```

**Recently merged PRs:**
- PR #28 v62a sprint (10 scripted, NO GW)
- PR #29 v63 sprint specs (11 tasks combined Опция X)
- PR #30 run_registry v4 (perдeлано subsequent merges — restoration в backlog)
- PR #31 v64 sprint specs (10 tasks revision loop architecture)
- PR #32 v65 sprint specs (14 tasks bugfix v64)
- PR #33 universality audit + жёсткое Правило 4
- PR #34 v66 plan finalized (Опция B + timing)
- ~~PR #35, #36~~ closed as superseded (add/add конфликты)
- PR #37 v65c spec + v66a plan + handoff (clean replacement)

**Текущие ветки:**
- `feat/v65-bugfix-sprint` — где реализация v65 + v65c у Курсора
- `runs/karakulina-v65-artifacts` @ `2cb5394` — v65c finalized artefacts (RP-1 tag)
- `runs/karakulina-v66a-artifacts` — будет создана после Курсорского прогона v66a

---

## v65c outputs (RP-1 reference, что было)

**text_FULL.md:** ≥20K Total, 19+ 7 7 5 4 3 …

| Метрика | v65c | Target | Status |
|---------|------|--------|--------|
| Total chars build_gate1 | 20 042 | ≥20K | ✅ |
| ch_02 | 7 730 | ≥7K | ✅ |
| ch_03 | 4 854 | ≥4K | ✅ |
| ch_04 | 3 160 | ≥2.5K | ✅ |
| epilogue | 1 077 | 800-1500 | ✅ |
| Historical_notes | 7 field + 7 inline | ≥3+≥5 | ✅ |
| Chronology errors | 0 | 0 | ✅ |
| Stop phrases | 0 | 0 | ✅ |
| Cross-paragraph dup | 0 | 0 | ✅ |
| writing_notes preserved post-LE | ✅ | required | ✅ |

**3 Никитины content blockers:**
- ✅ Капошвара = площадь (3 mentions, lines 178/244/250 в text_FULL)
- ✅ Баба Аня в ch_03 «В отличие от бабы Ани — матери первого мужа Татьяны» (line 309)
- ✅ Дача без «1990-е годы» в context продажи (lines 246/367)

**Versions использованные в v65c:**
- GW v2.24 (2 hot-fixes existing — ПРАВИЛО 13 schema + ПРАВИЛО 2 universality)
- CA v1.5, FC v2.13, LE v3.1, Historian v3
- pin-list `known_episodes_karakulina.md` v6
- 8+ generic configs (chronology_check, cross_paragraph_duplication, historical_notes_distribution, bio_data_format, etc.)

**Known issues для v66 (НЕ блокеры PASS):**
- 4 validator pattern bugs (required_episodes markers calibration, personal_historical_voice patterns, discourse_markers patterns) — false negatives, real content OK
- Pin-list depth 4 errors (ep_003 призыв 1941, ep_011 операция, ep_016 поликлиника, ep_024 огурцы — короткие 1-2 sentences)
- Class 6 epilogue пафос в новых формах («человеком своего поколения», «не сгибался под ударами судьбы») — recurring, regex не покрывает
- Audit_revision_diff chapter-level handling (false positive unauthorized_changes на chapter-level hints) — Курсор создал task `audit-chapter-level-hints-fix.md` для v66 backlog

---

## v66a sprint — что именно делает Курсор (текущий)

**3 tasks** (spec в `v66a-universality-test-infra-gw-rule3-8910.md`):

| # | Task | Что |
|---|------|-----|
| 1 | `tests/test_universality.py` | Pytest CI gate per Правило 4 B.2. Parse active prompts, split header/body, regex check по `tests/data/subject_specific_terms.txt`. FAIL при match в body |
| 2 | GW v2.24 → v2.25 universality refactor | ПРАВИЛА 3 (stop-phrases examples) + 8 (first paragraph examples) + 9 (X-по-Y formulation) + 10 (temporal connectors — самый большой, ~30 строк Дмитрий/Капошвара/1978/1996) + PIN_LIST антитриггеры (огурцы Молдавия) → placeholders. **Refactor existing rules, НЕ новые правила** per Правилу 6 |
| 3 | B3 `pipeline_utils.py:4977` NOMINATIVE_CITY_RE generic | Derive из `gazeteer_<subject>.json` cities либо generic morpho check |

**Версии v66a:** GW v2.24 → **v2.25**. CA v1.5 / FC v2.13 / pin-list v6 / configs — без изменений.

**Targets v66a (preserve v65c quality):**
- Total chars ≥ 19 500 (allow −2.5% variance vs v65c 20 042)
- 3 Никитины блокеры остаются закрытыми (Капошвара/баба Аня/дача)
- Validators clean (chronology 0, stop_phrases 0)
- **Pytest test_universality.py GW v2.25 = 0 body matches** обязательно
- **Grep команда GW v2.25 body = 0 matches** обязательно

**Финансово:** $4-6 один прогон.

---

## После v66a verified — что делать

### Сценарий 1 — v66a PASS (quality preserved + universality test green)

1. **Independent verify** Опуса (open `karakulina_v66a_text_FULL.md` глазами):
   - Total ≥ 19 500 ✅
   - 3 Никитины блокеры остаются (Капошвара/баба Аня/дача)
   - Recurring классы 1/6/11/12/17/19 — 0 errors
   - Огурцы Молдавия preserved без confabulation
   - Pytest test_universality.py PASS на GW v2.25
   - Grep команда GW v2.25 body = 0 matches

2. **Run_registry update** (Правило 5) — секция `## v66a`

3. **v66b sprint plan** — 3 tasks:
   - CA v1.5 → v1.6 universality refactor (ПРАВИЛА 1/2/4/6/7 + JSON schema events example)
   - B1 `pipeline_utils.py:4692-4695` `validate_children_before_birth` parametrize (child_name_stem из chronology_periods_<subject>.json)
   - B2 `pipeline_utils.py:4900-4904` `validate_entity_substitution` config-driven (substitution_pairs из entity_substitution_<subject>.json либо fact_map.place_canonical)

4. Создать handoff Курсору + PR + текст для нового окна

### Сценарий 2 — v66a quality снизилась (regression от placeholder examples)

1. Diagnostic: какое правило сломало (ch_02 не вырос / discourse markers упали / etc)?
2. Откат либо refinement placeholders (добавить explicit meta-description)
3. v66a' retry либо узкий fix v66a-bugfix
4. Не переходим к v66b до restore quality

### Сценарий 3 — v66a pytest test_universality fail

1. Курсор должен поправить **до push'a** prompt v2.25 (grep + переделать на placeholders)
2. Если pytest fails в CI — block merge

---

## Backlog после v66c PASS (после tag RP-2)

1. **Подключение Корольковой** через task 053 generic Stage runner (создан в v66c)
2. Audit_revision_diff chapter-level fix (v66 backlog accumulated)
3. Run_registry v6 restoration (потерянные v63/v64/v65 секции)
4. Validator pattern bugs (4 false negatives в v65c) — calibration
5. Pin-list depth 4 errors (ep_003/011/016/024) — расширение через GW prompt либо pin-list edits
6. Этап 2 Proofreader scripted (task 030 — было заблокировано до Ворот 1 PASS)
7. Чёрный треугольник — generic Stage 2/3 runners + per-subject config generation

---

## Lessons learned (накопленные за v60-v65c)

### 1. Recurring моя ошибка universality (4 раза)

- v60: «Татьяна 1956 Твери» в GW v2.21 ПРАВИЛО 9 — не поймал
- v63: написал «Молдавия 1946 две недели» в спеках 049d/038c — поправил при self-check
- v64: пропустил existing захардкоженные «выковыривал» etc в GW v2.23 ПРАВИЛО 2 (Никита спросил «выковыривал — это правило универсальное?»)
- Procedural защита через Правило 4 B (grep + pytest + checklist) — введена 2026-05-19 после universality audit

**Lesson:** мысленный test недостаточен; **процедурная** проверка обязательна. Перед каждым prompt-bump commit'ом — grep команда (см. `architect_universality_check.md`).

### 2. Chars metric ambiguity (4 раза)

- v62a: Курсор отчитал «22 927 chars», реальный narrative 17 750 (file_size vs build_gate1 Total)
- v63: я в run_registry неправильно интерпретировал v61 «20 272» (на самом деле build_gate1 Total с ch_01.content)
- v64: Курсор отчитал «21 697», реальный 18 242
- v65: Курсор отчитал «24 111» (file_size), реальный 19 705

**Lesson:** chars metric = `build_gate1 «Total chars»` (sum content всех глав). НЕ file_size. Цитировать только из build_gate1 summary. Distribution gate = 15K narrative + 3K paspart + 2K hist_notes.

### 3. Курсорский self-report может быть неточен (3 раза)

- v63: «daughter_tatyana_birth.year=1952 (estimated)» — в config реально 1956 (high)
- v64: chars отчёт wrong
- v65c: я подумал что баба Аня missing — Курсор был **прав** (line 309 «В отличие от бабы Ани»), мой grep не покрыл genitive падеж

**Lesson:** Cross-check VERIFIED отчёт Курсора с реальными артефактами. Открыть JSON / text_FULL.md, не доверять. И мне самому — при grep verify использовать **широкие patterns** (падежи, варианты написания).

### 4. Run_registry дисциплина

- PR #30 (run_registry v4 с v63 секцией) был перетёрт subsequent squash merges PR #31/#32 которые имели старую базу
- Main сейчас имеет run_registry только до v62a секции

**Lesson:** Каждый PR с pipeline changes должен **rebase main** и включать run_registry update в свой commit. Restoration v63/v64/v65/v65c секций — в backlog.

### 5. Validator без enforcement = decoration

- v62a/v63 — validators flag, GW игнорирует
- v64 — закрыто архитектурно через revision loop (GW v2.23 ПРАВИЛО 13)

**Lesson:** При проектировании validator — сразу спрашивать «как result возвращается обратно для исправления?». Закрепил в Правиле 8.

### 6. Pattern эволюция (Class 1/6/11/12)

- 5 sprints (v60-v65) recurring patterns возвращались в новых формах
- v64 revision loop с **семантическим hint** = первый случай когда defense работает на уровне семантики

**Lesson:** Класс багов лечится **семантическим suggestion** в revision_hint, не regex pattern (Правило 8). Regex = минимальный детектор для last known form, не лечение.

### 7. Bundle ловушка

- v63 combined Опция X = выкинутый sprint (невозможна диагностика regression)
- v66 split Опция B = $12-18 vs $4-6 экономии = разовая инвестиция в proof

**Lesson:** Каждый prompt-bump = отдельный verified прогон. Combined OK только для узких bugfixes известного эффекта. Закрепил в Правиле 7.

---

## Дисциплина команды (что сохранять)

1. **Артефакт ≠ proxy** — open file, не верь пересказу
2. **Posture-forcing observation** при closure
3. **Семантическая верификация ≠ формальная** — PASS-verdict с условиями требует cross-check
4. **Defense in depth** — промпт + код + тест
5. **Universality построчно** в финальном промпте (procedural grep + pytest)
6. **Класс багов через семантический hint**, не regex
7. **Каждый prompt-bump = отдельный прогон**
8. **Run_registry update** после каждого прогона (Правило 5)
9. **>3 регрессий разных классов = RETRO** не POINT_FIX
10. **Никита спал — после следующего сообщения скажет.** Не торопиться с решениями.

---

## Открытые ссылки

- **RP-1 tag:** `rp-1-karakulina-gate1-pass` на commit `2cb5394`
- **v65c артефакты:** `runs/karakulina-v65-artifacts` (read text_FULL.md)
- **v66a в работе у Курсора:** ветка `feat/v66a-universality-prep` (после Курсорского чекаута)
- **PR #37 merged:** https://github.com/NikitaMorgos/glava-bot/pull/37 (v65c spec + v66a plan + handoff)
- **Universality audit:** `collab/context/universality-audit-2026-05-19.md`
- **Recent merge commit на main:** `dbaa118` (PR #37)

---

## Конкретный следующий шаг

**Если Курсор уже отчитал по v66a:**
1. Fetch `runs/karakulina-v66a-artifacts` (либо новые commits в существующей ветке)
2. Open `karakulina_v66a_text_FULL.md` глазами
3. Posture-forcing observation: 3 Никитины блокеры остаются ✅ / Total ≥ 19 500 ✅ / pytest test_universality зелёный
4. Если PASS → v66b spec (CA v1.6 + B1 + B2)
5. Если quality снизилась → diagnostic + Никита решает

**Если Курсор ещё работает:**
1. Параллельная работа: восстановление `run_registry.md` v6 (Правило 5) — добавить секции v63/v64/v65/v65c которые потерялись после squash merges
2. Создать отдельный PR с restored run_registry
3. Не trog v66a у Курсора

**Если Никита спрашивает что-то новое:**
- Прочитать `dev-review-protocol.md` v2 + применить 8 правил
- Если задача неясна — задать уточняющие вопросы перед стартом
- **План перед кодом** (Правило 1)
- Pre-sprint checklist (Правило 4 B.3) обязателен для нового sprint plan'а

---

## Версии этого документа

| Версия | Дата | Изменение | Кто |
|---|---|---|---|
| v1 | 2026-05-19 | Создание после RP-1 на v65c + v66a sprint у Курсора в работе. Контекст текущей сессии Опуса >80% | Опус |
