# Handoff Опуса — 2026-05-18 (после v62a, перед v63)

> **Документ-страховка для следующей сессии Опуса.** Если текущая сессия (контекст 76%+) сжалась — новая сессия читает этот файл первым (5 мин) + 5-6 ключевых документов (15 мин) → готов работать.
>
> **Предыдущий handoff** `handoff-2026-05-15.md` (после v55) — устарел.

---

## За 30 секунд: где мы

**v62a verified, НЕ PASS Ворот 1.** Регрессия объёма (17 750 vs 20K+ target; vs v59 19 930 и v61 20 272). 10/11 scripted tasks работают, все Никитины critical items закрыты (Марфа, Contributors, render bug, paspart Калинин, anti_facts). Но GW v2.20 написал короче в этом прогоне — likely stochastic variance OR config recompilation effect (anti_facts в pin-list v4).

**Никита прочитал v62a живьём — дал 8 замечаний + мои 3 блокера = 11 items для v63.**

**Следующий шаг:** v63 sprint (combined 9 scripted + 1 GW rule + 1 CA tweak). Ждёт Никитино go на Опцию X или Y (split v63a/b).

**Baseline для diff:** v59 (Никитино решение).

---

## Команда и роли

- **Никита** — owner + продакт+техлид. Финальный sign-off.
- **Опус (ты)** — архитектор + продакт (с 2026-05-17, Даша/Клод отстранены).
- **Курсор** — единственный исполнитель.

---

## ОБЯЗАТЕЛЬНО прочитать (15-20 мин)

1. **`collab/context/run_registry.md`** v3 — реестр всех прогонов v54-v62a + Environment секция (Cursor agent/model)
2. **`collab/context/architecture-stocktake-2026-05-17.md`** — 16+ классов багов, v62a sprint раздел, backlog
3. **`collab/context/dev-review-protocol.md`** — **6 правил архитектора** (особенно Правило 6 prompt engineering)
4. **`collab/context/known_episodes_karakulina.md`** v4 — pin-list + Anti-facts секция + Contributors раздел
5. **`collab/context/gate1_product_checklist.md`** — target 20K+ (обновлено)
6. **`collab/runs/karakulina_v62/VERIFIED_ON_RUN_v62.md`** — Курсорский отчёт по v62a
7. **`collab/tasks/v62a-pointed-fixes-sprint.md`** — v62a spec (10 tasks выполнены)

В memory (для cold-start):
- `architect_universality_check.md` — 4 вопроса + subject-replacement test построчно
- `run_registry_discipline.md` — Правило 5
- `prompt_engineering_discipline.md` — Правило 6 (1 правило per GW bump)
- `feedback_script_first.md` — 4 принципа Никиты
- `user_role_nikita.md` — стиль работы
- `project_team_state.md` — состояние команды

---

## 6 правил архитектора (соблюдать)

1. **План перед волной** — spec до code
2. **Артефакт перед проектированием** — open file, не верь пересказам
3. **Stocktake каждые 2-3 волны** — без напоминания
4. **Universality check** — 4 вопроса + subject-replacement test построчно для **финального текста** промпта/spec'а
5. **Run registry** — после каждого прогона обновить
6. **Prompt engineering discipline** — 1 правило per GW bump, не bundle; новые features = скрипты

---

## 6 принципов команды (Никита **постоянно** повторяет)

1. Лес/деревья — лечим классы, не симптомы
2. Универсальность — все subjects, не Каракулинаспецифика
3. Класс багов, не симптом
4. Скрипт-first
5. Логирование (run_registry + Правило 5)
6. Медленно без откатов

---

## v62a outputs (что Никита читал)

**Артефакты:** `runs/karakulina-v62-artifacts` @ db03743
**Book chars:** 17 750 (< 20K+ target — REGRESSION)
- ch_02 6 834 (vs v61 8 359, −18%)
- ch_03 4 450
- ch_04 2 327
- epilogue 785
**Historical notes:** 10 field + 10 inline (рекорд!)
**Bio_data.family:** 23 (Марфа есть)
**Pin-list:** full 15 / partial 7 / skipped 45 / 67
**Timeline anchors:** 7/7 ✅
**FC verdict:** PASS iter1

**Что v62a закрыл:**
- ✅ Render bug `?: ?` (но дубль «перед Личные данные» — incomplete, см. Никитин #2)
- ✅ Марфа в bio_data.family
- ✅ Никита/Даша notes
- ✅ Тверь → Калинин paspart
- ✅ Contributors раздел (4 имени, но Никита просит **упростить** — см. #12)
- ✅ Anti-facts af_002 акушерство fired
- ✅ Timeline widowhood separate

**Что v62a НЕ закрыл (блокеры):**
- ❌ Объём 17 750 < 20K+
- ❌ Pin-list depth 5 errors (свадьба, операция, Кирсанов, пенсия, Капошвара, перелом — 2 sentences)
- ❌ Discourse markers all 3 chapters below threshold (049c validator работает, GW v2.20 не пишет markers)

---

## 11 items для v63 (мои 3 + Никитины 8)

### Мои 3 (объём + depth + voice)

| # | Item | Класс |
|---|---|---|
| M1 | Объём 17 750 < 20K+ target | structural |
| M2 | Pin-list depth 5 errors | Class 14 GW behavior |
| M3 | Discourse markers all 3 chapters below threshold | Class 13 GW behavior |

### Никитины 8 (из v62a review)

| # | Item | Класс | Recurring? |
|---|---|---|---|
| N1 | «В Германии 1946-48 сидела с детьми» (дети ещё не родились) | Class 12 chronology | **ДА** (v60 повторение) |
| N2 | «Много текста перед Личные данные» (render bug дубль) | task 044d incomplete | new |
| N3 | «событие, которое изменило семейную жизнь» — Валерий 1961 | Class 6 narrative пафос | new |
| N4 | «семья продала дачу в 1990-е» — год возможно неточный | Pin-list ep_029 уточнить | n/a |
| N5 | «не любил советов по электричеству и поездкам» | Class 11 awkward | **ДА** (v59/v60/v61 повторение) |
| N6 | «критиковала за подарки из командировок» (огурцы) — должно «из Молдавии» | Class 1 CA confabulation | **ДА** (v56/v60 повторение) |
| N7 | Epilogue overcrowded quotes (рукастость, выковыривать, дорожку, оловянный солдатик в одном абзаце) | Class 6 epilogue пафос | new |
| N8 | Bio_data.family format inconsistency («Муж: X (note)» vs «Бабушка Марфа: details») | task 044d/e/g | new |
| (impl) | Contributors раздел: убрать «основной рассказчик / со-интервьюер», только ФИО+родство | task 052d | new |

---

## План v63 sprint (combined 9 scripted + 1 GW rule + 1 CA tweak)

| # | Task | Что | Тип |
|---|---|---|---|
| 1 | **048d** | Chronology extend: «дети» в general context (не только grandchildren) | scripted |
| 2 | **044d-2** | Render bug extend: дубль «перед Личные данные» | scripted |
| 3 | **043g** | Class 6 narrative пафос: «событие, которое изменило», «типичной для поколения» | scripted |
| 4 | **051d** | Pin-list ep_029 продажа дачи year уточнение или remove year attribution | pin-list edit |
| 5 | **043f** | Class 11 awkward extend: «не любил [X] (особенно)? по [Y] и [Z]» pattern | scripted |
| 6 | **038c** | CA strict pin-list event: огурцы «из Молдавии», не «из командировок» | промпт CA v1.5 минор |
| 7 | **043e-2** | Epilogue overcrowded quotes detection (>5 cited phrases в epilogue) | scripted warning |
| 8 | **044g** | Bio_data.family format consistency: «Родство: Имя (note)» формат | scripted post-process |
| 9 | **052d** | Contributors simplify: только ФИО + родство | scripted |
| **10** | **GW v2.21 rule 12** | **«Narrative depth + voice + объём»**: explicit target в промпте: «Целевой объём book content **≥20K chars** (ch_02 ≥8K / ch_03 ≥4K / ch_04 ≥2.5K / epilogue 800-1500). Не сжимай narrative. Pin-list events развёрнуто (≥3 sentences с конкретикой). Сохраняй discourse markers рассказчика (≥5 в ch_02, ≥3 в ch_03/ch_04 «как вспоминает дочь / по словам Татьяны»).» | **GW prompt-bump (1 rule, шире scope)** |

**Per Правило 6:** GW rule 12 — **одно** новое правило, шире scope (3 metrics: depth + voice + объём). Не bundle 2+ независимых rules.

**Никитино решение 2026-05-18: Опция X** (combined sprint).

**Финансово:** $2-3 один прогон v63.

**Drivers объёма в v63:**
- GW rule 12 — direct target ≥20K (главный driver)
- 9 scripted fixes — все либо **flag-only** (chronology, awkward formulation, Class 6 pафос), либо **format-only** (render bug, bio_data format), либо **add small content** (Contributors simplify ничего не сокращает). НЕ сокращают объём.

**Risk объёма:** stochastic LLM variance может дать <20K даже с rule 12 (v62a показала 17K vs v61 20K без изменений). Mitigation: explicit chars target в промпте + monitor. **Если v63 даст <20K** — backlog v64 = GW revision loop (volume-based revision).

---

## Решение по Опциям ждёт Никита

- Опция X — combined v63 ($2-3, моя рекомендация)
- Опция Y — split v63a/b ($4-6, безопаснее по Правилу 6, узнаем что именно сработало)

Никита спал — после следующего сообщения скажет.

---

## Backlog после v63 PASS

- v64: ch_03 «Гостеприимство и кулинария» раздел (GW prompt-bump 1 rule)
- v65: Epilogue extend without pафос (GW prompt-bump 1 rule)
- v66+: task 053 generic Stage runners → подключение Корольковой

---

## Lessons learned (новые после v62a)

### Lesson 1: Chars metric ambiguity

Курсор отчитал «22 927 chars Gate-1 text» = `len(file_text)` всего text_FULL.md (с markdown decorations / paspart / Contributors). Реальный **book content** = build_gate1 own counter = **17 750**. При verify metric — уточнять source.

### Lesson 2: Recurring patterns без unit-test'а возвращаются

- Class 11 awkward «не любил X по Y и Z» — повторился в v59/v60/v61/v62a несмотря на task 043b/c/d patterns
- Class 12 «сидела с детьми 1946» — повторился v60→v62a
- Class 1 огурцы причина — повторился v56→v60→v62a

**Lesson:** для каждого recurring pattern — pytest unit test с конкретным example. Если pattern не ловит unit test — fix pattern.

### Lesson 3: Stochastic LLM variance — реальная угроза

v59=20 272 → v61=20 272 → v62a=17 750. Same GW v2.20, same configs (примерно). LLM stochastic gives 18% variance в ch_02. Это не controlled.

Mitigation: **stochastic check re-run** (Опция A) перед conclusion о systematic issue.

---

## Открытые ссылки

- PR #28 (главный): https://github.com/NikitaMorgos/glava-bot/pull/28
- v62a артефакты: `runs/karakulina-v62-artifacts` (read-only branch)
- v61 baseline: `runs/karakulina-v61-artifacts`
- Курсорский отчёт v62a: `VERIFIED_ON_RUN_v62.md`

---

## Дисциплина команды (что сохранять при handoff)

1. **Артефакт ≠ proxy** — open file, не верь пересказу
2. **Posture-forcing observation** при verified-on-run — одно конкретное наблюдение
3. **Семантическая верификация** ≠ формальная — PASS-verdict с условиями требует cross-check
4. **Defense in depth** — промпт + код + тест
5. **>3 регрессий разных классов = RETRO** (не POINT_FIX)
6. **Universality check построчно** в финальном промпте — не только в spec
7. **Run registry update** после каждого прогона
8. **1 правило per GW bump** (Правило 6)

---

## Версии этого документа

| Версия | Дата | Изменение | Кто |
|---|---|---|---|
| v1 | 2026-05-18 | Создание после v62a + Никитиного review, перед v63 sprint. Контекст текущей сессии Опуса >70% | Опус |
