# Задача 049e: GW v2.22 → v2.23 ПРАВИЛО 13 — Revision compliance (выполнить revision_hints из validators)

**Статус:** `new`
**Номер:** 049e
**Автор:** Опус (роль архитектор+продакт)
**Дата создания:** 2026-05-18
**Тип:** `промпт` GW (prompt-bump, 1 правило per bump per Правило 6)
**Sprint:** v64
**Связано:** stocktake-2026-05-18-v60-v63.md (архитектурный диагноз «validators detect, GW игнорирует»); task 049f (revision_hints orchestrator); все validators (chronology / pin_list_depth / discourse / style_checks / narrative_stop / anti_facts / новые 043h+046e)

---

## Контекст

**Архитектурный диагноз (см. stocktake):**

5 sprints v60-v63 — мы лечим конкретные patterns в GW prompt + расширяем validators. **Проблема:** validators **detect** violations, но **GW не получает** их обратно для исправления. Class 12 «Германия+дети» в v63 был **flagged как error** в `chronology_check.json`, но в narrative **остался как есть**. Validators висят в воздухе.

**Решение Никиты 2026-05-18 (развилка 1b):** revision loop через GW.

Архитектурный сдвиг: после первого Stage 2 (GW draft) и всех validators → **второй Stage 2 pass** где GW получает `revision_hints` (list flagged sentences + reason + suggestion) и обязан переписать flagged места.

Это **закрывает класс** «GW игнорирует flag» — единым архитектурным ходом, не точечно. Pattern эволюция Class 11 («по электричеству» → «в принципе, особенно по») больше не требует обновления regex — validator flag → GW переписывает любую форму.

---

## Universality check (КРИТИЧНО — Правило 4 архитектора)

- [x] Промпт без конкретики subject — ПРАВИЛО 13 работает с placeholder'ами `[flagged_sentence]`, `[validator_category]`, `[suggestion]`
- [x] Subject-specific конкретика — НИГДЕ в правиле; subject content приходит через input revision_hints (per-run)
- [x] Алгоритм generic — revision compliance применима к любому subject
- [x] **Subject-replacement test построчно** — см. секцию ниже

**Trap warning:** в финальном тексте ПРАВИЛА 13 не должно быть «Каракулина / Татьяна / огурцы / Молдавия / 1946». Все examples — generic placeholders (lesson v60 sprint).

---

## Спек

### 1. Файл prompts/03_ghostwriter_v2.23.md

Новая версия GW prompt = копия `v2.22.md` + ПРАВИЛО 13 в конце секции ПРАВИЛА.

**Шапка обновляется:**
```
## Версия: v2.23 (2026-05-18, Opus, task 049e, v64 sprint)
### Изменения v2.23: 1 новое правило, архитектурный сдвиг:
### • НОВОЕ ПРАВИЛО 13: REVISION COMPLIANCE — при revision pass с
###   revision_hints из validators переписать flagged sentences.
###   Архитектурный ход закрывающий класс «validators detect, GW игнорирует».
###
### v2.23 = v2.22 + ПРАВИЛО 13 (per Правило 6 — одно правило per bump).
###
### Триггер: 5 sprints v60-v63 — recurring patterns (Class 1/6/11/12) возвращаются
### в новых формах, потому что pattern в validator закрывает regex-форму,
### не семантику. Revision loop через LLM = семантический fix.
```

**Тело правила** (добавляется в раздел ПРАВИЛА после ПРАВИЛА 12):

```
══════════════════════════════════════════════════════════════════
ПРАВИЛО 13 — REVISION COMPLIANCE (v2.23)
══════════════════════════════════════════════════════════════════

Это правило применяется при call_type="revision" когда input содержит
поле revision_hints (отдельно от existing revision_scope.affected_chapters).

revision_hints — list объектов, каждый описывает одно нарушение, найденное
scripted validators после первого Stage 2 pass:

  revision_hints: [
    {
      "hint_id": "h_001",
      "validator": "chronology_check" | "pin_list_depth" | "style_checks"
                 | "narrative_stop_phrases" | "anti_facts" | "discourse_markers"
                 | "personal_historical_voice" | "narrative_truism" | ...,
      "category": "<machine-readable subclass>",
      "chapter_id": "ch_02" | "ch_03" | "ch_04" | "epilogue",
      "severity": "error" | "warning",
      "snippet": "<flagged sentence или paragraph fragment>",
      "reason": "<why это нарушение, machine-generated>",
      "suggestion": "<conkretная инструкция как переписать>",
      "must_apply": true | false  // true для severity=error
    },
    ...
  ]

ТВОЯ ЗАДАЧА при revision pass:

A. **must_apply: true (severity=error)** — ОБЯЗАН выполнить:
   - Найти sentence/paragraph в current_book matching snippet
   - Переписать **только эти sentences** (не всю главу)
   - Применить suggestion дословно (если конкретная) ИЛИ семантически
     (если общая, типа «удалить причинно-следственную связку которой нет
     в источнике»)
   - Никаких других изменений в этой главе **не делать**

B. **must_apply: false (severity=warning)** — приоритет на качество, не
   на форму:
   - Если suggestion улучшает текст без потери факта — применить
   - Если suggestion ломает связность / удалить factual content —
     можно проигнорировать, отметив в writing_notes "rule13_skipped_warning"

C. **Output requirements:**
   - В `out_book.writing_notes` добавить:
     ```
     rule13_revision_applied: [
       {"hint_id": "h_001", "action": "rewritten" | "deleted" | "skipped",
        "reason": "<если skipped — почему>"}
     ]
     ```
   - Если ни один error-level hint не выполнен — флаг `revision_failed: true`
     с пояснением (это сигнал archtechtural breakage, не нормальное состояние)

⛔ НЕЛЬЗЯ при revision compliance:
- Игнорировать error-level hint без записи "skipped" + reason
- Переписывать sentences which не в revision_hints (это нарушение
  ПРАВИЛА 0 REVISION SCOPE LOCK)
- Использовать hint как повод переписать всю главу

✅ МОЖНО:
- Удалить целое предложение если suggestion = "delete_sentence"
- Объединить два sentences если оба flagged + suggestion позволяет
- Добавить connecting phrase если удаление нарушает читаемость
  (минимально, не больше 5-10 слов)

══════════════════════════════════════════════════════════════════

EXAMPLES (placeholder-based, generic for any subject):

[Субъект] = биографируемая персона
[Период] = временной период из fact_map.timeline
[Имя_близкого] = родственник или другой person из fact_map.persons
[YYYY] = конкретный год
[X], [Y], [Z] = generic content placeholders

✅ Hint выполнен (Class 12 chronology):
   Input hint:
     validator: "chronology_check"
     category: "person_mentioned_before_birth"
     snippet: "В [Период] [Субъект] сидела с детьми"
     reason: "first_child birth_year = [YYYY_first_child],
             [Период] ends before [YYYY_first_child]"
     suggestion: "Удалить упоминание детей в этом контексте ИЛИ
                  заменить на 'занималась домом' / 'вела хозяйство'"

   Output после revision:
     "В [Период] [Субъект] не работала — занималась домом."
     writing_notes.rule13_revision_applied:
       [{"hint_id": "h_xxx", "action": "rewritten",
         "diff": "сидела с детьми → занималась домом"}]

✅ Hint выполнен (Class 17 narrative truism):
   Input hint:
     validator: "narrative_truism"
     category: "obvious_responsibility_constatation"
     snippet: "В те годы [Имя_близкого] брал на себя огромную
              ответственность — [перечисление], всё ложилось на её плечи"
     reason: "констатация очевидного — читатель сам понимает что
             забравший ребёнка из детдома берёт ответственность"
     suggestion: "delete_sentence"

   Output после revision: предложение удалено.
     writing_notes.rule13_revision_applied:
       [{"hint_id": "h_xxx", "action": "deleted",
         "reason": "applied delete_sentence suggestion"}]

✅ Hint выполнен (Class 1 causal confabulation, recurring):
   Input hint:
     validator: "narrative_stop_phrases"
     category: "speciality_defined_life_recurring"
     snippet: "дали ей [профессия] — специальность, которая определила
              всю её дальнейшую жизнь в [сфера]"
     reason: "causal confabulation — нет в transcripts; recurring v62a→v63"
     suggestion: "удалить часть после тире (causal claim);
                  оставить факт обучения"

   Output после revision:
     "[Субъект] получила специальность [профессия]."
     writing_notes.rule13_revision_applied:
       [{"hint_id": "h_xxx", "action": "rewritten",
         "diff": "удалена causal claim"}]

❌ Hint проигнорирован (anti-pattern):
   Output: текст не изменён, writing_notes пуст.
   → revision_failed: true, прогон возвращается в Опус для review.

══════════════════════════════════════════════════════════════════

PROOF OF ATTENTION — required at revision pass output:

В `writing_notes` обязательно:
- "rule13_revision_applied": list (см. выше)
- "rule13_hints_received": count input hints
- "rule13_errors_applied": count выполненных error-level hints
- "rule13_warnings_applied": count выполненных warning-level hints
- "rule13_revision_failed": true если есть error-level hint без apply/skip
  + reason

Эти поля проверяет orchestrator (task 049f). Если revision_failed=true →
прогон останавливается до Опусова review.

══════════════════════════════════════════════════════════════════
```

### 2. pipeline_config.json update

```json
"ghostwriter": {
    ...
    "prompt_file": "03_ghostwriter_v2.23.md",
    "_notes": "v2.23 (2026-05-18, task 049e, v64 sprint): добавлено ПРАВИЛО 13 REVISION COMPLIANCE — при revision pass с revision_hints из validators GW обязан переписать flagged sentences. Архитектурный ход закрывающий класс «validators detect, GW игнорирует» (5 sprints v60-v63 recurring). Per Правило 6 — одно правило per bump."
}
```

### 3. Subject-replacement test (Правило 4 архитектора)

**Каждая строка ПРАВИЛА 13 проверена** — ни одного:
- «Каракулина / Татьяна / Валентина» (использованы `[Субъект]`, `[Имя_близкого]`)
- «огурцы / Молдавия / Германия 1946» (использованы `[X]`, `[Период]`, `[YYYY]`)
- «акушерство / медицина» (использованы `[профессия]`, `[сфера]`)

**Mental test:** замена `[Субъект]` → «Иван Дмитриев», `[Период]` → «1953-1956», `[Имя_близкого]` → «сестра Анна» → правило **работает без правок** ✅.

Subject-specific values приходят через input `revision_hints` (per-run, генерируются orchestrator'ом 049f из fact_map + validators output).

### 4. Тесты

`tests/test_gw_v223_rule13.py` (новый):
- Schema test: GW output при revision pass содержит `writing_notes.rule13_revision_applied` (list), `rule13_hints_received` (int), `rule13_errors_applied` (int).
- Negative: если `revision_hints=[]` → GW не делает ничего, output = input book unchanged (ПРАВИЛО 0 SCOPE LOCK не нарушается).
- Mock: тестируется только schema output, не реальное переписывание (это integration test).

---

## Risk и mitigation

**Risk A: Revision loop pass превращается в hallucination.** GW при revision может «улучшить» больше чем flagged.

**Mitigation:**
- ПРАВИЛО 13 явно: «только flagged sentences, ПРАВИЛО 0 SCOPE LOCK активно»
- Validator orchestrator (049f) сравнивает diff между draft и revision: если изменились sentences НЕ из revision_hints → flag warning
- writing_notes.rule13_revision_applied — audit trail

**Risk B: Bundle с ПРАВИЛОМ 12 — слишком много новых правил в коротком цикле.**

**Mitigation:**
- v2.22 (ПРАВИЛО 12) уже battle-tested в v63 (хоть не сработал полностью)
- ПРАВИЛО 13 не conflict с 12 — оно **дополняет** (применяется только при revision pass, ПРАВИЛО 12 — при первом draft)
- Per Правило 6 — это **одно** новое правило

**Risk C: GW не понимает hint suggestion (особенно если suggestion общая «удалить causal claim»).**

**Mitigation:**
- Examples в ПРАВИЛЕ 13 показывают как интерпретировать общие suggestion
- Validator orchestrator (049f) генерирует **конкретные** suggestion где возможно (`delete_sentence` / `replace: X → Y` / семантический hint)

**Risk D: revision_failed=true каскадирует — orchestrator застревает.**

**Mitigation:**
- Max 1 revision pass v64. Если revision_failed → stop, Опус review
- Backlog v65: max 2 revision passes если single недостаточен

---

## Ограничения

- [ ] Один промпт-bump v2.22 → v2.23 (одно правило)
- [ ] Per Правило 6: НЕ bundle с другими новыми правилами
- [ ] Universality построчно — placeholders, не subject-specific examples
- [ ] Subject-replacement test пройден
- [ ] Proof-of-attention в output (writing_notes.rule13_*) обязательно
- [ ] ПРАВИЛО 13 совместимо с ПРАВИЛОМ 0 (SCOPE LOCK) — flagged-only переписывается
- [ ] Max 1 revision pass в v64 (avoid loop forever)

---

## Dev Review

**Статус:** ожидает

**[TECH]** — pre-answer от Опуса:
- Файл: `prompts/03_ghostwriter_v2.23.md` (новый, копия v2.22 + ПРАВИЛО 13). НЕ переписывать v2.22 — оставить archived.
- `pipeline_config.json.ghostwriter.prompt_file` → `"03_ghostwriter_v2.23.md"`.
- `_notes` обновить.
- Output schema GW при revision pass — добавить required `writing_notes.rule13_revision_applied` field (validator orchestrator task 049f читает это).

**[PRODUCT]** — нет (архитектурный ход, Никита sign-off на развилке 1b).

**Сложность:** `s` (1-3 ч — копия v2.22 + добавление текста ПРАВИЛА 13 + schema test)
**Риск:** `medium` (новое архитектурное правило; mitigation через ПРАВИЛО 0 SCOPE LOCK + diff audit в 049f + max 1 revision pass)

---

## Verified-on-run v64

**Cursor:** [после v64 прогона] — отчёт по revision_hints выполнению (counts + diff)
**Опус:** независимо откроет `karakulina_v64_text_FULL.md` + `writing_notes.rule13_*`, сравнит draft vs revision diff, проверит что:
- ✅ error-level hints выполнены (chronology, narrative_truism, Class 1 recurring, ...)
- ✅ ПРАВИЛО 0 SCOPE LOCK не нарушено (только flagged места изменены)
- ✅ revision_failed=false

---

## История

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-18 | `new` | Опус |
