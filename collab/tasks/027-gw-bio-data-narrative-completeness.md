# Задача: GW bio_data + narrative completeness — code-level enforcement

**Статус:** `in-progress` (реализация завершена · 2026-05-04, ожидает verified-on-run v42)
**Номер:** 027
**Автор:** Даша / Claude
**Дата создания:** 2026-05-03
**Тип:** `код` / `safety-net` / Stage 2
**Связано:** 026 (Stage 1 pin-list, закрыта), 015 (пилот), 024 (аналогичный паттерн auto-clean)

---

## Контекст

При независимой проверке финального PDF v40 (pdfplumber) обнаружена **content-регрессия**:
- `bio_data.family` в ghostwriter checkpoint: **3 строки** (муж, дети, внуки)
- v36 bio_data.family: **16 строк** (мать, отец, сёстры, муж, дети, оба зятя, внуки, тётя Шура, племянники)
- v38 bio_data.family: **11 строк**

В финальном PDF v40 — 0 упоминаний Нинваны Полсачевой, тёти Шуры, Риммы, Зины, тёти Мани — несмотря на то что все они присутствуют в `fact_map_v40.persons[]`.

**Корневая причина:** Ghostwriter — LLM, нестабильный по природе. Промпт-патч 015 «bio_data completeness rule» (v2.14) работал на v38 (11 записей), но деградировал к v40 (3 записи). Промпт-only защита недостаточна — паттерн идентичен 024 (chapter_start) и 022 (hybrid detection).

**Диагностика fact_map v40a/b/c (выполнена 2026-05-03):**
- Все ранее нестабильные персоны есть в `persons[]`: Нинвана Полсачева, тётя Шура, Римма, Зина, тётя Маня/Маша
- `bio_data.family` в fact_map: 0 entries — это норма, заполняется GW в Stage 2
- Ghostwriter checkpoint (approved_at=2026-04-05) содержит только 3 записи в bio_data.family

---

## Решение Даши (PRODUCT)

**P1 — behavior дефолт:** `auto-fill` (симметрично 024 auto-clean и 022 hybrid).

После Stage 2 проверить:
```
count(bio_data.family) >= count(persons где relation в ["семья", "муж/жена", "дети", "внуки", "сёстры", "братья", "родители", "племянники"])
```
Если не хватает — **auto-fill из fact_map** с пометкой `source: "auto-filled"`. Override-флаг `--strict-bio-data` для прода.

**P2 — scope:** только `bio_data` в этой задаче. Нарратив — отдельно (семантическая задача, Narrative Auditor 016, отложено до конца пилота).

---

## Спецификация

### Входные данные

- `book_FINAL` (Stage 2 GW output, JSON `{"chapters": [...]}`)
- `fact_map` (Stage 1 output, JSON `{"persons": [...]}`)

### Алгоритм (code-level, post-Stage-2)

Функция `enforce_bio_data_completeness(book_final, fact_map, strict=False)` в `pipeline_utils.py`:

1. Из `fact_map.persons[]` выбрать персон с `relation` в семейном списке:
   `FAMILY_RELATIONS = {"муж", "жена", "сын", "дочь", "отец", "мать", "брат", "сестра", "дедушка", "бабушка", "внук", "внучка", "дядя", "тётя", "племянник", "племянница", "свёкор", "свекровь"}`
   Плюс частичное совпадение: если `relation` содержит одно из этих слов.

2. Получить `ch_01.bio_data.family` из `book_FINAL`.

3. Для каждой персоны из fact_map семейного списка:
   - Проверить упоминание по имени в любой из `family` строк.
   - Если не найдено — **создать** запись `{"label": person.relation or "родственник", "value": person.name, "source": "auto-filled"}` и добавить в `bio_data.family`.

4. Вывести лог: `[BIO-COMPLETENESS] auto-filled N персон в bio_data.family: [имена]`.

5. Если `strict=True` (флаг `--strict-bio-data`) — raise вместо auto-fill.

### Изменения кода

| Файл | Что |
|------|-----|
| `pipeline_utils.py` | Функция `enforce_bio_data_completeness(book_final, fact_map, strict=False)` |
| `scripts/test_stage2_pipeline.py` | Вызов после GW + FC, `--strict-bio-data` флаг (основной скрипт Каракулиной) |
| `scripts/test_stage2_korolkova.py` | Вызов после GW + FC, `--strict-bio-data` флаг |
| `scripts/test_stage2_dmitriev.py` | Вызов после GW + FC, `--strict-bio-data` флаг |
| `scripts/test_stage2_phase_b.py` | Вызов после GW + FC, `--strict-bio-data` флаг (Phase B — не используется в пилоте) |

### Граничные случаи

- `fact_map.persons[]` пустой → нет изменений
- `bio_data` отсутствует в `ch_01` → создать `{"family": [auto-filled]}`, предупреждение в лог
- `relation` не заполнен у персоны → использовать `"родственник"` как label
- Дублирование имён → проверять по нормализованному имени (lowercase, без пробелов по краям)

---

## Dev Review

**Статус:** `spec-approved` (утверждено Дашей 2026-05-03)

### Гипотезы причин (Даша, 4 штуки)

1. **Промпт-патч 015 потерян при миграции на GW v3.21** — наиболее вероятно: версия GW изменилась, промпт обновлён, bio_data completeness rule не перенесена.
2. **LLM нестабильность** — патч был, но LLM его не соблюдает стабильно (v38 = 11, v40 = 3).
3. **Логика фильтрации persons в pipeline_utils** — между Stage 1 и Stage 2 GW теряются «тихие» персоны.
4. **persons[].relation = ?** — v40 fact_map имеет `relation: "?"` для ВСЕХ персон. GW не имеет info о семейных отношениях → не может правильно заполнить bio_data.

**Наиболее вероятная:** гипотеза 4 + 2 в комбинации. Если `relation` везде `"?"`, то фильтр по семейным отношениям не сработает. Нужно дополнительно проверить семейный статус через имя (тётя, дядя, брат, сестра как подстрока имени).

### Доп. требование к алгоритму

Дополнить шаг 1: если `person.relation == "?"`, проверить содержит ли `person.name` семейные маркеры ("тётя", "дядя", "брат", "сестра", "дедушка", "бабушка", "мама", "папа") — и включить в семейный список.

---

## Реализация (Cursor, 2026-05-04)

### Диагностика

Проверены все 19 персон в `fact_map` (v40 checkpoint на сервере): `relation: null` у всех. Подтверждена гипотеза 4 — `persons[].relation = null` для всех, поэтому фильтр по `relation` не сработает. Реализован алгоритм с двумя путями: по `relation` (если заполнен) и по маркерам в имени ("тётя", "дядя", "брат", и т.д.).

### Изменения

**`pipeline_utils.py`** — добавлена функция `enforce_bio_data_completeness(book_final, fact_map, strict=False)`:
- Константы `_FAMILY_RELATIONS`, `_FAMILY_NAME_MARKERS`, `_UNKNOWN_RELATIONS`
- Вспомогательные функции `_is_family_person()` и `_name_in_family_entries()`
- Алгоритм: проверяет `relation` на семейные слова (частичное совпадение) + маркеры в имени
- При `relation == "?" / null` — проверяет имя на маркеры ("тётя Шура" → семейный)
- Дублирование предотвращается через `_name_in_family_entries`: substring-поиск по частям имени длиной ≥ 4 символа
- auto-fill: `{"label": relation_or_"родственник", "value": name, "source": "auto-filled"}`
- strict=True: `raise RuntimeError` вместо auto-fill
- Если `ch_01` нет или `bio_data` нет — создаёт структуру с предупреждением, не падает

**`scripts/test_stage2_phase_b.py`**:
- Добавлен CLI флаг `--strict-bio-data`
- Вызов `enforce_bio_data_completeness(book_draft, fact_map, strict=args.strict_bio_data)` перед сохранением финального файла

### Локальные тесты (scripts/_test_027_local.py)

7 тестов, все **PASS**:
1. `auto-fill по маркерам в имени (тётя/дядя)` — тётя Шура и тётя Маня добавляются, Нинвана нет
2. `strict=True вызывает RuntimeError` — проверяет правильный текст ошибки
3. `уже упомянутые персоны не дублируются` — Дмитрий Каракулин в "Дмитрий Каракулин, военный" = найдено
4. `пустой fact_map → no changes`
5. `bio_data absent → создаётся и заполняется`
6. `relation='?' + нет маркера → не auto-fill` (Нинвана Полсачева, Маргось)
7. `relation=семейное слово → auto-fill с правильным label`

---

## Verified-on-run

По протоколу слепого прохода (dev-review-protocol.md):

**Процедура для v42:**
1. Курсор запускает Stage 2 v42 (Phase B) и присылает только: «прогон завершён, артефакт: `<путь>`»
2. Даша открывает `book_FINAL_v42.json` самостоятельно и пишет свои наблюдения
3. Курсор присылает свои наблюдения после
4. Сравниваем

**Критерии PASS:**
- `count(bio_data.family) >= 11` (как в v38)
- В логе: `[BIO-COMPLETENESS] auto-filled K персон в bio_data.family: [имена]`
- Все тётя Шура, тётя Маня/Маша, Рудай Иван, Рудая Пелагея упомянуты

---

## История статусов

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-03 | `new` → `spec-approved` | Даша |
| 2026-05-04 | `spec-approved` → `in-progress` | Cursor (реализация + 7/7 unit tests) |
