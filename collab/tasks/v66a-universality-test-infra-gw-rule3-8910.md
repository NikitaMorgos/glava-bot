# v66a sprint — Test infrastructure + GW v2.25 universality refactor (Правила 3/8/9/10 + PIN_LIST антитриггеры) + B3 NOMINATIVE_CITY_RE

**Статус:** `new`
**Sprint ID:** v66a (первый из 3 universality sub-sprints)
**Автор:** Опус
**Дата создания:** 2026-05-19
**Триггер:** RP-1 tag на v65c (Каракулина Gate 1 PASS); v66 plan finalized (PR #34 merged, Опция B split); universality audit 2026-05-19 (42 CRITICAL в active prompts).
**Связано:** dev-review-protocol.md Правило 4 УЖЕСТОЧЕНО (B procedural enforcement); v66 plan (split sub-sprints); audit findings

---

## Pre-sprint checklist (Правила 3+4+7+8 ужесточённое 4 B)

- [x] **Stocktake актуален** — `stocktake-2026-05-18-v60-v63.md` + `universality-audit-2026-05-19.md`. v66a — 1-я волна после RP-1, новый stocktake не нужен (счётчик: v65→v65c→v66a = 2 verified-on-run, до 3-го можно работать)
- [x] **Critical reading артефактов v65c** выполнено — text_FULL.md прочитан, validators проверены, PASS verified
- [x] **Universality построчно (Правило 4 A)** — этот sprint **сам** про universality fix
- [ ] **Universality grep команда (Правило 4 B.1)** — будет выполнена Курсором перед commit'ом GW v2.25 prompt
- [ ] **Pytest universality test (Правило 4 B.2)** — task 1 в этом sprint'е создаёт `tests/test_universality.py`
- [x] **Защита подключена к лечению** — да, GW v2.25 ПРАВИЛА 3/8/9/10 + PIN_LIST → placeholders + grep команда + pytest CI gate
- [x] **Прогон раздельный (Правило 7)** — v66a = ОДИН GW prompt-bump + 1 scripted (B3). Combined OK потому что узкие related fixes
- [x] **Класс багов, не симптом** — Universality recurring моя ошибка (3 раза), procedural enforcement = архитектурное закрытие класса
- [x] **Скрипт-first** — 2/3 tasks scripted (test infra + B3), 1 prompt refactor (необходимо для bug fix existing rules)

---

## Контекст

После RP-1 v65c (Каракулина Gate 1 PASS) — переходим к **universality refactor** на **test bed Каракулиной** (Никитин принцип: «убрать каракулинские темы и посмотреть на следующем прогоне что получается»).

v66a — **первый** из 3 universality sub-sprints (per v66 plan finalized PR #34):
- **v66a:** test_universality.py infrastructure + GW v2.25 (ПРАВИЛА 3/8/9/10 + PIN_LIST) + B3 NOMINATIVE_CITY_RE
- v66b: CA v1.6 + B1 (children_before_birth config) + B2 (entity_substitution config)
- v66c: FC v2.14 + FE v3.5 + C1 (generic Stage runner — task 053)

**Цель v66a verify:** GW работает с placeholder examples на Каракулиной → quality сохранена (≥19.5K chars, все Никитины блокеры остаются закрытыми, recurring классы не возвращаются).

---

## Универсальность принципов (verification)

- ✅ Лес/деревья: один архитектурный класс «universality recurring» закрывается процедурно
- ✅ Универсальность: GW v2.25 ПРАВИЛА 3/8/9/10 — placeholders во ВСЕХ examples; pin-list characteristic_words feeds через input
- ✅ Класс багов: subject-specific examples в **finally text** of LLM prompts (recurring моя ошибка v60/v63/v64)
- ✅ Скрипт-first: 2 scripted из 3 tasks, 1 prompt refactor — необходимо для closing class
- ✅ Логирование: после v66a verify → run_registry update + sprint plan reference
- ✅ Медленные шаги: одно prompt-bump (v2.24 → v2.25, refactor existing rules), отдельный verify прогон
- ✅ НЕ экономим: $4-6 за один прогон v66a

---

## 3 tasks для v66a

### Task 1 — Universality CI gate (test infrastructure)

**Файл:** `tests/test_universality.py` (новый)

**Зачем:** автоматическая проверка что prompts/*.md (active versions) не содержат subject-specific terms в body правил (header version history — OK).

**Реализация** (полная spec в `v66-universality-refactor-sprint.md`, кратко здесь):
- Парсит активные prompts из `pipeline_config.json` (после update в v66a → 03_ghostwriter_v2.25.md, 16_completeness_auditor_v1.5.md, итд)
- Splits each prompt на header (allowed subject mentions) + body (NOT allowed)
- Прогоняет regex patterns из `tests/data/subject_specific_terms.txt` (уже создан) по body
- FAIL если matches в body

**Header end markers:**
- `══════` (separator между правилами и шапкой)
- `## SYSTEM PROMPT`
- Первый ``` блок системного промпта

**Реализация:** см. v66-universality-refactor-sprint.md (раздел «tests/test_universality.py»).

**Tests for v66a verify:**
- GW v2.25 → 0 body matches (PASS)
- CA v1.5 → должны быть matches (closure в v66b)
- FC v2.13 → должны быть matches (closure в v66c)
- LE v3.1, Historian v3, Cleaner v1, Proofreader v1 → 0 matches (already clean per audit)

**CI integration:** добавить в `.github/workflows/*.yml` (если есть) либо в Makefile/local pytest. **PASS test обязателен для commit prompts/*.md**.

### Task 2 — GW v2.24 → v2.25 universality refactor

**Файл:** `prompts/03_ghostwriter_v2.25.md` (новый, копия v2.24 + 4 правила refactored)

**Шапка v2.25:**
```
## Версия: v2.25 (2026-05-19, Opus, v66a sprint)
### Изменения v2.25 (v66a universality sub-sprint):
### Refactor existing rules (НЕ новые правила per Правило 6):
### • ПРАВИЛО 3: stop-phrases examples → placeholders (Каракулино-specific Венгрия/Татьяна/Валерий снят)
### • ПРАВИЛО 8: ✅ examples first paragraph → placeholders (шуба/пианино/авоська снят)
### • ПРАВИЛО 9: формулировки (X-по-Y) examples → placeholders (Дашин зять Маргось снят)
### • ПРАВИЛО 10: temporal connectors examples → placeholders (Дмитрий/Капошвара/Тверь 1978/1996 снят)
### • PIN_LIST антитриггеры: огурцы Молдавия пример → placeholder example
###
### v2.25 = v2.24 + 4 rule refactors (bug fixes existing rules, не новые правила).
###
### Per Правило 4 B архитектора (УЖЕСТОЧЕНО 2026-05-19):
### grep команда + pytest test_universality.py обязательны перед commit'ом.
###
### Audit reference: universality-audit-2026-05-19.md (12 CRITICAL в GW v2.23/v2.24
### в правилах 3/8/9/10 + PIN_LIST антитриггеры; task 049h уже закрыл ПРАВИЛО 2).
```

**Что менять (per universality audit findings):**

#### ПРАВИЛО 3 — stop-phrases (lines 260-267 в v2.24)
**Старое:**
> Пример v54 регрессии: "трагически событие, изменившее семейную жизнь" — нужно "В 1961 году Валерий не захотел возвращаться в интернат в Венгрии"

**Новое (placeholders):**
> Пример recurring regression: "трагически событие, изменившее [семейную/трудовую] жизнь" — заменить на factual sentence начинающийся с конкретного года/события из fact_map.timeline. Не использовать generic «трагически», «события, изменившие жизнь» — это Class 6 narrative пафос (см. narrative_stop_phrases.json category event_that_changed_life).

#### ПРАВИЛО 8 — first paragraph contains facts (lines 337-366 в v2.24)
**Старое:**
> ✅ ПРАВИЛЬНО (ch_04): В 1962 году Валентина продала шикарную шубу, привезённую из Венгрии, чтобы купить дочери Татьяне пианино.
> ✅ ПРАВИЛЬНО (ch_03): «Бабушка у нас всё-таки стойкий оловянный солдатик», — говорит Татьяна, и в этом образе...
> ❌ ПЛОХО (v53b ch_04): Валентина Ивановна была человеком ярких поступков и запоминающихся привычек...
> ✅ ПРАВИЛЬНО (ch_04): Когда внучка Даша болела, Валентина приносила ей еду на работу матери...

**Новое (placeholders):**
> ✅ ПРАВИЛЬНО (ch_04 — конкретный факт): «В [YYYY] году [Субъект] [конкретное_действие] из fact_map.timeline эпизода [episode_id], чтобы [конкретная_цель]».
> ✅ ПРАВИЛЬНО (ch_03 — характерная цитата): «[характерная_цитата_рассказчика]», — говорит [Рассказчик_имя_из_pin_list], и в этом образе [конкретная_деталь].
> ❌ ПЛОХО (анти-pattern из v53b — ch_04 generic): «[Субъект] был человеком ярких поступков и запоминающихся привычек. За внешней X скрывалось Y...» — нет ни одного факта из fact_map.timeline, нет characteristic word из transcripts. См. ЗАПРЕТ 8.
> ✅ ПРАВИЛЬНО (ch_04 — внук_контекст): «Когда внук/внучка [имя_из_fact_map] [конкретное_событие], [Субъект] [конкретное_действие]» — все имена/события из fact_map.

#### ПРАВИЛО 9 — X-по-Y formulation (lines 402-419 в v2.24)
**Старое:**
> ✅ ПРАВИЛЬНО: «Дашин зять — Маргось — научился молчать», — позитивный пример
> ❌ ПЛОХО (v54): «он не любил советов по электричеству, поездкам и другим бытовым вопросам»

**Новое (placeholders):**
> ✅ ПРАВИЛЬНО (обобщение): «[Имя_родственника] научился [абстрактное_действие]» — позитивный пример без перечисления частных категорий.
> ❌ ПЛОХО (recurring v59-v64 anti-pattern): «[он/она] не любил X по Y, Z и [другим бытовым/практическим] вопросам» — формулировка через перечисление 3+ частных категорий вместо обобщения. См. narrative_stop_phrases.json category `class11_not_loved_x_by_y_and_z_extended` (pattern_options для 4 форм).

#### ПРАВИЛО 10 — temporal connectors (lines 427-460 в v2.24)
**Самый большой кластер subject-specific (Дмитрий Каракулин, Татьяна, Владимир Маргось, Олег Кужба, Капошвара, Тверь, Химинститут, 1978, 1996).**

**Старое (всё с конкретными именами):**
> ❌ ПЛОХО: «После смерти Дмитрия в 1978 году Валентина осталась одна» (фактически жила одна с 1996 после переезда дочери)
> ✅ ПРАВИЛЬНО: «После смерти Дмитрия в 1978 году Валентина продолжала жить с дочерью Татьяной в Химинституте. С 1996 года, когда Татьяна вышла замуж за Олега Кужбу и переехала на площадь Капошвара, осталась одна.»

**Новое (placeholders):**
> ❌ ПЛОХО (recurring anti-pattern): «После [событие_X] в [YYYY_событие_X] [Субъект] [результат_Y]» — где result_Y фактически наступил позже из-за [событие_Z в YYYY_Z]. Это **вымышленная временная связка** между event_X и result_Y, причинно-следственно не подтверждённая в fact_map.
> ✅ ПРАВИЛЬНО: разделить факты — «После [событие_X] в [YYYY_событие_X] [Субъект] [фактическое_состояние_в_тот_момент]. [Результат_Y] наступил позже, в [YYYY_событие_Z], когда [событие_Z из fact_map.timeline].»

#### PIN_LIST антитриггеры (lines 2010-2014 в v2.24)
**Старое:**
> Огурцы из Молдавии: НЕ добавлять причинной связки «потому что не привозит достаточно подарков» — это домысел, не из source_quote.

**Новое (placeholder):**
> Pin-list event с emotional/conflict содержанием (примеры от subjects): НЕ добавлять причинную связку которой нет в source_quote. Если source_quote описывает факт (что произошло) — narrative воспроизводит факт, не интерпретирует причину. См. ПРАВИЛО 7 CA (named entity preservation) — пара mechanisms.

### Task 3 — B3 NOMINATIVE_CITY_RE generic

**Файл:** `pipeline_utils.py:4977` (function `validate_bio_data_family_format`)

**Старое:**
```python
NOMINATIVE_CITY_RE = re.compile(r"\bв\s+(Калинин|Москва|Ленинград|Тверь)\b")
```
Hardcoded список 4 cities.

**Новое (generic):**

Option A — extract from gazeteer:
```python
def _build_nominative_city_re(gazeteer_data):
    """Build regex для locative-case проверки из gazeteer all canonical cities + historical names."""
    cities = set()
    for city_entry in gazeteer_data.get("cities", []):
        cities.add(city_entry.get("canonical"))
        for alt in city_entry.get("historical_alternates", []):
            cities.add(alt)
    pattern = r"\bв\s+(" + "|".join(re.escape(c) for c in cities if c) + r")\b"
    return re.compile(pattern)
```

Option B — generic morpho check (без list):
```python
NOMINATIVE_CITY_RE = re.compile(
    r"\bв\s+([А-ЯЁ][а-яё]+(?:ово|ино|ое|ск|инск|оград|бург|ум|ка|ин))\b"
    # Распространённые city suffixes которые нужно в locative
)
```

**Рекомендую Option A** (gazeteer-driven) — точнее. Subject-specific cities приходят из `gazeteer_<subject>.json` per subject. Falls back to generic если gazeteer пустой.

**Tests:**
- gazeteer karakulina (Калинин, Тверь, Москва, Ленинград) → regex покрывает все
- gazeteer korolkova (hypothetical: Тула, Орёл) → regex покрывает Тула/Орёл, не Калинин
- empty gazeteer → fallback на generic morpho либо warning

---

## Стратегия v66a verify

1. Stage 1 split-extract (TR1+TR2) — pin-list v6 / configs v66a versions
2. Stage 2 first pass **GW v2.25** → book_draft.json
3. Все ~12 validators на book_draft (orchestrator подключает их все per v65 work)
4. Orchestrator (049f-2) собирает revision_hints → Stage 2 revision pass GW v2.25 с rule13_revision_applied списком
5. Diff_audit, hist_notes enrichment если distribution не fixed
6. Stage 3 + LE preserve writing_notes (049g)
7. Final validators → reports JSON
8. build_gate1_full_text → karakulina_v66a_text_FULL.md
9. **Pytest test_universality.py** обязательно зелёный на GW v2.25
10. **Опус independent verify**: open text_FULL.md, sравнить с v65c per all Никитины блокеры + recurring классы + chars

---

## Targets v66a (preserve v65c quality)

| Metric | v65c | v66a target |
|--------|------|-------------|
| Total chars build_gate1 | 20 042 | ≥ 19 500 (allow −2.5% variance) |
| ch_02 / ch_03 / ch_04 / epilogue chars | per floors | per floors (same) |
| Капошвара = площадь | ✅ | ✅ |
| Баба Аня в ch_03 | ✅ | ✅ |
| Дача без «1990-е» | ✅ | ✅ |
| Огурцы Молдавия preserved | ✅ | ✅ |
| Chronology errors | 0 | 0 |
| Stop phrases errors | 0 | 0 |
| writing_notes preserved | ✅ | ✅ |
| **Pytest test_universality GW v2.25** | n/a | **0 body matches** ✅ |
| **grep команда GW v2.25 body** | n/a | **0 matches** ✅ |
| **Subject-replacement test mental** | not applicable | **passed** for replaced subject |

**Risk A:** GW v2.25 с placeholders → quality снизилась.
- Mitigation: placeholders с explicit meta-description («[Имя_родственника: близкий из fact_map.persons]» вместо просто «[Имя]»)
- Mitigation: revision pass ловит regression и фиксит

**Risk B:** Test_universality.py даёт false positive на legitimate match в comment.
- Mitigation: калибровка HEADER_END_MARKERS; allowlist если есть legitimate uses

---

## Что НЕ делаем в v66a (явный список)

- ❌ Новые правила в GW v2.25 (только refactor existing 3/8/9/10 + PIN_LIST антитриггеры)
- ❌ CA / FC / FE / LE / Historian / Cleaner / Proofreader prompt changes — v66b/c
- ❌ pipeline_utils B1/B2 fixes — v66b
- ❌ Generic Stage runner (task 053) — v66c
- ❌ Audit_revision_diff fix — v66 backlog (after v66c)
- ❌ Bundle новых features
- ❌ Pin-list v7 changes (v6 OK для v66a)
- ❌ Подключение Корольковой — после v66c verify + RP-2

---

## Когда v66a готов

1. Verified-on-run от Курсора + push артефактов в `runs/karakulina-v66a-artifacts` (новая ветка)
2. **Опус откроет text_FULL.md независимо**: Capacity-replacement test для каждого рефакторенного правила, build_gate1 Total chars vs v65c, все Никитины блокеры остаются закрытыми
3. **Опус обновит run_registry** секцией `## v66a`
4. **Pytest test_universality.py** обязательно зелёный
5. Если PASS (quality сохранена + pytest green) → v66b spec → handoff Курсору
6. Если quality снизилась → diagnostic (какое правило сломало?) + откат либо refinement placeholders

---

## История

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-19 | `new` | Опус |
