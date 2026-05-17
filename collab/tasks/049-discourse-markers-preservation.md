# Задача 049: Discourse markers preservation (Класс 13 — новый)

**Статус:** `new`
**Номер:** 049
**Автор:** Опус (роль архитектор+продакт)
**Дата создания:** 2026-05-17
**Тип:** `cco-скрипт` (метрика) + минор `промпт` GW v2.20 ПРАВИЛО 6
**Batch:** 2-fix
**Связано:** stocktake 2026-05-17 — **новый Класс 13** (discourse markers regression); Никитин feedback v58 «цитат Татьяны стало заметно меньше»

---

## Контекст

v57 имел много **discourse markers рассказчика** в нарративе:
- «как вспоминает дочь»
- «по словам Татьяны»
- «вспоминает Татьяна»
- «отмечает дочь»

В v58 их **стало заметно меньше** (Никитин feedback). Это **снижает теплоту и человечность** текста — Никите явно важен голос конкретного рассказчика.

**Класс 13 — Discourse markers regression**: GW при сжатии нарратива (когда нет якорей pin-list) сокращает discourse markers как «лишние слова».

Универсально — каждая биография имеет своего **rapporteur** (рассказчика), discourse markers должны сохраняться.

---

## Спек

### Что нужно изменить / создать

**1. Функция `validate_discourse_markers(book, fact_map, config) -> report`** в `pipeline_utils.py`:

```python
def validate_discourse_markers(book, fact_map, config) -> dict:
    """
    Класс 13: подсчёт discourse markers в нарративе.
    
    Returns:
        {
          "markers_found": {
            "ch_02": 8,
            "ch_03": 4,
            "ch_04": 2
          },
          "thresholds": {
            "ch_02": 8,  # минимум для биографической главы
            "ch_03": 5,  # портрет
            "ch_04": 3   # интересные факты
          },
          "issues": [
            {"chapter_id": "ch_03", "type": "below_threshold", "found": 4, "expected": 5}
          ],
          "errors_count": N,
          "warnings_count": M
        }
    """
```

**Алгоритм:**

1. Получить rapporteur'а из fact_map.persons (relation_to_subject="дочь"/"сын"/"внук"/"внучка"/"племянник" — основной рассказчик)
2. Generic discourse marker patterns с подстановкой `[rapporteur_name]`:
   - `как вспоминает [rapporteur_name]\|дочь\|сын\|внук`
   - `по словам [rapporteur_name]`
   - `[rapporteur_name] отмеча\w+\|вспомина\w+\|говор\w+\|рассказ\w+`
   - `как пиш\w+ [rapporteur_name]`
   - `утверждает [rapporteur_name]`
3. Подсчёт в каждой главе нарратива
4. Сравнение с threshold (subject-specific или generic):
   - ch_02 (биография): мин 8
   - ch_03 (портрет): мин 5
   - ch_04 (факты): мин 3
   - epilogue: 0 ожидается (нарратив автора, не рассказчика)

**2. Config `discourse_markers_<subject>.json`** (subject-specific rapporteurs + thresholds):

```json
{
  "subject_id": "karakulina",
  "rapporteurs": [
    {"name": "Татьяна", "aliases": ["дочь", "Татьяна Каракулина"], "primary": true},
    {"name": "Никита", "aliases": ["внук"], "secondary": true}
  ],
  "thresholds": {
    "ch_02": 8,
    "ch_03": 5,
    "ch_04": 3
  },
  "baseline_version": "v57",
  "baseline_counts": {"ch_02": 12, "ch_03": 6, "ch_04": 4}
}
```

**3. ПРАВИЛО 6 в GW v2.20 (universal)**:

```
### ПРАВИЛО 6 — DISCOURSE MARKERS (голос рассказчика)

В fact_map.subject.rapporteurs указаны люди, со слов которых записано интервью.
Сохраняй упоминания рассказчика в нарративе главами:
- «как вспоминает [рассказчик]», «по словам [рассказчика]»
- «[рассказчик] отмечает / вспоминает / рассказывает / говорит»
- Минимум:
  - ch_02 (биография): **8 упоминаний** на главу
  - ch_03 (портрет): **5 упоминаний** на главу
  - ch_04 (интересные факты): **3 упоминания** на главу
  - epilogue: **0** (это нарратив автора)

Это создаёт ощущение живой памяти семьи, а не отчёта алгоритма.
ИСКЛЮЧЕНИЕ: если в fact_map.subject.rapporteurs пусто (анкета без рассказчика) — правило не применимо.
```

**4. Интеграция в Stage 3**:
- После всех других validators → `validate_discourse_markers`
- Severity `warning` (не блокирует pipeline)

### Какой результат ожидается

В v59 `<run>_discourse_markers.json`:
- ch_02 ≥ 8 markers
- ch_03 ≥ 5
- ch_04 ≥ 3
- 0 errors

### Как проверить

1. **Unit-тесты** `tests/test_discourse_markers.py`:
   - Текст с 10 markers → above threshold ch_02 PASS
   - Текст с 3 markers ch_02 → flag below_threshold
   - Patterns ловят разные формулировки
   - Rapporteurs aliases работают

2. **Integration** на v57 + v58c:
   - v57 ch_02 → ~12 markers (baseline)
   - v58c ch_02 → ~8 markers (примерно, нужно посчитать)
   - Diff: regression flagged если v58 < baseline * 0.7

3. **Verified-on-run** v59:
   - Открыть discourse_markers.json — ch_02 ≥ 8
   - В text_FULL.md grep вручную «вспоминает дочь\|по словам Татьяны\|отмечает дочь» → ≥8 hits в ch_02

---

## Ограничения

- [ ] Generic for any subject — rapporteurs из конфига per subject
- [ ] ПРАВИЛО 6 промпта — без Каракулиноспецифики, через placeholder
- [ ] False positives возможны (например «вспоминает Валентина» — это не rapporteur). Распознавать subject vs rapporteur
- [ ] Idempotent

---

## Dev Review

**Статус:** ожидает

**[TECH]** — пред-резолв:
- Distinguish между «[субъект] вспоминает» (это не rapporteur marker — субъект рассказывает о себе?) и «[rapporteur] вспоминает (про субъекта)»:
  - Если subject — это интервьюер сам (редкий случай) — rapporteur может быть тот же. Обычно нет.
  - Patterns с конкретными именами rapporteurs (из config) — точнее.
- Baseline counts хранятся в config; обновляются после approved PASS version.

**[PRODUCT]** — нет.

**Сложность:** `s` (1-3 ч)
**Риск:** `low` (warning-level метрика, не block)

---

## История

| Дата | Статус | Кто |
|---|---|---|
| 2026-05-17 | `new` | Опус |
