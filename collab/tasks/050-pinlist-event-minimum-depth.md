# Задача 050: Pin-list event minimum depth (Класс 14 — новый)

**Статус:** `new`
**Номер:** 050
**Автор:** Опус (роль архитектор+продакт)
**Дата создания:** 2026-05-17
**Тип:** `cco-скрипт` + минор `промпт` GW v2.20
**Batch:** 2-fix
**Связано:** stocktake 2026-05-17 — **новый Класс 14** (pin-list event minimum depth); Никитин feedback v58c про шубу «без комментария выглядит странно»

---

## Контекст

**Класс 14 — Pin-list event minimum depth violation** (universal class):

Pin-list даёт **выбор** какие эпизоды развернуть, но **не глубину**. GW v2.19 может включить эпизод **одним предложением** — формально это `coverage: full`, но **бесполезно** для книги-биографии.

**Пример v58c (Каракулина — проявление класса):** шуба→пианино для дочери. v56 имел 3 предложения с цитатой «Шуба была, конечно, тяжеловата, но шикарная». v58 свёл к 1 предложению: «В 1962 году Валентина продала шикарную немецкую шубу, привезённую из Венгрии, чтобы купить дочери Татьяне пианино.» Формально pin-list эпизод присутствует, **но информационно беднее**.

**Универсально для всех subjects:** в любой биографии есть **ключевые эпизоды** которые должны быть развёрнуты, не свёрнуты. Pin-list per subject указывает minimum depth.

---

## Спек

### Что нужно изменить / создать

**1. Расширить schema pin-list** в `known_episodes_<subject>.md` — добавить колонку `min_sentences` (или новый раздел):

```markdown
| # | episode_id | Эпизод | Год | TR | Маркеры | min_sentences | В v_N? |
|---|---|---|---|---|---|---|---|
| 24 | ep_024 | Огурцы из Молдавии | ~1980-е | TR2 | `огурц`, ... | 3 | ⚠️ |
```

`min_sentences` — целое число, минимум для развёрнутого эпизода в нарративе.

**Default по умолчанию** (если колонка пуста):
- Хронологические эпизоды (`episodes`): `min_sentences=3`
- Бытовые (`bytovye`): `min_sentences=2`
- Traits (`traits`): `min_sentences=1` (могут быть в callout)

**Subject-extensible:** редактор pin-list может выставить `min_sentences=5` для особо важных эпизодов.

**2. Функция `validate_pin_list_depth(book, pin_list) -> report`** в `pipeline_utils.py`:

```python
def validate_pin_list_depth(book, pin_list) -> dict:
    """
    Класс 14: для каждого pin-list event с coverage='full' проверить
    что параграф с маркерами имеет >= min_sentences.
    
    Returns:
        {
          "depth_issues": [
            {
              "episode_id": "ep_024",
              "title": "Огурцы из Молдавии",
              "min_required": 3,
              "actual_sentences": 1,
              "chapter_id": "ch_04",
              "paragraph_snippet": "...",
              "severity": "error"
            }
          ],
          "errors_count": N,
          "warnings_count": M
        }
    """
```

**Алгоритм:**

1. Для каждого pin-list episode из `validate_pin_list_coverage` с `coverage` ∈ {full, partial}:
   - Найти **paragraph** в `book.chapters[].paragraphs[]` где markers нашлись (плотность совпадений ≥ N/min(len(markers), 5))
   - Подсчитать предложения в этом paragraph через regex `[.!?]\s+(?=[А-ЯA-Z])` + последнее sentence
   - Сравнить с `min_sentences` из pin-list
   - Если `actual < min_required`:
     - Если `coverage="full"` — severity=`error` (формально full, но depth violation)
     - Если `coverage="partial"` — severity=`warning` (уже частичное, depth ожидаемо ниже)

**3. Минорный патч GW v2.20** (мерж в существующий промпт от task 049):

```
### ПРАВИЛО 8 — МИНИМАЛЬНАЯ ГЛУБИНА PIN-LIST EVENTS (universal)

Для каждого события из `pin_list.episodes`:
- ОБЯЗАТЕЛЬНО развернуть в нарративе минимум на `min_sentences` предложений (из pin-list схемы)
- Default: 3 предложения для хронологических, 2 для бытовых, 1 для traits
- В предложениях — конкретика: что/когда/кто/почему/как; не общая фраза
- Если в источнике (TR + fact_map) недостаточно материала для `min_sentences` — указать в revision_log как `low_source_material: <episode_id>`, не выдумывать

Цель: pin-list event = развёрнутый эпизод, не упоминание. «Продала шубу для покупки пианино» — это 1 предложение и недостаточно; должны быть детали (какая шуба, откуда, реакция семьи, год, цитата из источника).
```

Этот промпт universal — нет конкретики subject.

**4. Интеграция в Stage 3 runner**:
- После `validate_pin_list_coverage` (existing task 041) → `validate_pin_list_depth`
- Severity error → flag для verified-on-run (не блокирует pipeline в Batch 2-fix; hard-fail в Batch 3)
- Отчёт `<run>_pin_list_depth.json`

### Какой результат ожидается

В v59 для Каракулиной:
- Шуба→пианино: 3+ предложения (с деталями: какая, откуда, для чего, реакция семьи)
- Огурцы из Молдавии: 4+ предложения (чемодан, испортились, реакция Татьяны, конфликт с Маргось)
- Счётчик 1977: 3+ предложения (повод, конкретика, последствия)

В v59 `<run>_pin_list_depth.json`:
- depth_issues errors: 0 для key episodes (огурцы, шуба, счётчик)

Универсально: для Корольковой — её ключевые эпизоды развёрнуты на 3+ предложения, согласно `known_episodes_korolkova.md` колонке `min_sentences`.

### Как проверить

1. **Unit-тесты** `tests/test_pin_list_depth.py`:
   - Episode min=3 + 1 sentence в book → error
   - Episode min=3 + 3 sentences → PASS
   - Coverage=partial + min=3 + 2 sentences → warning (не error)
   - Sentence count корректен (учёт многоточий, кавычек)
   - Idempotent

2. **Integration** на v58c:
   - Шуба (min=3) + 1 sentence → flag error
   - Счётчик / огурцы (skipped в v58) → не проверяются (coverage=skipped)

3. **Verified-on-run** v59:
   - `<run>_pin_list_depth.json` errors=0 для key episodes
   - text_FULL.md — шуба эпизод имеет ≥3 предложения с конкретикой

---

## Ограничения

- [ ] Generic for any subject — `min_sentences` per episode в subject-specific pin-list
- [ ] Default fallback (если колонка пуста) — generic правило по типу
- [ ] Sentence counter — robust для русского (точка не как разделитель в инициалах «В.И.»)
- [ ] Idempotent
- [ ] Промпт GW v2.20 ПРАВИЛО 8 — universal, без subject-specific примеров

---

## Universality check

- [x] Промпт ПРАВИЛО 8 — без конкретики subject (нет имён, событий из транскриптов; ссылка на `pin_list.episodes` generic)
- [x] Subject-specific — в `known_episodes_<subject>.md` колонка `min_sentences` per episode (опционально, fallback на default)
- [x] Алгоритм — generic, использует pin-list parsed structure + sentence counter
- [x] Subject-replacement test: для Корольковой `known_episodes_korolkova.md` с `min_sentences` → spec работает без правок ✅

---

## Dev Review

**Статус:** ожидает

**[TECH]** — пред-резолв:
- Sentence counter для русского — regex `[.!?]+\s+(?=[А-ЯA-Z])` + special cases (инициалы «В.И.», «И.А.»; кавычки «...»). Возможны edge cases — приемлемо.
- Default `min_sentences` для каждого типа — generic, без subject-config.
- Pin-list parser (existing task 041) расширяется — добавляет колонку `min_sentences` если есть, default иначе.

**[PRODUCT]** — нет.

**Сложность:** `s` (1-3 ч)
**Риск:** `low` (warning + error reporting, не auto-fix)

---

## История

| Дата | Статус | Кто |
|---|---|---|
| 2026-05-17 | `new` | Опус |
