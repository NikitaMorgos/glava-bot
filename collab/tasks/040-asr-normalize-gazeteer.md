# Задача 040: Post-FC нормализация ASR-искажений топонимов (gazeteer per subject)

**Статус:** `new`
**Номер:** 040
**Автор:** Опус
**Дата создания:** 2026-05-17
**Тип:** `cco-скрипт`
**Batch:** 1 (скриптовый, низкий risk)
**Связано:** [architecture-stocktake-2026-05-17.md](../context/architecture-stocktake-2026-05-17.md) Класс 4 «ASR транслитерация топонимов»

---

## Контекст

В v56 Fact Checker iter3 вернул **FAIL** с 5 ошибками, 3 из которых — низкоуровневая ASR-транслитерация топонимов, которую GW не исправляет за 3 итерации FC:

| FC error | Что в тексте | Что должно быть | Источник правды |
|---|---|---|---|
| err_001 critical | «Новомергородский район» (ch_01) | «Новомиргородский район» | fact_map.subject.birth_place |
| err_002 critical | «Новомергородского района» (ch_02) | «Новомиргородского района» | event_001 |
| err_003 major | «Керсанов» (ch_02) | «Кирсанов» | event_024 location |

Дополнительно из feedback Никиты:
- **«улица Капашвара» → «площадь Капошвара»** (в v56 ch_01 и ch_02). ASR + неверный type (улица vs площадь).

**Корень:** ASR (AssemblyAI / Whisper) делает ошибки на русских топонимах. Ошибки идут в transcript → Fact Extractor → fact_map → book. FC детектит, но **сам GW не способен надёжно исправить** на iter2/iter3 (за 3 итерации FC errors остались).

Это **Класс 4 stocktake** — universally применимо. Решение чисто скриптовое: gazeteer-словарь канонических топонимов + post-FC normalize step.

---

## Спек

### Что нужно изменить / создать

**1. Gazeteer per subject** — новый файл `collab/context/gazeteer_<subject>.json`:

```json
{
  "subject_id": "karakulina",
  "version": "v1",
  "topo_corrections": {
    "Новомергородский": "Новомиргородский",
    "Новомергородского": "Новомиргородского",
    "Керсанов": "Кирсанов",
    "Капашвара": "Капошвара",
    "Сапоново": "Сафроново",
    "Кишкунхалаш": "Кишкунхалаш"
  },
  "topo_types": {
    "Капошвара": "площадь",
    "Тверская": "улица",
    "Советская": "улица"
  }
}
```

Расширяется per subject. Для Каракулиной — на основе FC v56 ошибок + feedback Никиты.

**2. Функция `normalize_topo_via_gazeteer(text: str, gazeteer: dict) -> tuple[str, list]`** в `pipeline_utils.py`:
- На вход — текст + gazeteer
- На выход — нормализованный текст + список применённых замен (для diagnostics)
- Замена word-boundary aware (не делать `Сафронов` → `Сафронов` если в тексте `Сафроново`; чинить именно `Сапоново → Сафроново`)
- Регистр сохраняется (если в тексте «новомергородского» с маленькой — заменить на «новомиргородского»)

**3. Pipeline integration** в `scripts/test_stage3.py` (или соответствующий runner):
- После Fact Checker и Literary Editor, **до** Proofreader / Quality Gates:
  - Применить `normalize_topo_via_gazeteer` к `book_FINAL_stage3.json` (рекурсивно по всем text-полям: paragraphs.text, callouts.text, historical_notes.text, bio_data.* values)
  - Сохранить отчёт `<run>_topo_normalize_report_<ts>.json` с списком замен

**4. Также применить к fact_map** в Stage 1:
- В `enrich_timeline_with_subject_age` (task 042) **или отдельно**: применить `normalize_topo_via_gazeteer` к fact_map после merge, до Completeness Auditor.
- Чтобы fact_map был чист с самого начала, а не только в финальном book.

### Какой результат ожидается

В v57 `karakulina_v57_text_FULL.md`:
- ✅ «Новомиргородский район» (не «Новомергородский»)
- ✅ «Кирсанов» (не «Керсанов»)
- ✅ «площадь Капошвара» (не «улица Капашвара»)

Fact Checker iter3 v57 → 0 critical (или ≤1, если останется person_019 Марфа — это task 039 scope).

### Как проверить

1. **Unit-тесты** `tests/test_topo_normalize.py`:
   - Базовая замена: «Новомергородский район» → «Новомиргородский район»
   - Case preserving: «новомергородского» → «новомиргородского», «Новомергородского» → «Новомиргородского»
   - Word boundary: «Сапоново-ское» (если такое появится) — выбрать политику (default: только exact word + склонения через простой суффикс-match)
   - Idempotent: вторая нормализация ничего не меняет
   - Type correction: если в gazeteer.topo_types есть «Капошвара: площадь» — найти в тексте «улица Капошвара» / «улицу Капошвара» / «на Капошвара» и нормализовать к «площадь Капошвара» — **это сложнее, обсуждаемо**, см. Dev Review флаг ниже

2. **Integration-тест** на v56 артефактах:
   - Загрузить `karakulina_v56_book_FINAL_stage3.json`
   - Применить normalize
   - Сохранить нормализованный artifact
   - Проверить что 3/5 FC ошибок v56 «исчезли» (синтетически переdebug через тот же FC промпт на новом артефакте — или просто grep на канонические формы)

3. **Verified-on-run**:
   - После v57: открыть `karakulina_v57_text_FULL.md`, grep «Новомер», «Керсан», «Капашвара» — должно быть **0 находок**.
   - Открыть `<run>_topo_normalize_report.json`, проверить список замен — соответствует ожидаемому.

---

## Ограничения

- [ ] Не менять промпт Fact Extractor / Cleaner — это **пост-процессинг**, не пред-обработка
- [ ] Не нормализовать `source_quote` поля (это **прямые цитаты ASR**, должны оставаться как есть для трейсабилити; нормализация только в нарративных полях)
- [ ] Idempotent: повторное применение не должно ничего ломать
- [ ] Не делать generic Russian geo normalize без gazeteer (риск false-positive на legit имена)

---

## Dev Review

**Статус:** ожидает

**[TECH]** — потенциальные флаги:
- [ ] Type correction («улица → площадь Капошвара») сложнее чем просто string replace — нужна grammar-aware замена. Возможные альтернативы: (a) генерировать regex per type («(улица|улицы|улицу|на улице) Капошвара» → «площадь Капошвара» + согласовать предлог), (b) оставить только string replace топонима, type correction backlog
- [ ] Не нормализовать `source_quote` — нужна явная whitelist полей, на которые применяется normalize

**[PRODUCT]** — нет

**Оценка сложности:** `s` (1-3 ч; type correction может вытянуть до `m`)
**Оценка риска:** `low` для базового normalize, `medium` для type correction (false positives)

---

## Dev Review Response

**Статус:** ожидает

**Pre-answer от Опуса (можно использовать для self-resolve [TECH]):**
- Базовый normalize (string replace + case preserve) — реализуем сейчас.
- Type correction («улица → площадь») — **отдельной волной**, после v57. В Batch 1 — только string replace.
- Whitelist полей: применять normalize к `paragraphs[].text`, `callouts[].text`, `historical_notes[].text`, `bio_data` values (кроме `source_quote` если оно где-то есть). НЕ применять к `*.source_quote`, `*.evidence`, `*.transcript_quote` — это сохраняемые ASR-цитаты.

---

## Реализация

**Статус:** ожидает

---

## Verified-on-run

**Cursor:** [после v57]

**Claude:** [Опус проверит grep по «Новомер|Керсан|Капашвара» — должно быть 0]

---

## История статусов

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-17 | `new` | Опус |
