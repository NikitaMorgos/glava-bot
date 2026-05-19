# v66 sprint: Universality refactor на Каракулиной (test bed)

**Статус:** `new`
**Sprint ID:** v66
**Автор:** Опус
**Дата создания:** 2026-05-19
**Триггер:** Universality audit 2026-05-19 (`collab/context/universality-audit-2026-05-19.md`) — 42 CRITICAL + 18 BUG в active prompts/code; Никитино решение «делать во время Каракулиной (test bed), не перед Корольковой»
**Связано:** dev-review-protocol.md Правило 4 УЖЕСТОЧЕНО (B.1+B.2+B.3 procedural enforcement)

---

## Контекст

**Никитин принцип (зафиксировано 2026-05-19):**
> «нам надо это всё сделать не перед Корольковой, а во время Каракулиной — чтобы проверить, насколько на Каракулиной работают эти универсальные правила. Поэтому лучше сейчас все специфические каракулинские темы убрать и посмотреть на следующем прогоне, что получается».

**Логика:** Каракулина — test bed для универсальности. Если pipeline с **placeholder examples** (а не захардкоженной каракулино-конкретикой) работает на Каракулиной → это **proof** что pipeline работает универсально. Если ломается → значит мы compensated subject-specific конкретикой, не реальной generalization.

**Сейчас:** 42 CRITICAL + 18 BUG в active prompts/code (см. audit). Каракулино-конкретика рассыпана в GW v2.23, CA v1.5, FC v2.13, pipeline_utils.py, sprint scripts.

**Цель v66:** убрать **всю** subject-specific конкретику из:
- LLM prompts (GW, CA, FC, FE)
- Pipeline_utils.py 2 validators (children_before_birth, entity_substitution)
- Stage runner scripts (task 053 generic runners)

И прогнать на **той же Каракулиной** — увидеть, что качество не ухудшилось (или ухудшилось — тогда поймём что мы держали на «костыли»).

---

## Pre-sprint checklist (Правила 3+4+7+8 + ужесточённое 4 B)

- [x] **Stocktake актуален** — `stocktake-2026-05-18-v60-v63.md` + `universality-audit-2026-05-19.md` (~5 sprints с прошлого stocktake = пора нового, но audit заменяет его в плане «лес»)
- [x] **Critical reading артефактов v65** выполнено перед planning (требует Курсорского verified-on-run; либо planning делается после v65 verify — см. timing ниже)
- [x] **Universality построчно (Правило 4 A)** — этот sprint **сам** про universality fix
- [ ] **Universality grep команда (Правило 4 B.1)** — будет выполнена Курсором перед commit'ом каждого refactored prompt
- [ ] **Universality pytest test (Правило 4 B.2)** — task 1 в этом sprint'е создаёт `tests/test_universality.py`
- [x] **Защита подключена к лечению** — да, refactor устраняет блокирующие subject-specific entries
- [x] **Прогоны раздельные где требуется (Правило 7)** — см. options (combined vs split) ниже
- [x] **Класс багов, не симптом** — universality fix целиком одного класса
- [x] **Скрипт-first** — 3 LLM prompt refactors (необходимо) + 3 scripted fixes + 1 test infrastructure

---

## Timing — после v65 verify, **независимо от outcome** (зафиксировано 2026-05-19)

**Решение:** v66 запускается после v65 verified-on-run, **независимо** от outcome v65.

**Логика (single-axis sprints):**
- v65 решает **bugs реализации v64** + **recurring classes** (одна ось — quality Каракулиной narrative)
- v66 решает **универсальность** (другая ось — pipeline architecture, ортогональна quality bugs)

| v65 outcome | Что после v66 |
|-------------|---------------|
| v65 PASS Ворот 1 на Каракулиной | v66 → проверка что universality не убивает quality → RP-1 + Королькова |
| v65 НЕ PASS | v66 → потом v67 узко fix'ит оставшееся **уже на универсальном pipeline** (clean diagnostic) |

Никитин принцип «test bed на Каракулиной» работает в любом случае: universality refactor на текущем subject = proof что pipeline работает с обобщёнными правилами.

**Не bundle v66 + v65b:** universality refactor — architectural change, узкие bugfix — другая семантика. Single-axis isolation per sprint.

---

## Формат реализации: **Опция B — Split v66a/b/c** (зафиксировано 2026-05-19)

**Решение:** 3 раздельных sub-sprints, $12-18 total.

**Обоснование (per Правило 7):**
- v63 combined Опция X — прямой precedent: 10 scripted + 1 GW rule + 1 CA + pin-list в одном прогоне = невозможна диагностика; v64 = архитектурный ход который надо было делать в v63 (выкинутый sprint)
- Universality refactor = **architectural change** на 3 LLM agents, не bugfix известного эффекта. Risk regression high (5 sprints мы держали захардкоженными examples — они могли «работать» именно потому что были subject-specific)
- $12-18 vs $4-6 — относительно небольшая дельта; разовая инвестиция в proof универсальности
- Per Правилу 7 «сейчас нам важней результат стабильный получить»

---

## Раздельные sub-sprints

### v66a — GW v2.25 universality + test infrastructure + B3

**Tasks:**
1. **test_universality_infrastructure**: `tests/test_universality.py` + `tests/data/subject_specific_terms.txt` (уже создан) — pytest CI gate
2. **GW v2.24 → v2.25**: refactor ПРАВИЛ 3, 8, 9, 10 + PIN_LIST антитриггеры (lines 260-460, 2010-2014). Все examples → placeholders ([Имя_близкого], [Локация_X], [YYYY], [объект_X]). Дополнить task 049h v65 (только ПРАВИЛО 2 был refactored)
3. **B3 — pipeline_utils.py NOMINATIVE_CITY_RE generic**: `pipeline_utils.py:4977` — generic morpho check либо расширение из gazeteer

**Прогон:** 1 шт. v66a — $4-6.

**Verify:** GW работает на placeholders на Каракулиной → quality сохранена.
- Total chars vs v65 stable (±5%)
- discourse markers / pin-list depth / recurring classes — не хуже v65
- `tests/test_universality.py` GW v2.25 PASS
- `grep` команда GW v2.25 body — 0 matches

### v66b — CA v1.6 universality + B1 + B2

**Tasks:**
1. **CA v1.5 → v1.6**: refactor ПРАВИЛ 1, 2, 4, 6, 7 + JSON schema events example. Lines 14, 64, 94-96, 134-136, 284-306, 329-336, 374-379, 391-400
2. **B1 — pipeline_utils.py validate_children_before_birth parametrize**: `pipeline_utils.py:4692-4695` — извлекать `child_name_stem` из `chronology_periods_<subject>.json`, не hardcoded
3. **B2 — pipeline_utils.py validate_entity_substitution config**: `pipeline_utils.py:4900-4904` — `substitution_pairs` → `entity_substitution_<subject>.json` (новый config) либо расширение fact_map.place_canonical

**Прогон:** 1 шт. v66b — $4-6.

**Verify:** CA + validators универсальные.
- Pin-list events coverage на Каракулиной не упал
- chronology + entity_substitution работают на configs (не hardcoded)
- `tests/test_universality.py` CA v1.6 PASS

### v66c — FC v2.14 + FE v3.5 + C1 generic Stage runner

**Tasks:**
1. **FC v2.13 → v2.14**: refactor block lines 853-1031 (~150 строк «огурцы Object Markers Test») → placeholder example + 6 BUG examples (lines 62, 324, 545-546, 775-776, 1037-1039). **Самый большой fix**
2. **FE v3.4 → v3.5**: minor refactor (lines 343-358, 547 → placeholders)
3. **C1 — generic Stage 1 runner (task 053)**: `scripts/run_stage1.py` (новый, generic) — `--subject=<name>`, `--project-id=<id>` CLI args; per-subject defaults config

**Прогон:** 1 шт. v66c — $4-6.

**Verify:** FC + FE универсальные; generic runner работает на Каракулиной (заменяет `test_stage1_karakulina_full.py` либо параллельно).
- FC verdict на Каракулиной не хуже v65
- `tests/test_universality.py` FC v2.14 + FE v3.5 PASS
- Generic runner с `--subject=karakulina` даёт идентичный output старому

---

## Что НЕ делаем в v66 (явный список)

### Опция A — Combined sprint (1 прогон $4-6)

**Все 9 tasks в одном sprint, один прогон verify.**

| # | Task | Файл | Изменение |
|---|------|------|-----------|
| 1 | **universality_test_infrastructure** | `tests/test_universality.py` + `tests/data/subject_specific_terms.txt` (уже создан) | Pytest CI gate. Парсит `prompts/*.md`, отделяет шапку version history от body правил, прогоняет regex по terms. FAIL если match в body |
| 2 | **GW v2.24 → v2.25 universality refactor** | `prompts/03_ghostwriter_v2.25.md` | Refactor ПРАВИЛ 3, 8, 9, 10 + PIN_LIST антитриггеры (lines 260-460, 2010-2014). Все examples → placeholders ([Имя_близкого], [Локация_X], [YYYY], [объект_X]). Дополнить task 049h (v65 закрыл только ПРАВИЛО 2) |
| 3 | **CA v1.5 → v1.6 universality refactor** | `prompts/16_completeness_auditor_v1.6.md` | Refactor ПРАВИЛ 1, 2, 4, 6, 7 + JSON schema events example. Lines 14, 64, 94-96, 134-136, 284-306, 329-336, 374-379, 391-400 |
| 4 | **FC v2.13 → v2.14 universality refactor** | `prompts/04_fact_checker_v2.14.md` | **Самый большой fix**: lines 853-1031 (~150 строк «огурцы Object Markers Test») → placeholder example + 6 BUG examples |
| 5 | **FE v3.4 → v3.5 universality refactor** | `prompts/02_fact_extractor_v3.5.md` | Minor: lines 343-358, 547 → placeholders |
| 6 | **B1 — pipeline_utils.py validate_children_before_birth parametrize** | `pipeline_utils.py:4692-4695` | Извлекать `child_name_stem` из `chronology_periods_<subject>.json`, не hardcoded |
| 7 | **B2 — pipeline_utils.py validate_entity_substitution config** | `pipeline_utils.py:4900-4904` | `substitution_pairs` → `entity_substitution_<subject>.json` (новый config) либо расширение fact_map.place_canonical |
| 8 | **B3 — pipeline_utils.py NOMINATIVE_CITY_RE generic** | `pipeline_utils.py:4977` | Generic morpho check либо расширение из gazeteer |
| 9 | **C1 — generic Stage 1 runner (task 053)** | `scripts/run_stage1.py` (новый, generic) | `--subject=<name>`, `--project-id=<id>` CLI args; per-subject defaults config |

**Плюсы:** 1 прогон $4-6, видим эффект всей универсальности на Каракулиной в одном тесте.

**Минусы:** **3 prompt-bumps + 3 scripted в одном прогоне.** Per Правило 7 — это нарушение «не экономим на тестовых прогонах». Если v66 даст regression — невозможно диагностировать какой fix (GW v2.25 / CA v1.6 / FC v2.14 / B1 / B2 / C1) сломал.

**Risk:** medium. Один из 9 fixes может regression — придётся откатить весь sprint.

### Опция B — Split sprints (3 прогона $12-18)

**Разбить на 3 sub-sprints, каждый = 1 prompt-bump + связанные scripted fixes:**

**v66a — GW v2.25 universality + B3 NOMINATIVE_CITY_RE:**
- Task 1 (test infrastructure) + Task 2 (GW v2.25) + Task 8 (B3) + минор generic Stage runner stub
- 1 прогон $4-6
- Проверка: GW работает на placeholders на Каракулиной → quality сохранена

## Что НЕ делаем в v66 (явный список)

- ❌ Новые правила в LLM prompts (только refactor existing examples → placeholders)
- ❌ Изменения в LE v3.1, Historian v3, Cleaner v1, Proofreader v1 (audit показал clean)
- ❌ Изменения в generic configs (audit показал clean)
- ❌ Sprint scripts cleanup (D1-D4 из audit — Phase 2, делаем с каждым новым sprint, не специально)
- ❌ DOCS clarity (E1-E3 — Phase 3, низкий приоритет)
- ❌ Подключение Корольковой (после RP-1 на Каракулиной)
- ❌ Bundle новых features (только refactor)

---

## Что подключить к v66 sprint (универсальный test infrastructure)

### tests/test_universality.py (создание)

```python
"""
Universality CI gate — pytest test для Правила 4 B.2.

Парсит prompts/*.md, отделяет шапку version history (allowed subject-specific
matches) от body правил (NOT allowed). Прогоняет regex из subject_specific_terms.txt.
FAIL если match в body.
"""
import re
import pytest
from pathlib import Path


PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
TERMS_FILE = Path(__file__).parent / "data" / "subject_specific_terms.txt"

# Только active prompts (из pipeline_config.json). Архивные версии (v2.13, v2.18, etc.) skip.
ACTIVE_PROMPTS = {
    "ghostwriter": "03_ghostwriter_v2.25.md",  # после v66 refactor
    "completeness_auditor": "16_completeness_auditor_v1.6.md",
    "fact_extractor": "02_fact_extractor_v3.5.md",
    "fact_checker": "04_fact_checker_v2.14.md",
    "literary_editor": "05_literary_editor_v3.1.md",
    "historian": "12_historian_v3.md",
    "cleaner": "01_cleaner_v1.md",
    "proofreader": "06_proofreader_v1.md",
}

# Markers отделяющие шапку version history от body правил.
# Шапка — до первого ══════ либо до строки "## SYSTEM PROMPT" / "```"
HEADER_END_MARKERS = ["══════", "## SYSTEM PROMPT", "═══"]


def load_subject_terms():
    """Load regex patterns from subject_specific_terms.txt."""
    patterns = []
    for line in TERMS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        patterns.append(line)
    return patterns


def split_header_body(prompt_text: str) -> tuple[str, str]:
    """Разделить prompt на header (allowed subject mentions) и body (NOT allowed)."""
    for marker in HEADER_END_MARKERS:
        idx = prompt_text.find(marker)
        if idx > 0:
            return prompt_text[:idx], prompt_text[idx:]
    # Если нет marker — весь файл = body (strict mode)
    return "", prompt_text


@pytest.mark.parametrize("prompt_name,filename", ACTIVE_PROMPTS.items())
def test_prompt_universality(prompt_name, filename):
    """В body правил активного prompt НЕ должно быть subject-specific terms."""
    prompt_path = PROMPTS_DIR / filename
    if not prompt_path.exists():
        pytest.skip(f"Prompt {filename} не существует (возможно ещё не создан)")
    
    text = prompt_path.read_text(encoding="utf-8")
    header, body = split_header_body(text)
    patterns = load_subject_terms()
    
    violations = []
    for pattern in patterns:
        matches = list(re.finditer(pattern, body, re.IGNORECASE))
        for m in matches:
            # Найти номер строки match в body
            line_num = body[:m.start()].count("\n") + len(header.split("\n"))
            violations.append({
                "pattern": pattern,
                "match": m.group(),
                "line": line_num,
                "context": body[max(0, m.start()-40):m.end()+40],
            })
    
    if violations:
        msg = f"\nUniversality violations в {filename} body (НЕ в version history):\n"
        for v in violations[:10]:  # limit вывод
            msg += f"  L{v['line']}: pattern '{v['pattern']}' → '{v['match']}'\n    context: ...{v['context']}...\n"
        if len(violations) > 10:
            msg += f"  ...и ещё {len(violations) - 10} violations\n"
        msg += f"\n=== FIX: переделать примеры в body на placeholders (см. dev-review-protocol Правило 4 B) ==="
        pytest.fail(msg)
```

**CI integration:** обязательный test в `tests/`, прогоняется на каждом commit prompts/*.md. Без green test — merge заблокирован.

---

## Risk + mitigation v66 (общее для обоих опций)

**Risk A:** Refactor examples → placeholders может **сломать понимание** LLM. Пример был instruction, placeholder может быть менее clear.

**Mitigation:** placeholders с **explicit мета-описанием** (`[Имя_близкого: родственник субъекта из fact_map.persons]` вместо просто `[Имя]`). LLM понимает intent.

**Risk B:** Caracculина quality снизится после refactor (на самом деле GW лучше работал с захардкоженными examples).

**Mitigation:** Это **именно то что мы тестируем**. Если quality снизилась — значит мы compensated subject-specific конкретикой. Никитин принцип: лучше знать сейчас на Каракулиной чем при подключении Корольковой.

**Risk C:** Один из 3 sub-sprints (v66a/b/c) даёт regression на Каракулиной.

**Mitigation:** Split sprints — точная диагностика per prompt-bump; rollback узкого fix не trog other agents. Per Правилу 7.

**Risk D:** Тест `tests/test_universality.py` даёт false positive (legitimate match в comment dev / objection).

**Mitigation:** калибровка — HEADER_END_MARKERS точно отделяют шапку (где matches OK); allowed-patterns whitelist (если есть legitimate uses в comments dev).

---

## Решения зафиксированы 2026-05-19

1. ✅ **Формат:** Опция B — split v66a/b/c, 3 прогона $12-18 (per Правило 7)
2. ✅ **Timing:** после v65 verified-on-run, независимо от outcome
3. ✅ **Правило 4** УЖЕСТОЧЕНО в `dev-review-protocol.md` — A (мысленный test) + B (procedural enforcement: grep команда + pytest CI gate + pre-sprint checklist + audit-driven cleanup)

Никита делегировал выбор Опусу (2026-05-19) с обоснованием через v63 combined precedent (выкинутый sprint из-за невозможности диагностики).

---

## Следующие шаги

1. **Сейчас:** ждать v65 verified-on-run от Курсора
2. **После v65 verify:** Опус делает independent verify v65 + обновляет run_registry v5
3. **Затем v66a:** Опус пишет 3 spec'a (test infrastructure + GW v2.25 + B3) + handoff Курсору
4. **Курсор реализует v66a** → verify
5. **v66b → v66c** аналогично с verify между
6. **После v66c verify:** если quality на Каракулиной сохранена — tag RP-1 + подключение Корольковой (task 053 generic runner уже готов в v66c)

---

## История

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-19 | `new` | Опус |
