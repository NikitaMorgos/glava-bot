# Задача 043e-2: Epilogue overcrowded quotes detection (>4 cited phrases в одном абзаце)

**Статус:** `new`
**Номер:** 043e-2
**Автор:** Опус (роль архитектор+продакт)
**Дата создания:** 2026-05-18
**Тип:** `cco-скрипт`
**Sprint:** v63
**Связано:** Class 6 epilogue пафос; task 043 / 043b / 043c / 043g (narrative stop phrases); v62a epilogue review — 4 cited phrases в одном абзаце

---

## Контекст

В v62a epilogue (последний абзац, 1 параграф, 785 chars):

```
Голод 1933 года, война, послевоенные переезды, работа, семья — каждый этап
требовал стойкости и умения приспосабливаться к обстоятельствам. Она
воспитала двоих детей, дождалась внуков, проработала в медицине более
тридцати лет. Была награждена боевыми орденами и трудовыми медалями,
получила звание «Ударник коммунистического труда», дважды была на доске
почёта. Валентина оставила после себя семью, которая помнит её «рукастость»
и трудолюбие, умение «выковыривать» выход из любой ситуации, традицию
«посидеть на дорожку» и веру в то, что любовь выражается не словами, а
делом. Её жизнь была типичной для поколения, прошедшего через войну и
восстановление страны. Но в этой типичности была своя уникальность —
стойкость «оловянного солдатика», который не сгибается под ударами судьбы.
```

В одном абзаце 5 cited phrases:
1. «Ударник коммунистического труда» — звание
2. «рукастость»
3. «выковыривать»
4. «посидеть на дорожку»
5. «оловянного солдатика»

Никитин feedback (#7): epilogue **перегружен** цитатами в одном абзаце. Читается как gallop из characteristic words рассказчика. Хорошо когда они **распределены** по тексту, плохо когда все в одном пафосном финале.

**Класс:** Class 6 (epilogue пафос) — конкретный pattern «density of cited phrases».

---

## Universality check

- [x] Промпт — n/a, scripted
- [x] Subject-specific — n/a (threshold generic)
- [x] Алгоритм generic — count cited substrings («X», `«...»`, «...»)в paragraph, threshold = N
- [x] Subject-replacement test — для любого subject epilogue: если GW сгружает 5+ characteristic words в один абзац → flag ✅

**Trap warning:** конкретные «рукастость», «выковыривать» — симптомы. Класс = «density of quotes per paragraph в epilogue > threshold». Spec строится на классе.

---

## Спек

### Что нужно изменить

### 1. Новая функция `validate_epilogue_quote_density`

В `pipeline_utils.py`:

```python
def validate_epilogue_quote_density(
    book: dict,
    config: dict | None = None,
) -> list[dict]:
    """Flag paragraphs in epilogue with > threshold cited phrases.

    Cited phrase = substring enclosed in « » (Russian guillemets)
    OR " " (straight quotes).

    Default threshold: > 4 (i.e., 5+ phrases = error).
    """
    threshold = (config or {}).get("max_quotes_per_paragraph", 4)
    findings = []
    epilogue = book.get("chapters", {}).get("epilogue", {})
    content = epilogue.get("content", "") or ""
    for idx, para in enumerate(content.split("\n\n")):
        # Russian guillemets « ... » + straight quotes "..."
        # Don't count italic markers _..._ or bold **...**
        quotes = re.findall(r'«[^»]+»', para)
        # Also match straight quotes
        quotes_straight = re.findall(r'"[^"]+"', para)
        total = len(quotes) + len(quotes_straight)
        if total > threshold:
            findings.append({
                "type": "epilogue_quote_density",
                "paragraph_index": idx,
                "quote_count": total,
                "threshold": threshold,
                "quotes": quotes + quotes_straight,
                "severity": "warning",
                "suggestion": (
                    f"Распределите цитаты по тексту — {total} цитат в одном "
                    "абзаце создаёт перегруз; характерные слова рассказчика "
                    "лучше работают разбросанными по ch_02/ch_03/ch_04, а в "
                    "epilogue — короче и спокойнее."
                ),
            })
    return findings
```

### 2. Конфиг (optional)

`narrative_stop_phrases.json` или новый `epilogue_density_config.json`:

```json
{
  "epilogue_quote_density": {
    "max_quotes_per_paragraph": 4,
    "severity": "warning",
    "scope": ["epilogue"]
  }
}
```

Если конфиг отсутствует — defaults используются (threshold=4).

### 3. Integration в Stage 3 pipeline

В `scripts/test_stage3.py` добавить вызов `validate_epilogue_quote_density` после style_checks; результат записать в `<run>_epilogue_density_check.json` или объединить с `style_checks.json` (предпочтительный вариант — extension к existing style_checks).

### 4. (Опционально) GW prompt-bump на v63 NOT — отложить

GW prompt можно дополнить hint «epilogue максимум 4 cited phrases per paragraph», но **per Правилу 6** — 1 правило per bump. v63 уже добавляет ПРАВИЛО 12 (depth+voice+chars). Этот аспект — backlog v64+ если scripted defense недостаточен.

### Какой результат ожидается

В v63:
- `epilogue_density_check.json` ИЛИ `style_checks.json` содержит `epilogue_quote_density` warning для финального абзаца epilogue
- Никита/Опус видит warning, может попросить GW revision pass

### Как проверить

1. **Unit-тесты** `tests/test_epilogue_quote_density.py`:
   - Paragraph с 5 cited phrases → warning
   - Paragraph с 4 cited phrases → no flag (boundary)
   - Paragraph с 3 cited phrases → no flag
   - Paragraph с 0 cited phrases → no flag
   - Idempotent
   - Negative: cited phrases в ch_02/ch_03/ch_04 — НЕ flag (scope=epilogue only)

2. **Integration** на v62a epilogue:
   - 5 cited phrases (Ударник, рукастость, выковыривать, посидеть на дорожку, оловянный солдатик) → 1 warning

3. **Verified-on-run** v63:
   - Открыть `karakulina_v63_style_checks.json` — содержит warning epilogue_quote_density либо такого warning нет потому что epilogue переписан / меньше density

---

## Ограничения

- [ ] **Warning only** (не enforce auto-delete) — epilogue density — стилистический баланс, не factual error
- [ ] **Scope = epilogue** только (в narrative chapters cited phrases уместны)
- [ ] **Generic threshold** — настраивается через config
- [ ] **Idempotent**
- [ ] Quote markers: Russian guillemets « » primary, straight " " secondary; not italics/bold

---

## Dev Review

**Статус:** ожидает

**[TECH]** — pre-answer от Опуса:
- Quote detection: regex `«[^»]+»` + `"[^"]+"`. Edge case — overlapping quotes (вложенные) редки, ignore.
- Threshold 4 — calibrate на v62a + v59 epilogue (v59 epilogue ~676 chars, fewer quotes); если v59 PASS на threshold=4 — keep
- Severity warning, не error — epilogue density субъективен

**[PRODUCT]** — нет (Никитин feedback явный)

**Сложность:** `xs` (<1 ч)
**Риск:** `low`

---

## Verified-on-run

**Cursor:** [после v63]
**Опус:** независимо посмотрит epilogue last paragraph и quote count

---

## История

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-18 | `new` | Опус |
