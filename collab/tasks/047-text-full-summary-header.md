# Задача 047: Сводка объёма + структуры в начале каждого text_FULL.md

**Статус:** `new`
**Номер:** 047
**Автор:** Опус (роль архитектор+продакт)
**Дата создания:** 2026-05-17
**Тип:** `cco-скрипт` (build_gate1_full_text.py)
**Batch:** 2-fix
**Связано:** Никитин запрос v58 review — «давай каждую версию такой сводкой сопровождать, так легче сопоставить»

---

## Контекст

Сейчас `build_gate1_full_text.py` (Этап 1) генерирует `karakulina_v<N>_text_FULL.md` с сводкой:
```
**Глав:** 5
**Объём текста:** 17 411 chars
**По главам:** ch_01 — 2877 ...
**Callouts:** 7
**Historical notes:** 3
**bio_data.family:** 19 записей
**bio_data.awards:** 8 наград
**ch_01 timeline:** 0 этапов
```

Никитин запрос: **расширить сводку** так чтобы можно было **сравнить версии** между собой.

---

## Спек

### Что нужно изменить

**Расширенная сводка** в начале `text_FULL.md`:

```markdown
# Сводка по книге

## Объём
- **Total chars:** 17 411 (target 14-18K)
- **ch_01:** 2 877 chars
- **ch_02:** 8 006 chars
- **ch_03:** 4 105 chars
- **ch_04:** 1 478 chars
- **epilogue:** 945 chars

## Структура
- **Глав:** 5 (ch_01..ch_04 + epilogue)
- **ch_02 подсекций:** 11 (## headers)
- **ch_03 подсекций:** 7
- **ch_04 эпизодов:** 8 (отдельные абзацы)

## Bio_data (паспортичка)
- **family:** 16 записей
- **awards:** 8 наград
- **timeline периодов:** 7 (в content, JSON array пуст ⚠️)

## Дополнительные элементы
- **Callouts:** 7
- **Historical notes (field):** 0 ⚠️
- **Historical notes (inline `***...***`):** 3

## Pin-list coverage
- **Episodes full:** 13 / 35 (из known_episodes_<subject>.md)
- **Episodes partial:** 8 / 35
- **Episodes skipped:** 14 / 35
- **Bytovye full:** 4 / 20
- **Characteristic words used:** 5 / 6

## Diff vs baseline
- **Baseline:** v56
- **Regressions (был full → стал partial/skipped):** 2 (огурцы, счётчик)
- **Improvements (был skipped → стал full):** 6 (разные отцы, Полина забрала, ДК Синтетик, почерк, дороговизна, операция желудок)

## Quality flags (если есть отчёты в том же ts)
- ⚠️ Epilogue stop phrases: 2 errors, 1 warning
- ⚠️ Narrative stop phrases: 3 warnings («семейные узы», «определила всю жизнь», «расстроить любую мать»)
- ✅ ASR normalize: 0 находок старых форм
- ✅ Bio_data integrity: filtered_non_family=2
- ⚠️ Timeline anchors: 0/7 found (JSON array пуст, см. task 045b)
- ❌ Chronological consistency: 1 error («1946 сидела с детьми» при том что Валерий 1948)
- ⚠️ Discourse markers: count=12 (baseline v57=18, -33%)

---

[далее идёт собственно текст глав как сейчас]
```

### Реализация

**1. `scripts/build_gate1_full_text.py`** — расширить:
- Принимает дополнительные пути к отчётам (опционально): `--pin-coverage-json`, `--style-checks-json`, `--episode-diff-json`, `--chronology-json`, `--discourse-markers-json`, `--timeline-anchors-json`, `--bio-integrity-json`
- Если отчёт есть — читает + рендерит в сводке
- Если нет — пропускает (graceful degradation)
- Auto-detect отчётов в той же директории по prefix `<run_id>_`

**2. Подсчёт структуры из book:**
- `ch_02 подсекций`: regex `^##\s+` в content
- `ch_04 эпизодов`: count paragraphs (`\n\n`-separated) или `\n\n[А-Я]` блоков
- ch_01 timeline периодов: regex `^\*\*\d{4}` в content (markdown) + length из JSON array

**3. Сравнение с baseline** (если есть `pipeline_config.json`):
- Прочитать `pin_list_diff_baseline_version: "v56"`
- Если baseline артефакты есть → подсчитать regressions/improvements
- Если нет → пропустить раздел

### Какой результат ожидается

В v59 `text_FULL.md` начинается с **детальной сводки**, которую можно прямо скопировать в comparison table v57 vs v58 vs v59.

### Как проверить

1. **Unit-тесты** `tests/test_text_full_summary.py`:
   - Все секции присутствуют
   - Числа корректно вычисляются из book + reports
   - Graceful degradation если отчёт missing

2. **Integration** на v58c:
   - Перегенерировать `text_FULL.md` с новой сводкой
   - Сравнить с моим manual анализом v58c — должно совпадать

3. **Verified-on-run** v59:
   - Открыть `karakulina_v59_text_FULL.md` начало — все секции сводки заполнены

---

## Ограничения

- [ ] Generic для любого subject (нет hardcoded Каракулиной)
- [ ] Graceful degradation: если отчёт missing — пропустить раздел, не fail
- [ ] Idempotent

---

## Dev Review

**Статус:** ожидает

**[TECH]** — пред-резолв: auto-detect отчётов по timestamp в имени файла; если нет — отдельные `--*-json` parameters.

**[PRODUCT]** — нет (структура сводки моя предложение; Никита может расширить).

**Сложность:** `s` (1-3 ч)
**Риск:** `low`

---

## История

| Дата | Статус | Кто |
|---|---|---|
| 2026-05-17 | `new` | Опус |
