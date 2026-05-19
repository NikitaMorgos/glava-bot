# Handoff Курсору — 2026-05-19 (для нового окна, перед v66a sprint)

> **Документ-страховка для нового окна Курсора.** Новое окно читает этот файл **первым** (5-10 мин) → готов к v66a.

---

## За 30 секунд: где мы

**Каракулина PASS Ворот 1 в v65c.** Tag `rp-1-karakulina-gate1-pass` на commit `2cb5394`. Total chars = 20 042, все 3 Никитины content blockers закрыты (Капошвара = площадь, Баба Аня в ch_03, дача без 1990-е), validators clean.

**Сейчас — universality refactor на test bed Каракулиной** (Никитин принцип «убрать каракулинские темы и посмотреть на следующем прогоне что получается»). Цель — proof что pipeline работает с **placeholder** examples (не захардкоженной конкретикой).

**v66 = 3 sub-sprints (Опция B split):**
- **v66a (этот sprint):** test_universality.py infrastructure + GW v2.25 (ПРАВИЛА 3/8/9/10 + PIN_LIST антитриггеры refactor) + B3 NOMINATIVE_CITY_RE generic
- v66b: CA v1.6 + B1 + B2
- v66c: FC v2.14 + FE v3.5 + C1 generic Stage runner

Каждый sub-sprint = 1 verify прогон ($4-6).

---

## Команда и роли — без изменений

| Роль | Кто |
|------|-----|
| Owner / Product Lead | Никита |
| Архитектор + Продакт | Опус |
| Исполнитель | Курсор |

---

## ОБЯЗАТЕЛЬНО прочитать (20 мин)

### Принципы (обновлено 2026-05-19)

1. **`collab/context/dev-review-protocol.md` v2** ⭐ — **8 правил архитектора**. **Правило 4 УЖЕСТОЧЕНО:**
   - A: мысленный test (4 вопроса) — **недостаточен** (провалили 3 раза)
   - **B.1: ОБЯЗАТЕЛЬНАЯ grep команда** перед commit'ом GW/CA prompt-bump
   - **B.2: pytest tests/test_universality.py — CI gate, fails при subject-specific match в body правил**
   - B.3: Pre-sprint checklist hard validation
   - B.4: Audit-driven cleanup (v66 universality refactor)

2. **`collab/tasks/_template.md`** — pre-sprint checklist в шапке

### Sprint v66a

3. **`collab/tasks/v66a-universality-test-infra-gw-rule3-8910.md`** ⭐ — главный план v66a (3 tasks)
4. **`collab/tasks/v66-universality-refactor-sprint.md`** — overarching план v66 (3 sub-sprints)
5. **`collab/context/universality-audit-2026-05-19.md`** — audit findings (42 CRITICAL в GW/CA/FC; v66a покрывает GW части)

### v65c контекст (что было, RP-1 reference)

6. **`runs/karakulina-v65-artifacts:collab/runs/karakulina-v65-artifacts/karakulina_v65c_text_FULL.md`** — v65c output (Ворота 1 PASS на этом тексте)
7. RP-1 tag: `rp-1-karakulina-gate1-pass` (commit `2cb5394`)

---

## 8 правил архитектора (обновлено 2026-05-19, ты сверяешь)

| # | Правило | v66a status |
|---|---------|-------------|
| 1 | План перед волной | ✅ 3 готовых tasks |
| 2 | Артефакт перед проектированием | ✅ Опус read v65c text_FULL.md глазами |
| 3 | Stocktake каждые 2-3 волны | ✅ актуален (счётчик 2 verified-on-run после universality audit) |
| 4 | **Universality построчно** УЖЕСТОЧЕНО | ⚠️ обязательная grep команда + pytest test перед commit'ом GW v2.25 |
| 5 | Run registry update | После v66a — Опус добавит секцию ## v66a |
| 6 | 1 правило per bump | ✅ v2.25 = **4 rule refactors** existing rules (НЕ новые правила, bug fixes) + 1 minor В рамках one cohesive refactor |
| 7 | **Не экономим на тестовых прогонах** | ✅ v66a = ОТДЕЛЬНЫЙ прогон $4-6, не bundle с v66b/c |
| 8 | **Класс лечится семантикой, не regex** | ✅ universality fix через placeholders + pytest CI gate (procedural) |

---

## 7 принципов команды

1. Лес/деревья — лечим классы багов
2. Универсальность — все subjects
3. Класс багов, не симптом
4. Скрипт-first
5. Логирование
6. Медленно без откатов
7. **НЕ экономим на тестовых прогонах** (новое 2026-05-19)

---

## v65c outputs (RP-1 reference, что было)

**Артефакты:** `runs/karakulina-v65-artifacts` @ `2cb5394` (tag `rp-1-karakulina-gate1-pass`)

**Метрики v65c:**
- Total chars: **20 042** ✅
- ch_01=3221, ch_02=7730, ch_03=4854, ch_04=3160, epilogue=1077
- Historical_notes: 7 field + 7 inline
- Chronology / Stop_phrases / Cross_paragraph_dup: 0 errors
- writing_notes preserved post-LE ✅
- 3 Никитины content blockers — все закрыты

**Versions использованные в v65c:**
- GW v2.24 (revision pass второй для 3 content fixes)
- CA v1.5, FC v2.13, LE v3.1, Historian v3
- pin-list v6, gazeteer v2 + paspart temporal
- 3 generic configs (chronology_check, cross_paragraph_duplication, historical_notes_distribution)

---

## v66a — 3 tasks

### Task 1 — `tests/test_universality.py` (test infrastructure)

**Зачем:** CI gate для Правила 4 B.2. Automatic check что body правил активных prompts НЕ содержит subject-specific terms (header version history OK).

**Файлы:**
- `tests/test_universality.py` (новый, реализация в spec)
- `tests/data/subject_specific_terms.txt` — **уже создан в main** (regex patterns для Karakulina + future subjects placeholders)

**Реализация:** см. v66-universality-refactor-sprint.md (раздел «tests/test_universality.py»). Parse `pipeline_config.json` для active prompts list; split header/body по `══════` markers; regex check.

**Tests for v66a verify:**
- GW v2.25 → **0 body matches PASS**
- CA v1.5 / FC v2.13 → должны быть matches (closure в v66b/c)
- LE v3.1, Historian v3, Cleaner v1, Proofreader v1 → 0 matches (already clean per audit 2026-05-19)

### Task 2 — GW v2.24 → v2.25 universality refactor

**Файл:** `prompts/03_ghostwriter_v2.25.md` (новый — копия v2.24 + 4 правила refactored)

**Что менять (per universality audit findings):**

#### ПРАВИЛО 3 — stop-phrases (lines 260-267 в v2.24)
Заменить subject-specific example (Валерий/Венгрия/интернат) на placeholder example. Ссылка на narrative_stop_phrases.json category `event_that_changed_life`.

#### ПРАВИЛО 8 — first paragraph contains facts (lines 337-366 в v2.24)
Заменить 3 examples (шуба/пианино/авоська/«стойкий оловянный солдатик»/Даша) на placeholder versions с meta-описанием.

#### ПРАВИЛО 9 — X-по-Y formulation (lines 402-419 в v2.24)
Заменить «Дашин зять Маргось» example + «электричество/поездки» negative на placeholder. Ссылка на category `class11_not_loved_x_by_y_and_z_extended`.

#### ПРАВИЛО 10 — temporal connectors (lines 427-460 в v2.24) — **самый большой fix**
~30 строк Каракулино-конкретики (Дмитрий, Татьяна, Маргось, Кужба, Капошвара, Тверь, Химинститут, 1978, 1996) — все на placeholders.

#### PIN_LIST антитриггеры (lines 2010-2014 в v2.24)
Огурцы/Молдавия пример → placeholder example про generic emotional/conflict эпизод.

**Detail см. в spec v66a.**

### Task 3 — B3 NOMINATIVE_CITY_RE generic

**Файл:** `pipeline_utils.py:4977` (function `validate_bio_data_family_format`)

**Сейчас (Каракулино-specific):**
```python
NOMINATIVE_CITY_RE = re.compile(r"\bв\s+(Калинин|Москва|Ленинград|Тверь)\b")
```

**Нужно:** generic, либо строит regex из `gazeteer_<subject>.json` cities list. См. spec.

**Tests:** gazeteer karakulina покрывает Калинин/Тверь; hypothetical gazeteer korolkova (Тула/Орёл) — works without code change.

---

## Версионирование v66a

- **GW v2.24 → v2.25** (refactor existing rules, НЕ новые правила; per Правило 6)
  - Новый файл `prompts/03_ghostwriter_v2.25.md`
  - `pipeline_config.json.ghostwriter.prompt_file` → `"03_ghostwriter_v2.25.md"`
- **CA v1.5** — без изменений
- **pin-list `known_episodes_karakulina.md` v6** — без изменений
- **Configs** — без изменений
- **Code:**
  - `pipeline_utils.py:4977` — `NOMINATIVE_CITY_RE` параметризуется
  - `tests/test_universality.py` — новый файл
- **gate1_product_checklist.md v2** — без изменений

---

## Branch стратегия v66a

**Base:** main (после PR v66a specs merged) либо текущий v65c artifact commit + universality-audit branch
**Новая ветка кода:** `feat/v66a-universality-prep` off main
**Новая ветка артефактов:** `runs/karakulina-v66a-artifacts` после прогона

---

## Прогон v66a — что именно запускать

1. Stage 1 split-extract (pin-list v6)
2. Stage 2 first pass **GW v2.25** → book_draft.json
3. Все ~12 валидаторов на book_draft (orchestrator 049f-2 подключает их все, per v65 work)
4. Orchestrator → revision_hints → Stage 2 revision pass GW v2.25 (с rule13_revision_applied как list)
5. Schema validation + diff_audit
6. Historical_notes enrichment post-revision (если distribution неравномерное)
7. Stage 3 + 049g preserve writing_notes + post-processing
8. **pytest test_universality.py** PASS обязательно
9. Final validators → reports JSON
10. build_gate1 → karakulina_v66a_text_FULL.md
11. Push в `runs/karakulina-v66a-artifacts` (новая ветка) + ваш VERIFIED_ON_RUN отчёт

Создай `scripts/_run_v66a_full.sh` (extend `_run_v65_full.sh` с GW v2.25 + test_universality.py step).

---

## Дисциплина для Курсора в v66a

1. **GW v2.25 = 4 hot-fixes existing rules (НЕ новые правила).** Не добавляй ничего ещё.

2. **ОБЯЗАТЕЛЬНАЯ grep команда перед commit'ом prompts/03_ghostwriter_v2.25.md** (Правило 4 B.1):
   ```bash
   grep -in "Каракулин\|Татьян\|Валентин\|Химинститут\|выковырив\|зарубить\|зажиточн\|движуха\|рукаст\|бабульно\|Молдави\|Маргось\|Кужб\|Капошвар\|Влась\|Полин\|Маня\|Шура\|Аня\|Нинван\|Марф\|Кировоград\|Старобельск\|Венгри\|Германи\|Кечкемет\|Сахалин\|Кирсанов\|Сафроново\|1946\|1956\|1962\|1977\|1978\|1996\|две недели" prompts/03_ghostwriter_v2.25.md
   ```
   Допустимы matches только в шапке version history. **Любые matches в body правил** — переделать на placeholder перед commit'ом. Это закрытие моей recurring ошибки (v60/v63/v64).

3. **Pytest test_universality.py обязательно зелёный** перед merge:
   - GW v2.25 → 0 body matches ✅
   - Other prompts (CA/FC) → допустимо matches (closure в v66b/c)
   - LE/Historian/Cleaner/Proofreader → 0 (already clean)

4. **Verified-on-run = одно конкретное наблюдение per task.**

5. **Chars metric — build_gate1 «Total chars»** (sum content всех глав), НЕ file_size. **3-й раз lesson v62a/v63/v64/v65** — не повтори (v65 ты отчитал 24 111 при реальных 19 705).

6. **Cross-check VERIFIED отчёт с реальными артефактами** (lesson v63 Татьяна 1952, lesson v64 chars, lesson v65 баба Аня — Курсор был **прав** в v65c, я зря не учёл падежи). Если в отчёте написал X — открой JSON и убедись что реально X.

7. **Manifest versions** — Stage 2/3 manifest: `ghostwriter_version: v2.25`, `completeness_auditor_version: v1.5`.

8. **writing_notes proof-of-attention** (schema из v65 049e-2):
   - `rule13_revision_applied` — list of dicts
   - `rule13_revision_failed` — bool
   - **«action» field** теперь обязателен (v65 показал GW использует `fix` — переучить на `action`)

9. **diff_audit `revision_diff_audit.json`** — артефакт с unauthorized_changes (audit_revision_diff chapter-level fix в backlog после v66c)

10. **NO bundle:** не добавляй CA / FC / FE / LE changes в v66a. Только GW v2.25 + test infra + B3. Остальное — v66b/c.

11. **Git push** обеих веток (`feat/v66a-universality-prep` + `runs/karakulina-v66a-artifacts`).

---

## Targets для v66a (preserve v65c quality)

Distribution gate:
- **Total ≥ 19 500 (allow −2.5% variance vs v65c)**, narrative ≥ 15K, paspart ~3K, hist_notes ≥2K
- Per-chapter floors: ch_02 ≥7K / ch_03 ≥4K / ch_04 ≥2.5K / epilogue 800-1500

Content (must preserve from v65c):
- Капошвара = площадь (3 mentions) ✅
- Баба Аня в narrative ch_03 ✅
- Дача без «1990-е годы» ✅
- Огурцы Молдавия preserved ✅
- Мария / тётя Маша / грибы — present

Validators clean после revision:
- Chronology 0 errors ✅
- Stop phrases 0 errors ✅
- Cross paragraph dup 0 ✅
- Pin-list depth ≤ 4 errors (accept v65c level)

**Universality (новое):**
- **pytest test_universality.py GW v2.25 = 0 body matches** ✅ обязательно
- **grep команда GW v2.25 = 0 matches в body** ✅
- Subject-replacement test mental for ПРАВИЛА 3/8/9/10 — passed

Architecture:
- Stage 2 manifest: ghostwriter_version=v2.25, completeness_auditor_version=v1.5
- writing_notes.rule13_revision_applied — list with `action` field
- revision_failed = false

---

## Risk + mitigation v66a

**Risk A:** GW v2.25 с placeholder examples → quality снизилась (LLM хуже работает без захардкоженных примеров).
- Mitigation: placeholders с **explicit meta-description** в скобках («[Имя_близкого: родственник субъекта из fact_map.persons]» не просто «[Имя]»)
- Mitigation: revision loop ловит regression
- Mitigation: если quality FAIL > 5% → rollback к v2.24 + diagnostic

**Risk B:** Test_universality.py false positive на legitimate match в comment.
- Mitigation: калибровка HEADER_END_MARKERS

**Risk C:** Капошвара/баба Аня/дача регрессируют после v2.25 (placeholders недостаточно clear).
- Mitigation: revision pass + post-process scripted check (validate_entity_substitution + narrative_required_persons если реализовано в v65c)

---

## Финансово

v66a = **1 прогон $4-6** (revision loop). Не экономим per Правило 7.

---

## Когда v66a готов

1. Verified-on-run от Курсора + push артефактов в `runs/karakulina-v66a-artifacts`
2. **Pytest test_universality.py зелёный**
3. Опус откроет text_FULL.md независимо — verify quality preserved vs v65c
4. Опус обновит run_registry секцией `## v66a`
5. Если PASS (quality preserved + universality test green) → Опус пишет v66b spec → handoff Курсору
6. Если quality снизилась → diagnostic (какое правило сломало?) + откат либо refinement

---

## Что НЕ делать в v66a (явный список)

- ❌ CA / FC / FE / LE / Historian prompt changes — v66b/c
- ❌ pipeline_utils B1/B2 fixes — v66b
- ❌ Generic Stage runner (task 053) — v66c
- ❌ Audit_revision_diff chapter-level fix — v66 backlog (после v66c)
- ❌ Pin-list v7 changes — pin-list v6 OK для v66a
- ❌ Bundle новых features
- ❌ Skip grep команды перед commit'ом GW v2.25 (Правило 4 B violation)
- ❌ Skip pytest test_universality.py (Правило 4 B violation)
- ❌ Подключение Корольковой — после v66c verify + RP-2

---

## Версии этого документа

| Версия | Дата | Изменение | Кто |
|---|---|---|---|
| v1 | 2026-05-19 | Создание перед v66a sprint после RP-1 на v65c | Опус |
