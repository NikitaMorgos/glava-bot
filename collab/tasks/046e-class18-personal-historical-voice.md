# Задача 046e: Class 18 NEW — personal-historical voice (pin-list anchors + validator)

**Статус:** `new`
**Номер:** 046e
**Автор:** Опус (роль архитектор+продакт)
**Дата создания:** 2026-05-18
**Тип:** конфиг + pin-list extension + cco-скрипт + snapshot tests
**Sprint:** v64
**Связано:** Никитин feedback v63 «нет исторических вкраплений рассказчика»; existing discourse_markers validator (task 049); существующий class «historical_notes» field (objective) и discourse_markers (rapporteur attribution) — но **personal-historical voice** новый класс

---

## Контекст

**Никитин feedback v63 (точная цитата):**
> «мало врезок историка, почему так? и нет исторических вкраплений рассказчика»

**Две разные проблемы:**
1. «Мало врезок историка» — historical_notes regression v62a 10+10 → v63 3+0 (task 046d)
2. «Нет исторических вкраплений рассказчика» — **новый класс**

**Что есть в пайплайне:**
- ✅ `historical_notes (field)` — **objective** исторические справки от historian («Голодомор был экономическим бедствием...»)
- ✅ `discourse_markers` — **attribution** воспоминаний рассказчика («Татьяна вспоминает: ...», «по словам дочери»)

**Что отсутствует:**
- ❌ **Personal-historical voice** — рассказчик помещает свою личную память в исторический контекст эпохи: «Как я помню, в 90-е цены росли каждую неделю — мама постоянно ворчала на это», «Тогда, в нашей семье, дача была обычным делом — у всех соседей по Химинституту были»

Это **третий слой**: не отдельный historical fact (historian), не атрибуция фразы (discourse marker), а **slice голоса рассказчика-внука + эпоха через личную lens**.

**Класс 18 NEW:** patterns личного-исторического attribution.

**Реализация (Никитин 3c):** combined a+b:
- a) Pin-list extension `narrator_voice_anchors` — examples из TR1/TR2 actual фраз
- b) Validator `validate_personal_historical_voice` — detector + threshold per chapter

---

## Universality check

- [x] Промпт — n/a (config + script + pin-list)
- [x] Subject-specific — pin-list anchors per subject (`narrator_voice_anchors` секция в `known_episodes_<subject>.md`); validator generic
- [x] Алгоритм generic — pattern detection с use of subject-specific rapporteurs
- [x] Subject-replacement test — для Корольковой с другим rapporteur'ом и эпохой работает (other anchors) ✅

---

## Спек

### 1. Pin-list extension `known_episodes_karakulina.md` v6 (либо v5 если task 044h объединяет)

Новая секция **`## narrator_voice_anchors`** — examples actual фраз из TR1/TR2 рассказчика (Татьяны, Никиты), помещающих личную память в исторический контекст:

```markdown
## Narrator voice anchors — personal-historical attribution (Class 18)

> Examples фраз рассказчика, помещающих личную/семейную память в исторический
> контекст эпохи. Используются как образцы для GW + детектор validator'ом.

| anchor_id | rapporteur | period | phrase_pattern | source |
|-----------|------------|--------|----------------|--------|
| nv_001 | Татьяна | 1990-е | «как я помню, в 90-е [event]» | TR1 |
| nv_002 | Татьяна | 1960-е | «тогда у нас в семье [event]» | TR1 |
| nv_003 | Татьяна | детство | «когда я была ребёнком, [event]» | TR1, TR2 |
| nv_004 | Никита | 1980-е | «помню, в детстве я [event]» | TR2 |
| nv_005 | Никита | 1990-е | «в школе тогда [event]» | TR2 |
| nv_006 | generic | любой | «как мы помним, [event]» / «по тем временам [event]» | both |
| nv_007 | Татьяна | 1962+ | «у нас в Химинституте [event]» | TR1 |
| nv_008 | generic | советская эпоха | «в советское время [event]» / «по советским меркам [event]» | both |

### Generic patterns (для validator regex)

Markers detection:
- `(как\s+(я|мы)\s+помн\w+)`
- `(тогда\s+(в|у)\s+(нашей|у\s+нас))`
- `(когда\s+(я|мы)\s+(был\w+|жил\w+))`
- `(помн\w+,\s+в\s+\w+\s+(я|мы))`
- `(в\s+(советск\w+|те)\s+\w*\s*время)`
- `(по\s+(тем|советск\w+|нашим)\s+\w*\s*временам)`
- `(у\s+нас\s+в\s+(семь\w+|доме|городе|посёлке))`

### Anti-patterns (NOT personal-historical)

- Просто discourse marker «Татьяна вспоминает» (это discourse_markers, не personal-historical)
- Просто historical_note «В 1933 году был голод» (это objective historical_notes)
- «Как X вспоминает...» (это discourse_markers attribution)

Personal-historical = **combination** «personal pronoun (я/мы/у нас)» + «temporal/era marker (тогда/в 90-е/в советское время)» + **event/context**.
```

### 2. Validator `validate_personal_historical_voice`

В `pipeline_utils.py`:

```python
def validate_personal_historical_voice(
    book: dict,
    config: dict | None = None,
    pin_list_anchors: list[dict] | None = None,
) -> dict:
    """Detect personal-historical voice patterns в narrative chapters.

    Returns:
    {
        "markers_found_per_chapter": {"ch_02": N, "ch_03": M, "ch_04": K, "epilogue": L},
        "thresholds": {"ch_02": 3, "ch_03": 2, "ch_04": 1, "epilogue": 0},
        "issues": [
            {
                "type": "personal_historical_voice",
                "category": "below_threshold",
                "chapter_id": "ch_02",
                "found": 0,
                "expected": 3,
                "severity": "warning",
                "suggestion": "Добавить ≥3 personal-historical voice markers в ch_02. Examples: «как я помню, в [период]...» / «тогда у нас в семье...». Использовать narrator_voice_anchors из pin-list.",
                "reason": "Class 18 — personal-historical voice missing"
            }
        ],
        "errors_count": 0,
        "warnings_count": N,
    }
    """
    thresholds = (config or {}).get("thresholds_per_chapter", {
        "ch_02": 3,
        "ch_03": 2,
        "ch_04": 1,
        "epilogue": 0,  # epilogue без personal voice OK
    })

    # Combined regex patterns (generic)
    patterns = [
        r'\bкак\s+(я|мы)\s+помн\w+',
        r'\bтогда\s+(в|у)\s+(нашей|нас|у\s+нас)',
        r'\bкогда\s+(я|мы)\s+(был\w+|жил\w+|росл\w+)',
        r'\bпомн\w+,\s+(в|на)\s+\w+\s+(я|мы)',
        r'\bв\s+(советск\w+|те)\s+\w*\s*време\w*',
        r'\bпо\s+(тем|советск\w+|нашим)\s+\w*\s*времен\w*',
        r'\bу\s+нас\s+в\s+(семь\w+|доме|городе|посёлке|институте)',
    ]

    counts = {}
    for ch in book.get("chapters", []):
        chid = ch.get("id")
        if chid == "ch_01":
            continue
        content = ch.get("content", "") or ""
        total = 0
        for pat in patterns:
            total += len(re.findall(pat, content, re.IGNORECASE))
        counts[chid] = total

    issues = []
    for chid, expected in thresholds.items():
        found = counts.get(chid, 0)
        if found < expected:
            issues.append({
                "type": "personal_historical_voice",
                "category": "below_threshold",
                "chapter_id": chid,
                "found": found,
                "expected": expected,
                "severity": "warning",
                "suggestion": (
                    f"Добавить ≥{expected - found} personal-historical voice "
                    f"markers в {chid}. Использовать narrator_voice_anchors из "
                    f"pin-list. Examples: 'как [rapporteur] помнит, в [период]...', "
                    f"'тогда у нас в семье...', 'когда [rapporteur] был ребёнком, ...'"
                ),
                "reason": "Class 18 personal-historical voice — рассказчик помещает личную память в исторический контекст",
            })

    return {
        "markers_found_per_chapter": counts,
        "thresholds": thresholds,
        "issues": issues,
        "errors_count": sum(1 for i in issues if i["severity"] == "error"),
        "warnings_count": sum(1 for i in issues if i["severity"] == "warning"),
    }
```

### 3. Конфиг

`personal_historical_voice_config.json`:
```json
{
  "thresholds_per_chapter": {
    "ch_02": 3,
    "ch_03": 2,
    "ch_04": 1,
    "epilogue": 0
  },
  "version": "v1",
  "_notes": "Defaults для 90-минутного интервью с 2 rapporteurs (parent + grandchild). Calibrate per subject если интервью только с одним rapporteur."
}
```

### 4. Integration в Stage 3 pipeline

В `scripts/test_stage3.py` либо в orchestrator (049f): запустить `validate_personal_historical_voice` после Stage 2 → output saved as `karakulina_v64_personal_historical_voice_check.json`.

### 5. Snapshot tests

`tests/test_personal_historical_voice.py`:

```python
def test_personal_historical_voice_kak_pomnyu():
    """Pattern 'как я помню, в [период]...' — match."""
    sentence = "Как я помню, в 90-е цены росли каждую неделю."
    flags = validate_personal_historical_voice_for_sentence(sentence)
    assert flags  # any match


def test_personal_historical_voice_togda_u_nas():
    """Pattern 'тогда у нас в семье...' — match."""
    sentence = "Тогда у нас в семье было принято собираться по воскресеньям."
    flags = validate_personal_historical_voice_for_sentence(sentence)
    assert flags


def test_personal_historical_voice_kogda_ya_byl():
    """Pattern 'когда я был ребёнком...' — match."""
    sentence = "Когда я была ребёнком, бабушка часто рассказывала про войну."
    flags = validate_personal_historical_voice_for_sentence(sentence)
    assert flags


def test_personal_historical_voice_negative_discourse_marker():
    """Pure discourse marker без personal-historical — НЕ count."""
    sentence = "Татьяна вспоминает, что бабушка готовила пирожки."
    flags = validate_personal_historical_voice_for_sentence(sentence)
    assert not flags


def test_personal_historical_voice_negative_objective_historical():
    """Objective historical_note — НЕ count."""
    sentence = "В 1933 году в Кировоградской области был голод."
    flags = validate_personal_historical_voice_for_sentence(sentence)
    assert not flags


def test_threshold_below():
    """ch_02 с 1 marker, threshold 3 → flag below_threshold."""
    book = {
        "chapters": [
            {"id": "ch_02", "content": "Как я помню, в 1962 году семья переехала."},
            {"id": "ch_03", "content": "..."},
        ]
    }
    result = validate_personal_historical_voice(book)
    assert result["markers_found_per_chapter"]["ch_02"] == 1
    issues = [i for i in result["issues"] if i["chapter_id"] == "ch_02"]
    assert issues
    assert issues[0]["found"] == 1
    assert issues[0]["expected"] == 3
```

### 6. GW v2.23 awareness (НЕ новое правило, лишь использование)

ПРАВИЛО 13 (task 049e) обрабатывает revision_hints от любого validator, в т.ч. `personal_historical_voice`. **НЕ нужно** новое GW правило — orchestrator передаст hint, GW переписывает.

**Однако** в input GW v2.23 (при revision pass) добавляется ссылка на `pin_list.narrator_voice_anchors` секцию — GW может использовать examples для guidance. Это extension input format (через orchestrator 049f), не GW prompt change.

---

## Risk и mitigation

**Risk A: Validator over-triggers — flag every chapter.**

**Mitigation:**
- Thresholds calibrated на v62a (где было 10+10 historical_notes — но personal-historical отдельно)
- Initial thresholds (3/2/1/0) консервативные — easy to adjust
- Severity warning, не error → GW при revision может skip если context legitимно не позволяет

**Risk B: Patterns могут не покрыть subject-specific voice phrases.**

**Mitigation:**
- Generic patterns (как я помню / тогда у нас / в советское время) — universal
- Subject-specific anchors в pin-list — examples для GW guidance, не для validator detection
- v65 backlog: subject-specific patterns в `narrator_voice_anchors_<subject>.json`

**Risk C: Validator counts false-positive matches (e.g. random «у нас» в narrative).**

**Mitigation:**
- Patterns demand combination personal pronoun + temporal/era marker (не одиночные «у нас»)
- Calibration на v63 артефактах перед commit
- Negative snapshot tests

---

## Ограничения

- [ ] Generic patterns + subject-specific anchors per subject
- [ ] Idempotent
- [ ] Severity warning (revision pass решает)
- [ ] Thresholds per chapter (defaults conservative)
- [ ] Snapshot tests mandatory: 4+ positive + 2 negative
- [ ] Scope = narrative chapters (НЕ ch_01)
- [ ] Anti-overlap with discourse_markers + historical_notes (different classes)

---

## Dev Review

**Статус:** ожидает

**[TECH]** — pre-answer от Опуса:
- Pin-list extension `known_episodes_karakulina.md` — секция `## narrator_voice_anchors` (либо рядом с existing discourse markers anchors)
- Validator function в `pipeline_utils.py`
- Generic patterns first; subject-specific (если есть в pin-list) — usage examples для GW input, validator focuses on generic
- Anti-overlap с discourse_markers (pure attribution) и historical_notes (objective): personal-historical = combination personal + temporal

**[PRODUCT]** — нет (Никитин 3c sign-off)

**Сложность:** `s` (1-3 ч — pin-list edit + validator + 6 snapshot tests)
**Риск:** `low` (warning severity + generic patterns; calibration на v63)

---

## Verified-on-run v64

**Cursor:** [после v64] — `personal_historical_voice_check.json` + `karakulina_v64_text_FULL.md`
**Опус:** независимо проверит:
- ✅ markers_found_per_chapter — все ≥ threshold (либо warnings для нижних)
- ✅ После revision pass narrative содержит personal-historical voice phrases
- ✅ Snapshot tests PASS (6+)
- ✅ False positives для discourse_markers / historical_notes — 0

---

## История

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-18 | `new` | Опус |
