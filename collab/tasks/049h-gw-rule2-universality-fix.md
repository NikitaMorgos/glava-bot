# Задача 049h: GW v2.23 → v2.24 ПРАВИЛО 2 universality fix — replace hardcoded characteristic words на placeholders + wire pin-list input

**Статус:** `new`
**Номер:** 049h
**Автор:** Опус
**Дата создания:** 2026-05-19
**Тип:** `промпт` GW (bug fix existing rule, не новое правило)
**Sprint:** v65 (combined с task 049e-2 в v2.24)
**Связано:** task 044i-2 verification report; Никитин feedback v64 «выковыривал — это правило универсальное или каракулинское?»; Правило 4 архитектора (universality построчно)

---

## Контекст

Verification (см. task 044i-2): GW v2.23 ПРАВИЛО 2 содержит **захардкоженные** Каракулино-specific examples в финальном тексте:

**Шапка (строка 58):**
```
Правило 2 усилено: characteristic words из transcript ОБЯЗАТЕЛЬНЫ
(минимум 3 в нарративе) — закрывает потерю «выковыривал»,
«зажиточные ребята», «движуха», «зарубиться на пустом месте», «рукастый»
```

**Тело правила (строки 190-202):**
```
Примеры characteristic words для Каракулиной (из TR1):
  • «выковыривал» — про солдата...
  • «зарубиться на пустом месте» — про характер...
  • «зажиточные ребята» — про переезд в Химинститут...
  • «движуха» (бабушкина) — ...
  • «рукастый» — про Дмитрия и внука Никиту...
```

Это **violation Правила 4 архитектора** (universality построчно). Тот же класс что v60 «Татьяна 1956 Твери» в ПРАВИЛЕ 9 — recurring моя ошибка (см. memory `architect_universality_check.md`).

Pin-list имеет секцию `characteristic_words` per subject (правильно), код generic читает оттуда. Но **GW prompt обходит mechanism** — LLM читает захардкоженные examples в Правиле 2 раньше чем смотрит input.

---

## Pre-sprint checklist

- [x] Stocktake актуален
- [x] Critical reading — v64 narrative + v2.23 prompt + pin-list + code проверены (task 044i-2)
- [x] Universality построчно — этот task **сам** про universality fix
- [x] Защита подключена — да, GW читает characteristic_words из input per subject
- [x] Прогон раздельный — combined с 049e-2 в v2.24 (оба — bug fixes existing rules, не новые правила)
- [x] Класс — universality recurring моя ошибка (procedural защита грep команда введена)
- [x] Скрипт-first — но GW prompt change нужен (input wire alone не достаточно если в prompt захардкожены приоритетные examples)

---

## Спек

### 1. GW v2.24 Правило 2 — заменить examples на placeholders

**Шапка v2.24** (изменение vs v2.23):
```
### Изменения v2.24: 2 bug fixes existing правил (НЕ новые правила):
### 1. ПРАВИЛО 13 schema fix — rule13_revision_applied как list of dicts (task 049e-2)
### 2. ПРАВИЛО 2 universality fix — replace hardcoded characteristic words examples
###    на placeholders + wire pin-list characteristic_words в input (task 049h).
###    Closing recurring моей ошибки universality (v60, v63, v64).
```

**Тело ПРАВИЛА 2** (изменение):

```
══════════════════════════════════════════════════════════════════
ПРАВИЛО 2 (v2.24) — CHARACTERISTIC WORDS ИЗ TRANSCRIPT
══════════════════════════════════════════════════════════════════

Голос рассказчика теряется если автор переходит на «литературный»
стиль. Текст становится анонимной биографией без голоса конкретной
семьи.

ПРАВИЛО:
1. Открой transcript (cleaned_transcript) **либо** input
   `pin_list.characteristic_words` (если передан — это источник правды
   per subject, NOT examples из этого промпта).
2. Если `pin_list.characteristic_words` присутствует — использовать **его**
   как список характерных слов для этого subject. Минимум 3 из списка
   ОБЯЗАТЕЛЬНО употребить в нарративе.
3. Если `pin_list.characteristic_words` отсутствует — найди **5
   characteristic words/colloquialisms** в transcript: нестандартные,
   колоритные, бытовые слова или выражения, которые рассказчик
   употребил **спонтанно**, не из литературной речи.
4. Из 3+ обязательных — НЕ превращай их в символы и НЕ объясняй их
   в скобках — просто **пиши их**, как часть голоса.

GENERIC EXAMPLES PATTERN (применимо к любому subject):

✅ ХОРОШО (любой subject):
  Source quote: «[характерное слово] её через [место]»
  Narrative: «[характерное слово рассказчика, как помнит источник]» —
  слово сохранено в нарративе, attribution к рассказчику явная.

❌ ПЛОХО (любой subject):
  Source quote содержит [характерное слово]
  Narrative использует литературный синоним → теряется голос.

Признаки нарушения (любой subject):
- В transcript есть [колоритное слово], в книге — стандартный
  литературный синоним
- В transcript есть [колоритное выражение], в книге — обобщённый
  концепт без слова

НЕ путать с правилом «не символизировать»: говорить про слово
нельзя (это символизация). Просто **употреблять** его — нужно.

══════════════════════════════════════════════════════════════════

INPUT FORMAT для characteristic_words (per subject):

В user message GW Stage 2 (либо в pin_list_events block) передаётся
секция:

```yaml
characteristic_words:
  - word: "[слово 1 из transcript]"
    context: "[короткое описание контекста: про что/кого]"
    source_quote: "[фрагмент transcript содержащий слово]"
  - word: "[слово 2]"
    context: "..."
    source_quote: "..."
  # минимум 5 элементов, GW использует ≥3
```

Этот список приходит **per subject** из `known_episodes_<subject>.md`
секции «Голос рассказчика — characteristic words». GW promp **НЕ**
содержит конкретных слов — только generic шаблон.

══════════════════════════════════════════════════════════════════
```

### 2. Wire `pin_list.characteristic_words` в Stage 2 input

В `scripts/test_stage2_pipeline.py` (либо актуальном runner):
- Pin-list parser уже умеет читать `characteristic_words` секцию (verified в `pipeline_utils.py`)
- При формировании Stage 2 user message — **добавить** characteristic_words как отдельный блок (либо в PIN_LIST_EVENTS context)
- GW обязан читать input, не захардкоженный prompt list

```python
def build_gw_stage2_input(fact_map, pin_list, ...):
    characteristic_words = pin_list.get("characteristic_words", [])
    return {
        ...
        "pin_list_events": [...],
        "characteristic_words": characteristic_words,  # NEW: explicit input
        ...
    }
```

### 3. Тесты — universality verification

`tests/test_gw_rule2_universality.py`:

```python
def test_rule2_no_hardcoded_subject_specific_words():
    """GW v2.24 prompt не содержит Каракулино-specific characteristic words в финальном тексте Правила 2."""
    prompt_text = read_file("prompts/03_ghostwriter_v2.24.md")
    # Извлечь body of ПРАВИЛО 2 (между его заголовком и заголовком ПРАВИЛА 3)
    rule2_body = extract_rule_body(prompt_text, rule_num=2)
    # Проверить отсутствие hardcoded subject-specific слов
    BANNED_HARDCODED = [
        "выковырив", "зарубить", "зажиточн", "движуха", "рукаст", "бабульно",
        "Каракулин", "Татьян", "Валентин", "Химинститут", "Молдави", "1946 год"
    ]
    for banned in BANNED_HARDCODED:
        assert banned not in rule2_body.lower(), (
            f"GW Правило 2 содержит hardcoded Каракулино-specific '{banned}'. "
            f"Должно быть через placeholder либо из input."
        )


def test_rule2_uses_input_characteristic_words():
    """GW v2.24 prompt явно ссылается на pin_list.characteristic_words как input."""
    prompt_text = read_file("prompts/03_ghostwriter_v2.24.md")
    rule2_body = extract_rule_body(prompt_text, rule_num=2)
    assert "characteristic_words" in rule2_body, "Правило 2 должно ссылаться на input characteristic_words"
    assert "pin_list" in rule2_body, "Правило 2 должно ссылаться на pin_list как источник"


def test_stage2_input_wires_characteristic_words():
    """Stage 2 builder передаёт characteristic_words из pin-list в GW input."""
    pin_list = {"characteristic_words": [{"word": "тестслово", "context": "test", "source_quote": "test quote"}]}
    fact_map = {...}
    input_dict = build_gw_stage2_input(fact_map, pin_list)
    assert "characteristic_words" in input_dict
    assert input_dict["characteristic_words"][0]["word"] == "тестслово"


def test_grep_command_zero_matches():
    """Procedural защита — grep команда из memory architect_universality_check возвращает 0."""
    import subprocess
    result = subprocess.run(
        ["grep", "-cni", "Каракулин\\|Татьян\\|Валентин\\|Химинститут\\|выковырив\\|зарубить\\|зажиточн\\|движуха\\|рукаст\\|бабульно\\|Молдави\\|1946 год\\|две недели",
         "prompts/03_ghostwriter_v2.24.md"],
        capture_output=True, text=True
    )
    # Skip header lines (version history) — count только тело prompt
    # Допустимо в шапке version notes (~10 строк header). Остальное должно быть 0.
    body_matches = count_matches_in_body(result.stdout)
    assert body_matches == 0, f"GW v2.24 prompt body содержит Каракулино-specific terms: {body_matches}"
```

### 4. Pin-list verify — characteristic_words секция актуальна

Открыть `known_episodes_karakulina.md` v6/v7 — убедиться что секция «Голос рассказчика — characteristic words» **актуальна** и **полная** (6 слов: выковыривал, зарубиться на пустом месте, зажиточные ребята, движуха, рукастый, бабульно).

Если в v6 секция уже соответствует — в v7 не trog (содержание готово, нужна только wiring через input).

---

## Universality check (КРИТИЧНО)

- [x] Промпт без конкретики Каракулиной — все examples через placeholders `[характерное слово]`, `[место]` (вместо «выковыривал», «через КПП в Германию» итд)
- [x] Subject-specific конкретика — в `pin_list.characteristic_words` per subject (правильно)
- [x] Algorithm generic — для любого subject; GW reading input
- [x] Subject-replacement test ПОСТРОЧНО — grep по Каракулино-specific terms = 0 в финальном Правиле 2

**Grep команда** (выполнить ВРУЧНУЮ перед commit'ом v2.24):
```bash
grep -in "Каракулин\|Татьян\|Валентин\|Химинститут\|выковырив\|зарубить\|зажиточн\|движуха\|рукаст\|бабульно\|Молдави\|1946 год\|две недели" prompts/03_ghostwriter_v2.24.md
```

Допустимы matches **только** в шапке (version history секция «Изменения v2.X»). В теле правил — 0 matches.

---

## Ограничения

- [ ] Один промпт-bump v2.23 → v2.24 (combined с 049e-2)
- [ ] Все examples в Правиле 2 — через placeholders
- [ ] Input wire через Stage 2 builder
- [ ] Pin-list characteristic_words — source of truth per subject
- [ ] Snapshot тесты + grep команда
- [ ] Procedural защита grep в pre-sprint checklist (введено 2026-05-19)
- [ ] К v66+ — апply ту же universality проверку к **всем** существующим правилам GW (не только 2 и 13) — backlog

---

## Dev Review

**Статус:** ожидает

**[TECH]** — pre-answer от Опуса:
- Combined с 049e-2 в одном файле `prompts/03_ghostwriter_v2.24.md`
- Stage 2 builder extend для passing characteristic_words
- Snapshot tests + grep test обязательны
- К v66: апply universality scan ко всем existing GW rules (не только 2/13)

**[PRODUCT]** — нет

**Сложность:** `s` (1-3 ч — prompt edit + input wire + tests)
**Риск:** `low` (bug fix existing rule + input format extension, не новая логика)

---

## Verified-on-run v65

**Cursor:** [после v65]
**Опус:** независимо:
- Прочитает `prompts/03_ghostwriter_v2.24.md` Правило 2 — проверит placeholders, не Каракулино-specific
- Запустит grep команду — должно быть 0 matches в body
- Проверит Stage 2 input format — characteristic_words присутствует
- В narrative v65 — слова из pin_list.characteristic_words использованы (≥3)

---

## История

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-19 | `new` | Опус |
