# Задача 042: Алгоритмическое обогащение fact_map.timeline возрастом субъекта

**Статус:** `completed`
**Номер:** 042
**Автор:** Опус
**Дата создания:** 2026-05-17
**Тип:** `cco-скрипт`
**Batch:** 1 (скриптовый, низкий risk)
**Связано:** [architecture-stocktake-2026-05-17.md](../context/architecture-stocktake-2026-05-17.md) Класс 8 «Age markers underused»

---

## Контекст

Из feedback Никиты по v56: ему **нравятся** возрастные маркеры в нарративе — «в 40 лет начала работать», «в 85 лет душилась французскими духами». Эти маркеры помогают читателям-потомкам **соотнести себя с персонажем** (когда у бабушки родился первый ребёнок, во сколько лет вышла на пенсию, сколько лет посвятила работе).

В v56 такие маркеры есть **выборочно**, в v55 их **было больше**. GW не вычисляет возраст автоматически — это стохастика промпта.

**Корень:** GW получает в input даты событий (`year: 1962`), но не возраст субъекта (`subject_age: 41`). Если бы возраст был **в input**, GW использовал бы его последовательнее.

Это **Класс 8 stocktake** — universally применимо к любому subject. Чисто скриптовое решение, риск нулевой.

---

## Спек

### Что нужно изменить / создать

**Новый шаг enrichment между Fact Extractor и Completeness Auditor** (Stage 1):

1. Функция `enrich_timeline_with_subject_age(fact_map: dict) -> dict` в `pipeline_utils.py`:
   - Читает `fact_map.subject.birth_year` (для Каракулиной: 1920)
   - Для каждого event в `fact_map.timeline`:
     - Если `event.date.year` есть → добавить поле `subject_age = year - birth_year`
     - Если `event.date.precision == "decade"` (например 1960) → `subject_age` = середина декады − birth_year (для 1960 → 1965 − 1920 = 45)
     - Если `year` отсутствует → пропустить (поле не добавляется)
   - Не модифицировать другие поля event

2. Применить функцию в `scripts/test_stage1_karakulina_full.py`:
   - После split-extract merge, до Completeness Auditor
   - Сохранить enriched fact_map как `fact_map_full_enriched_<timestamp>.json` (диагностика)

3. Промпт Ghostwriter: **НЕ меняется**. GW получает enriched fact_map как есть; уже умеет использовать поля event. Дополнительно — короткое упоминание в GW input schema (handler если есть) что `subject_age` — возраст субъекта на момент события, можно использовать в нарративе.

### Какой результат ожидается

В `fact_map_full_<timestamp>.json` каждый event с известным годом имеет поле `subject_age`:

```json
{
  "id": "event_007",
  "date": {"year": 1962, "month": null, "precision": "approximate"},
  "title": "Переезд в Химинститут",
  "subject_age": 41,
  ...
}
```

В v57 нарративе ожидаем **больше** возрастных маркеров типа «в 41 год переехала в Химинститут», «в 25 лет потеряла мать» (1933 − 1908 для матери? нет, для Валентины 1933−1920=13). И — нарратив не должен **противоречить** возрасту (GW v56 написал «тринадцатилетняя Валентина попала в детский дом» — корректно для 1933, можно проверить).

### Как проверить

1. **Unit-тесты** `tests/test_subject_age_enrichment.py`:
   - Базовый случай: year=1962, birth=1920 → age=42 (или 41 при month<12? решить: по году, без месяца, age = year − birth_year, для day-level точности — отдельно если нужно)
   - Decade case: precision="decade", year=1960 → age=45 (середина декады)
   - Missing year: event без `date.year` → пропускается, поле не добавлено
   - Future-proof: subject без birth_year → функция возвращает unchanged + warning в log

2. **Integration-тест** на v56 fact_map: запустить enrichment на сохранённой `karakulina_v56_fact_map_full_*.json`, проверить что появилось поле `subject_age` для всех events с known year.

3. **Verified-on-run**: после v57 прогона — открыть `fact_map_v57_full_enriched.json`, проверить что 80%+ events имеют `subject_age`. Открыть `karakulina_v57_text_FULL.md` — посчитать количество возрастных маркеров (типа «в N лет», «N-летний»), должно быть ≥ v56.

---

## Ограничения

- [ ] Не менять формат остальных полей event (`date`, `title`, `description`, `participants`, ...)
- [ ] Не менять промпт Ghostwriter и Completeness Auditor — только enrichment
- [ ] Не вычислять возраст для events с `precision: "unknown"` или отсутствующим year
- [ ] Функция идемпотентна: повторный вызов на уже enriched fact_map не должен ломать

---

## Dev Review

**Статус:** `approved`

**[TECH]** — флагов нет. Чисто скриптовая функция, не меняет формат (добавляет только новое поле `subject_age`), не downstream-impact на агентов (GW игнорирует unknown fields). Идемпотентность реализована через `if "subject_age" in event: continue`. Decade = mid-decade (year+5): for 1960 → 1965 − 1920 = 45.

**[PRODUCT]** — флагов нет. Универсальное обогащение, не специфично к Каракулиной.

**Оценка сложности:** `xs` (< 1 ч) — реализовано.
**Оценка риска:** `low`

---

## Dev Review Response

**Статус:** N/A — [PRODUCT] флагов не было.

---

## Реализация

**Статус:** `completed` (2026-05-17)

Реализовано в `pipeline_utils.py::enrich_timeline_with_subject_age`. Вызывается в `scripts/test_stage1_karakulina_full.py` между merge и CA (шаг 2.5). Сохраняет `karakulina_fact_map_enriched_{ts}.json` для диагностики. Тесты: `tests/test_subject_age_enrichment.py` (13 тестов, 100% PASS).

---

## Verified-on-run

**Cursor:**

[После v57]

**Claude:**

[Опус откроет fact_map_v57_full_enriched + text_FULL + сосчитает возрастные маркеры]

---

## История статусов

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-17 | `new` | Опус |
