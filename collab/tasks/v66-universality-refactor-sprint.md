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

## Timing — когда делаем v66

**Зависимость:** v65 в работе у Курсора (bugfix v64 implementation). Логика:

| v65 outcome | v66 timing |
|-------------|------------|
| **v65 PASS** Ворот 1 на Каракулиной | v66 universality refactor → проверка на следующем прогоне Каракулиной. Если quality сохранилось — RP-1 + Королькова |
| **v65 НЕ PASS** | Решить: либо v65b (узкий bugfix v65) → потом v66 универсальность; либо v66 (содержит и universality, и узкие bugfix) — risk bundle |

**Рекомендация (моя):** v66 = универсальность **независимо** от v65 outcome. Никитин принцип «test bed на Каракулиной» — universality fix должен пройти прогон Каракулиной для verification. Если v65 не закроет Ворот 1 — v67 узко fixит оставшееся, **уже на универсальном pipeline**.

---

## 2 опции реализации v66

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

**v66b — CA v1.6 + B1 validate_children_before_birth + B2 validate_entity_substitution:**
- Task 3 (CA v1.6) + Task 6 (B1) + Task 7 (B2)
- 1 прогон $4-6
- Проверка: CA работает универсально + validators параметризованные

**v66c — FC v2.14 + FE v3.5 + C1 generic Stage runner:**
- Task 4 (FC v2.14) + Task 5 (FE v3.5) + Task 9 (C1)
- 1 прогон $4-6
- Проверка: FC + FE универсальные; generic runner работает (либо проверка через mock Корольковой subject)

**Плюсы:** Per Правило 7 — каждый prompt-bump verified отдельно. Точная диагностика если что-то сломается. Меньший risk per sprint.

**Минусы:** 3 прогона $12-18 total. Длиннее по времени (3-4 дня вместо 1-2).

**Risk:** low per sprint.

---

## Моя рекомендация

**Опция B (split sprints)** — соответствует Правилу 7 («не экономим на тестовых прогонах»). Универсальность — серьёзный архитектурный refactor, не bugfix. Каждое prompt-bump = риск регрессии в **другом** месте (cognitive shift при изменении examples может изменить attention LLM в неожиданных направлениях).

**Cost:** $12-18 total — приемлемо per Никитино «сейчас нам важней результат стабильный».

**Time:** 3-4 дня (vs 1-2 для combined) — приемлемо, цели Корольковой это того стоит.

---

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

**Risk C:** Combined sprint v66 даёт regression — не диагностируем что fix виноват.

**Mitigation:** Split (Опция B) — каждый prompt-bump verified отдельно.

**Risk D:** Тест `tests/test_universality.py` даёт false positive (legitimate match в comment dev / objection).

**Mitigation:** калибровка — HEADER_END_MARKERS точно отделяют шапку (где matches OK); allowed-patterns whitelist (если есть legitimate uses в comments dev).

---

## Что нужно от Никиты

1. **Выбор Опция A (combined $4-6) vs Опция B (split $12-18)**
2. **Timing:** делать v66 сразу после v65 verify (независимо от v65 outcome) либо ждать v65 PASS Ворот 1?
3. **Sign-off:** на изменение Правила 4 в `dev-review-protocol.md` (B.1+B.2+B.3 procedural enforcement)

---

## История

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-19 | `new` | Опус |
