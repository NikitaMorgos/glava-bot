# Задача 039: Bio_data integrity — required fields check + family relation whitelist

**Статус:** `completed`
**Номер:** 039
**Автор:** Опус
**Дата создания:** 2026-05-17
**Тип:** `cco-скрипт`
**Batch:** 1 (скриптовый, низкий risk)
**Связано:** [architecture-stocktake-2026-05-17.md](../context/architecture-stocktake-2026-05-17.md) Классы 2 + 3; task 027 (bio_data.family completeness)

---

## Контекст

Из feedback Никиты по v56 (паспортичка ch_01):

**Что потерялось vs v55 (Класс 2 — volatility):**
- Не указан год смерти мужа Дмитрия (1978) — в fact_map есть, в bio_data.family.spouse — нет
- Нет года рождения Валерия (1948) в bio_data.family.son
- Нет даты пенсии 1994 (в нарративе есть, в паспортичке-сводке нет)
- Нет упоминания звания «Ударник коммунистического труда» в bio_data.awards (хотя оно в нарративе ch_02 есть)

**Что лишнее (Класс 3 — relation mismatch):**
- Тётя Маша попала в bio_data.family, хотя она **соседка**, не родственница
- Аналогично — в auto_enrich CA выделил «Баба Аня» как «свекровь или родственница зятя» — она не родственница Валентины, а свекровь рассказчика (= мать Владимира Маргось), это для bio_data.family.in_laws максимум, не для core family

**Что критически missing (FC err_004 v56):**
- person_019 (бабушка Марфа) — есть в fact_map.persons с relation_to_subject="бабушка", но отсутствует в bio_data.family. `enforce_bio_data_completeness` (task 027) **не сработал** — нужно дебажить.

**Корень:** `enforce_bio_data_completeness` чинит **completeness** (person из fact_map → bio_data.family), но не чинит:
- **Required field consistency** (если в fact_map.persons[i].death_year есть, bio_data.family[same person].death_year должен быть)
- **Relation whitelist** (только родственные relations попадают в family; соседи/коллеги — нет)
- Возможно — фильтрует по `confidence` (Марфа имеет `confidence: low` в fact_map, возможно `enforce_bio_data_completeness` её отсеивает)

Это **Классы 2 + 3 stocktake**. Чисто скриптовое решение.

---

## Спек

### Что нужно изменить / создать

**1. Дебаг существующей `enforce_bio_data_completeness`** в `pipeline_utils.py`:
- Загрузить v56 fact_map_full + book_FINAL_stage3
- Проверить почему person_019 (Марфа, бабушка, confidence: low) не добавлена в bio_data.family
- Гипотеза: фильтр `confidence >= medium` или `relation not in whitelist`
- Зафиксировать в комментарии и **расширить whitelist** на родственников с любым confidence (но с пометкой `needs_verification: true` если confidence low)

**2. Новая функция `validate_bio_data_required_fields(fact_map, book) -> list[issue]`** в `pipeline_utils.py`:
- Сравнивает bio_data.family / bio_data.awards с fact_map
- Для каждого родственника в bio_data.family:
  - Если в fact_map.persons[same id] есть `death_year` → bio_data entry должна содержать год смерти (в `note` или отдельном поле)
  - Если есть `birth_year` → должна содержать (для детей/супруга/субъекта)
  - Для супруга: и birth_year (если есть), и death_year (если есть, как у Дмитрия 1978)
- Для каждой награды в fact_map.subject.awards (или соответствующих events) → должна быть в bio_data.awards с годом
- Для пенсии (event_type="retirement"): в bio_data.work.retirement_year должен быть указан (или в bio_data.timeline соответствующий период)
- Возвращает список issues: `[{type: "missing_field", entity: "spouse Дмитрий", field: "death_year", expected: 1978, source: "fact_map.persons.person_006"}]`

**3. Функция `filter_bio_data_family_by_relation_whitelist(book, fact_map) -> book`**:
- Whitelist relations: `{отец, мать, муж, жена, сын, дочь, брат, сестра, бабушка, дедушка, прабабушка, прадедушка, внук, внучка, тётя, дядя, племянник, племянница, золовка, свекровь, тесть, тёща, свёкр, сват, сватья, зять, невестка, кум, кума}`
- Любая persona в bio_data.family с `relation_to_subject` НЕ в whitelist → **удалить из bio_data.family**, переместить в `bio_data.non_family_close` (новое поле, опционально) или просто log+remove.
- Логировать что удалено, для диагностики

**4. Интеграция в pipeline** (`scripts/test_stage3.py` или соответствующий runner):
- После Literary Editor + `preserve_chapter_structural_fields`, до Proofreader:
  - `enforce_bio_data_completeness` (existing, дебагнутая) — recall: добавить недостающих
  - `filter_bio_data_family_by_relation_whitelist` — precision: убрать чужих
  - `validate_bio_data_required_fields` — отчёт о потерянных полях, **+ auto-patch** где возможно (заполнить death_year супруга из fact_map.persons[].death_year)
- Сохранить отчёт `<run>_bio_data_integrity_<ts>.json`

### Какой результат ожидается

В v57 `bio_data.family`:
- ✅ Марфа (бабушка) есть с пометкой `needs_verification: true` (confidence low в fact_map)
- ✅ Тёти Маши **нет** (соседка фильтруется), либо она перемещена в отдельное поле
- ✅ Дмитрий (муж) — есть с `death_year: 1978` или text-поле «(ум. 1978)»
- ✅ Валерий — есть с `birth_year: 1948`
- ✅ Татьяна — есть с `birth_year: 1956`

В v57 `bio_data.awards`:
- ✅ Звание «Ударник коммунистического труда 1965» есть в bio_data.awards (а не только в нарративе ch_02)

В v57 `bio_data.work` или `bio_data.timeline`:
- ✅ Дата ухода на пенсию 1994 указана в паспортичке (не только в нарративе)

В отчёте `<run>_bio_data_integrity.json`:
- 0 issues типа `missing_field`
- 0 issues типа `non_family_in_family`
- Список добавленных персон через enforce (включая Марфу) с указанием `confidence`

### Как проверить

1. **Unit-тесты** `tests/test_bio_data_integrity.py`:
   - Required field: fact_map с death_year супруга 1978, bio_data без него → issue
   - Auto-patch: после `validate_bio_data_required_fields` поле заполнено из fact_map
   - Whitelist: persona с relation="соседка" в bio_data.family → удалена
   - Whitelist edge: persona с relation="свекровь" — это уровень in-laws, обсудить (`whitelist=False` или отдельное поле `bio_data.in_laws`)
   - Марфа case: confidence="low", relation="бабушка" → попадает в bio_data.family с needs_verification

2. **Integration-тест** на v56:
   - Загрузить `karakulina_v56_book_FINAL_stage3.json` + `karakulina_v56_fact_map_full.json`
   - Прогнать 3 функции
   - Проверить: Марфа добавлена, тётя Маша удалена, Дмитрий имеет death_year 1978

3. **Verified-on-run** v57:
   - Открыть `karakulina_v57_text_FULL.md`, секция «Семья»: проверить Марфа есть, тётя Маша не семья, Дмитрий «(ум. 1978)»
   - Проверить bio_data.awards: Ударник 1965 есть
   - FC iter3 v57: err_004 (Марфа) должен быть **отсутствовать**

---

## Ограничения

- [ ] Не менять промпт Ghostwriter / LE — это пост-процессинг
- [ ] Не трогать `bio_data.family` персон с relation в whitelist (только фильтровать НЕ-родственников)
- [ ] Auto-patch только из fact_map — не выдумывать данных
- [ ] Идемпотентность: повторный вызов не дублирует записи

---

## Dev Review

**Статус:** `approved`

**[TECH]:**
- ✅ Дебаг `enforce_bio_data_completeness`: корень — Stage 2 в v56 вызвал `sys.exit(1)` при FC FAIL **до** вызова `enforce_bio_data_completeness` (строка 362, после sys.exit на строке 357). Функция никогда не выполнилась. Марфа (`confidence: low`, `relation_to_subject: "бабушка"`) IS в fact_map.persons — логика `_is_family_person` правильно возвращала бы True. Фикс: добавить вызов в Stage 3 (независимо от Stage 2). Также: добавить `needs_verification: True` для `confidence: low` при auto-fill.
- ✅ Формат — текущий сохранён: `{"label", "value", "source"}` + optional `note`. death_year → в `note` как `"(ум. YYYY)"`. Рендер вёрстки не затронут.
- ✅ Whitelist — explicit (не blacklist): 26 relations в `_FAMILY_RELATION_WHITELIST`. Баба Аня (свекровь рассказчика) проходит через whitelist как "свекровь" — это проблема (она не родственница субъекту). Решение: filter смотрит на `relation_to_subject` в bio_data.family entry, и если CA правильно указывает "свекровь или родственница зятя" — фильтр оставит. Это edge case, решится при CA v1.3 (task 038).

**[PRODUCT]:**
- ✅ Свекровь рассказчика — **НЕ в bio_data.family Валентины** (Опус pre-answered). Если попадёт через GW — filter уберёт только если relation != whitelist. При правильной работе CA/GW должны ставить "свекровь рассказчика/дочери" — не в whitelist → удалится. Риск принят.

**Оценка сложности:** `s` (реализовано без затяжного дебага)
**Оценка риска:** `low`

---

## Dev Review Response

**Статус:** принято (соответствует pre-answer Опуса).

---

## Реализация

**Статус:** `completed` (2026-05-17)

**Дебаг результат:** Марфа missing в v56 потому что `enforce_bio_data_completeness` не вызывалась — Stage 2 упал с `sys.exit(1)` при FC FAIL до её вызова.

Реализовано в `pipeline_utils.py`:
- `enforce_bio_data_completeness` — улучшена: `confidence: low` → `needs_verification: True` при auto-fill
- `filter_bio_data_family_by_relation_whitelist(book)` — убирает не-родственников, сохраняет все 26 whitelist relations
- `validate_bio_data_required_fields(fact_map, book)` — проверяет + auto-patches death_year/birth_year в `note`, проверяет awards

Интеграция в `scripts/test_stage3.py`: после `preserve_chapter_structural_fields`, до Proofreader. Сохраняет `bio_data_integrity_{ts}.json`.

Тесты: `tests/test_bio_data_integrity.py` (17 тестов, 100% PASS).

---

## Verified-on-run

**Cursor:** [после v57]

**Claude:** [Опус проверит секцию «Семья» в v57 text_FULL — Марфа, нет тёти Маши, Дмитрий (ум. 1978), Ударник в awards]

---

## История статусов

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-17 | `new` | Опус |
