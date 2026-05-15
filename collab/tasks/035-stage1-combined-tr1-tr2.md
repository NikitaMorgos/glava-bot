# Задача 035: Stage 1 на combined TR1+TR2 теряет TR2-эпизоды

**Статус:** `in-progress` (v55 done, 2/4 эпизодов)
**Номер:** 035
**Автор:** Опус
**Дата создания:** 2026-05-15 (после Дашиного feedback'а v54)
**Тип:** `cco-скрипт` + `промпт` (Stage 1: Fact Extractor / Completeness Auditor)
**Связано:** task 016 (Name Normalizer), task 027 (bio_data.family completeness), `known_episodes_karakulina.md` (pin-list source of truth)

---

## Контекст

v54 — первый прогон Каракулины на **combined TR1+TR2** транскриптах через все защиты волн 1.1-1.3.3 + Этап 1 (GW v2.17, LE v3.1, preserve). По чек-листу обнаружено что **9 эпизодов потеряны** относительно known_episodes_karakulina.md:

Из TR2 (52K chars, не извлечены):
- ❌ Огурцы из Молдавии 1990 (`огурц`: 3 раза в TR2, **0** в fact_map_v54)
- ❌ Счётчик 1977 — конфликт с зятем (`счётчик`: 2 раза в TR2, **0** в fact_map_v54)
- ❌ Нинвана Полсачева — авторитет врача (`Нинван`: 2 раза в TR2, **0**)
- ❌ Шарлотка — кулинария (`шарлотк`: 1 раз в TR2, **0**)
- ❌ «Французская бабушка» сравнение (TR2, 1 упоминание)

Из TR1 (20K chars, не извлечены):
- ❌ Соседка тётя Маша / нелюбовь к грибам-ягодам
- ❌ Дороговизна в 90-е («Процена постоянно ворчала»)
- ❌ Характерное слово «выковыривал» (про солдата с документами)

**Сравнение по версиям:**

| Прогон | TR | Огурцы в book? |
|---|---|---|
| v51 | TR2 only (Stage 2 fragment) | ✅ ЕСТЬ |
| v53b | TR2 only (full Stage 1→4) | ✅ ЕСТЬ |
| **v54** | **TR1+TR2 combined** | ❌ ОТСУТСТВУЕТ |

На отдельном TR2 эпизод извлекался корректно. На combined TR1+TR2 — теряется. Это **новый класс регрессии** не покрытый волнами 1.1-1.3.3.

## Гипотезы

### Гипотеза A — Fact Extractor отсёк как дубли с TR1

Когда транскрипты объединяются в один cleaned_transcript, Fact Extractor может посчитать некоторые TR2-only эпизоды дубликатами TR1 (например «конфликт с Маргош в TR1 общими словами + конкретный счётчик в TR2» → FE решил что счётчик дубль).

**Проверка:** запустить FE отдельно на TR1 и отдельно на TR2, посмотреть какие events извлекаются. Сравнить с combined.

### Гипотеза B — Cleaner свёл TR2-уникальный контент

Cleaner на 41K combined вернул 41.3K (-0.2%). Но какие именно куски сжаты? Может быть TR2-эпизоды попали в «общие места» при cleanup.

**Проверка:** diff cleaned_transcript_v54 ↔ raw_TR1+TR2.

### Гипотеза C — Completeness Auditor не подхватил

CA должен найти gaps. Pin-list (task 026) для огурцов/счётчика/Нинваны — есть ли?

**Проверка:** карта `karakulina_completeness_audit_v54.json` — какие gaps log_only_gaps.

---

## Решение

### Вариант 1 (рекомендуемый) — split-extract mode

Изменить `scripts/test_stage1_karakulina_full.py`:

- Cleaner на TR1 → cleaned_TR1
- Cleaner на TR2 → cleaned_TR2
- Fact Extractor на cleaned_TR1 → fact_map_TR1
- Fact Extractor на cleaned_TR2 (передавая fact_map_TR1 как existing_facts через Phase B) → fact_map_TR2
- Name Normalizer + Completeness Auditor на merged fact_map

Phase B уже поддерживает existing_facts — это **существующая возможность** FE, которую мы используем для cumulative extraction.

Плюс:
- Каждый транскрипт обрабатывается в полном своём контексте
- FE видит только свой транскрипт + already known facts
- Conflicts между TR1 и TR2 выделяются явно

Минус:
- Удваивается API cost Stage 1 (FE × 2)
- Cumulative merge через Phase B нужно проверить на корректность

### Вариант 2 — расширить pin-list Completeness Auditor

Из `known_episodes_karakulina.md` собрать pin-list:
- Огурцы Молдавия, счётчик 1977, Нинвана, шарлотка, продажа дачи, тётя Маша-соседка, и т.д.
- Передавать в CA как `pin_list_episodes` (новое поле в config или фактическом аргументе)
- CA при отсутствии в fact_map → flag в log_only_gaps + auto_enrich

Плюс:
- Не меняем архитектуру Stage 1
- Pin-list — это уже принятая концепция (task 026 для persons, расширяем на events)

Минус:
- Не работает для неизвестных эпизодов (если они есть)
- Pin-list нужно поддерживать вручную для каждого субъекта

### Вариант 3 — оба параллельно

Split-extract + pin-list. Самый дорогой, но самая высокая вероятность что эпизоды не теряются.

---

## Что нужно

**Опус-уровень (после go от Никиты):**
- Дизайн split-extract в test_stage1_karakulina_full.py
- Pin-list events секция в Completeness Auditor v1.2 (расширение v1.1)
- Unit-тесты на split-extract логику

**Курсор-уровень:**
- Реализация по дизайну Опуса
- v55 прогон Каракулины с новым Stage 1
- Сравнение fact_map_v55 vs fact_map_v54 (какие events появились)

**Дашин-уровень:**
- Pin-list для других субъектов (Королькова, Дмитриев) когда подойдём — другая задача

---

## Бюджет

~2-3 дня (split-extract + pin-list + тесты + интеграция).

## Verified-on-run

После реализации — v55 прогон Каракулины. Ожидание: все 8 потерянных эпизодов из known_episodes_karakulina.md появляются в fact_map_v55 и затем в book_FINAL_stage3_v55.

---

## История статусов

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-15 | `new` | Опус |
| 2026-05-15 | `in-progress` | Cursor |

## v55 результаты (2026-05-15)

Реализован Вариант 1 (split-extract) в `test_stage1_karakulina_full.py` + CA v1.2.
14 unit-тестов PASS. Слияние через PR #24 в main.

**Split-extract диагностика:**
- Phase A (TR1): 33 events, 18 persons
- Phase B (TR2) добавил: +9 events, +8 persons
- fact_map_full: 42 events, 26 persons

**Маркеры в fact_map_full:**
- ✅ счётчик 1977 (event_auto_002)
- ❌ огурцы Молдавия (не в timeline, но ✅ в book через CA persons/descriptions)
- ❌ Нинвана (не в timeline, но ✅ в book)
- ❌ шарлотка (absent)

**task 035 в book_FINAL_stage3:** 2/4 ✅ (огурцы ✅, Нинвана ✅, счётчик ❌, шарлотка ❌)

**Вывод:** Split-extract улучшил с 0/4 → 2/4. Огурцы и Нинвана попадают в книгу через CA обогащение.
Счётчик и шарлотка нужны итерация v56 с pin-list events (CA v1.2) через `--prev-fact-map v55_fact_map`.
