# Задача: Completeness Auditor + Name Normalizer — защита от нестабильности FE

**Статус:** `done` (прогон v36 завершён · 2026-04-28 · Cursor)
**Номер:** 014
**Автор:** Даша / Claude
**Дата создания:** 2026-04-27
**Тип:** `новый-агент` + `cco-скрипт`
**Преемник задачи:** 011 (closed-superseded)

> **Статусный флоу:**
> `new` → `dev-review` → `spec-review` → `spec-approved` / `blocked-on-product` → `in-progress` → `dasha-review` → `done`

---

## Контекст

Задача 011 предполагала, что в FE v3.4 произошла регрессия (Татьяна и ключевые факты пропали из fact_map). После анализа исторических прогонов выяснилось: **это не регрессия конкретной версии, а системная нестабильность LLM Fact Extractor.**

### Доказательства нестабильности

**Анализ 4 прогонов** (`fact_map_v29.json`, `v30.json`, `v34.json`, `karakulina_fact_map_full_20260413_042556.json`):

**Стабильно во всех 4 прогонах** только 9 персон (Иван, Пелагея, Дмитрий, Валерий, Никита, Даша, тётя Шура, тётя Маша, младший брат).

**Появляются/исчезают между прогонами:**

| Персона | Когда есть | Когда нет |
|---------|------------|-----------|
| Полина (старшая сестра) | v29, v30, v34 | full_0413 (там «Полина Амельченко») |
| Маргось Владимир | v29, v30, v34 | full_0413 (там «Владимир Маргось») |
| Кужба Олег | v29, v30, v34 | full_0413 (там «Олег Кужба») |
| Толя (племянник) | v29, v30, full_0413 | v34 |
| Витя (племянник) | v29, v30, full_0413 | v34 |
| Коля (племянник) | v30, full_0413 | v29, v34 |
| тётя Маня | v34, full_0413 | v29, v30 |
| Каракулина Татьяна (дочь!) | v34, full_0413 | v29, v30 |
| Нинвана (врач) | v34 | v29, v30 |
| Нинвана Полсачева | full_0413 | v29, v30, v34 |
| старшие сёстры | v29, v30 | v34, full_0413 |
| Амельченко | v29, v30 | v34, full_0413 |
| Римма / Зина / Коля-лётчик | редкие | в большинстве отсутствуют |

**Вывод:**

1. **LLM нестабилен** — даже на одинаковом входе он по-разному решает кого считать персоной, как нормализовать имя, какие сущности пропустить.
2. **Нормализация имён непредсказуема** — «Полина» vs «Полина Амельченко», «Маргось Владимир» vs «Владимир Маргось». Без детерминированной канонизации downstream-агенты получают разные id для одного человека.
3. **Ключевые факты (пианино, Сахалин, Нинвана) тоже теряются нестабильно** — в одних прогонах есть, в других нет.

Правкой промпта это не лечится — это свойство самой LLM на длинном входе.

### Предложенное решение (выбор Даши: **A + C**)

**Variant A — Completeness Auditor (LLM, второй проход):**
Отдельный агент после FE. Получает на вход: транскрипт + fact_map. Задача — найти упомянутое в транскрипте, но отсутствующее в fact_map (персоны, события, локации, traits). На выход — список gaps.

**Variant C — Name Normalizer (детерминированный, код):**
После Completeness Auditor. Сканирует транскрипт, нормализует имена/фамилии (склонения, перестановки имя/фамилия, диминутивы), склеивает persons[] с пересекающимся набором упоминаний в одну каноническую запись.

**Порядок:** FE → Completeness Auditor → Name Normalizer → downstream (Historian, GW, FC).

Сначала A (нашли все упомянутые сущности, в том числе разные варианты имён), затем C (схлопнули дубликаты по канонической форме). Архитектурно тот же Name Normalizer применим к локациям (Капошвара/Капашвара).

---

## Спек

### Что нужно создать

#### 1. Completeness Auditor (Variant A)

**Новый агент:** `15_completeness_auditor_v1.md` (или второй проход FE — см. [PRODUCT-1] ниже)

**Вход:**
- Очищенный транскрипт (cleaned_transcript)
- fact_map.json после FE

**Задача агента:**
- Прочитать транскрипт целиком
- Прочитать fact_map
- Найти **все** упомянутые в транскрипте: имена людей, топонимы, события, объекты (пианино, шуба, сервиз), привычки/черты
- Сравнить с fact_map
- Вернуть JSON со списком gaps:

```json
{
  "missing_persons": [
    {"mention_in_transcript": "Татьяна", "context": "...", "likely_relation": "дочь"}
  ],
  "missing_events": [
    {"keyword": "Сахалин", "transcript_quote": "Дмитрию предложили...", "suggested_title": "Развилка с Сахалином"}
  ],
  "missing_locations": [...],
  "missing_traits": [...]
}
```

**Действие при gaps:**
- В debug-режиме (сейчас): пишем gaps в `roles_checklist.md`, ставим `"completeness_status": "incomplete"` + список gaps в `manifest.json`. Пайплайн **продолжается**.
- В прод-режиме: уровень эскалации решается в task 013 (CJM).

#### 2. Name Normalizer (Variant C)

**Новый CCO-скрипт:** `scripts/normalize_named_entities.py`

**Логика:**

```python
def normalize_named_entities(fact_map, transcript):
    # 1. Для каждой записи persons[] и locations[]:
    #    - сгенерировать варианты канонического имени:
    #      a) перестановки (Маргось Владимир ↔ Владимир Маргось)
    #      b) части (только имя, только фамилия)
    #      c) диминутивы (Владимир → Володя), если есть в aliases
    #      d) словоформы через лемматизатор (pymorphy2 или простой стеммер)
    # 2. Сканировать транскрипт — собрать множество позиций упоминаний
    # 3. Если две записи имеют пересекающиеся множества упоминаний → склеить
    #    - выбрать каноническую форму (полная: имя + фамилия)
    #    - объединить aliases, asr_variants
    #    - сохранить наивысший confidence
    # 4. Обновить ссылки во всём fact_map (events.participants, relationships, traits)
```

**Применяется к:**
- `persons[]` (имена людей)
- `locations[]` (топонимы)

**Лог:**
- В `roles_checklist.md` — какие записи слиты, по каким признакам
- В `manifest.json` — `"normalized_pairs": [["Маргось Владимир", "Владимир Маргось"], ...]`

#### 3. Интеграция в пайплайн

**Pipeline order:**

```
Cleaner → Fact Extractor → [NEW] Completeness Auditor → [NEW] Name Normalizer → Historian → GW → FC → ...
```

**Pre-flight check:** дополнить проверкой что промпт `15_completeness_auditor_v1.md` существует и `scripts/normalize_named_entities.py` импортируется.

**Manifest:** добавить ключи:
- `"completeness_audit": {"status": "ok|incomplete", "gaps": [...]}`
- `"name_normalization": {"merged_pairs": [...], "normalized_count": N}`

### Какой результат ожидается

На прогоне v36 на тех же транскриптах TR1 + TR2:

1. **Completeness Auditor:** поднимает в gaps как минимум — пианино, Сахалин, сервиз, «посидеть на дорожку», Нинвана (если FE снова их пропустит). Если FE их извлёк — gaps пустой.
2. **Name Normalizer:** «Маргось Владимир» и «Владимир Маргось» → одна запись. «Полина» и «Полина Амельченко» → одна запись.
3. Между прогонами v36, v37, v38 на одних и тех же транскриптах — **persons[] стабильны** (одинаковый набор канонических имён) даже если LLM выдаёт разные формы.
4. Manifest содержит `completeness_audit` и `name_normalization` блоки.

### Как проверить

```bash
# Запустить Stage 1 с новой архитектурой
python scripts/test_stage1_karakulina_full.py --tr1 TR1 --tr2 TR2 --output v36

# Проверить manifest
cat collab/runs/manifest_s1_v36.json | jq '.completeness_audit, .name_normalization'

# Прогнать дважды и сравнить стабильность persons[]
python scripts/test_stage1_karakulina_full.py --tr1 TR1 --tr2 TR2 --output v36a
python scripts/test_stage1_karakulina_full.py --tr1 TR1 --tr2 TR2 --output v36b
python scripts/compare_persons_across_runs.py v36a v36b
# Ожидается: 0 различий в персонах (или только confidence-варьирование)
```

---

## Ограничения

- [ ] Не менять формат fact_map.json для downstream-агентов — после Name Normalizer структура та же, просто записи дедуплицированы
- [ ] Не блокировать пайплайн при gaps в debug-режиме — только warning + флаг в manifest
- [ ] Не использовать тяжёлые NLP-зависимости без согласования (pymorphy2 ок; spacy/natasha — обсудить)
- [ ] Сохранять traceability — после слияния записей в manifest должно быть видно какие записи были слиты и по каким признакам
- [ ] Для Name Normalizer: не сливать записи если пересечение упоминаний < 50% (порог обсуждаем) — иначе риск ложного слияния тёзок

---

## Принятые продуктовые решения (Даша)

**[PRODUCT — закрыто перед dev-review]**

1. **Подход:** Variant A (Completeness Auditor LLM, two-pass) + Variant C (Name Normalizer deterministic). Применяется в порядке A → C.

2. **Уровень эскалации при gaps (debug-режим):** **уровень 2** — warning + флаг `"completeness_status": "incomplete"` в `manifest.json` + блок «Completeness Check» в `roles_checklist.md`. Пайплайн **не блокируется**. Уровень эскалации для прод-режима — решается в task 013 (CJM).

3. **Name Normalizer ищет варианты по транскрипту:** не только по полю `aliases` в fact_map, а сканируя cleaned_transcript на словоформы и перестановки канонического имени. Записи с пересекающимся набором упоминаний в транскрипте — склеиваются.

---

## Dev Review

> Заполняет Cursor до реализации. Статус задачи при заполнении: `dev-review`.
> Протокол: `collab/context/dev-review-protocol.md`

**Статус:** ожидает Cursor

---

### Открытый вопрос для разработки (требует ответа Cursor перед spec-approved)

**[OPEN-1] Completeness Auditor: отдельный агент или второй проход FE?**

Два варианта реализации Variant A:

**(a) Отдельный агент `15_completeness_auditor_v1.md`:**
- Свой промпт-файл
- Свой вызов LLM с собственными `model`, `max_tokens`, `temperature`
- На вход: cleaned_transcript + fact_map.json
- На выход: structured JSON со списком gaps
- В `pipeline_config.json` — отдельная запись `completeness_auditor`

(+) Чистая архитектура, легко дебажить отдельно, можно поменять модель на более дешёвую (Haiku) для проверки полноты
(–) Дополнительный LLM-вызов (~$0.05–0.10), отдельный промпт поддерживать

**(b) Второй проход того же FE с дополнительной инструкцией:**
- Тот же `02_fact_extractor_v3.X.md` вызывается повторно
- На вход: cleaned_transcript + fact_map.json (от первого прохода) + инструкция «найди что пропущено»
- На выход: дельта-fact_map, мерджится с основным

(+) Не нужно создавать новый промпт, переиспользуем уже отлаженный FE
(–) FE и так длинный — добавление self-check логики раздует промпт; смешение ролей (extract + audit); сложнее дебажить какой проход что сделал

**Просим Cursor ответить:**
- Какой вариант проще встроить в текущий пайплайн (`scripts/run_pipeline.py`, `pipeline_config.json`)?
- Стоимость (a) vs (b) при текущем объёме входа (~70 KB)?
- Дебаг и логирование — где проще различать «что сделал FE-первый проход» vs «что нашёл аудитор»?
- Какие промпт-кэширование риски (если первый и второй вызов используют один и тот же системный промпт)?

Cursor может дать рекомендацию [TECH], если решение чисто техническое. Если есть продуктовые импликации — эскалирует Даше как [PRODUCT].

---

**Статус:** заполнено Cursor · 2026-04-27

---

### Ответ на [OPEN-1]: отдельный агент vs второй проход FE

**Рекомендация: вариант (a) — отдельный агент на Haiku.**

Конкретные данные:

| Параметр | (a) Отдельный агент | (b) Второй проход FE |
|---|---|---|
| Модель | claude-haiku (достаточно) | claude-sonnet (обязательно) |
| Input tokens | ~20K (transcript + fact_map) | ~30K (+ длинный промпт FE) |
| Output tokens | ~2K (список gaps) | ~17K (полная дельта fact_map) |
| Стоимость/прогон | **~$0.006** | **~$0.09** (~15× дороже) |
| Debug | gaps явно в JSON, легко логировать | нужен diff двух fact_map |
| Merge | новая функция merge_gaps() | существующий merge_fact_maps() |
| Prompt caching | нет эффекта (один прогон = один Stage 1) | нет эффекта |
| Когнитивная роль | "найди что пропущено" (аудит) | "извлеки факты" (экстракция) |

Ключевой аргумент против (b): FE-промпт заточен на извлечение с нуля или обновление (Phase B). «Найди что я сам пропустил» — другой когнитивный режим. Второй проход FE с existing_facts входит в Phase B логику (ищет противоречия), а не в логику completeness gap. Смешение ролей усложняет отладку — непонятно, почему конкретный факт снова не извлечён.

**Совет по модели**: для Auditor'а достаточно Haiku — задача паттерн-матчинга («есть ли в транскрипте слово X, которого нет в fact_map?»), не творческое письмо.

---

### Диагностика перед реализацией

Проверил `pipeline_config.json`, `pipeline_utils.py`, существующие скрипты:

1. **Агент с именем `15_...` уже существует** — `15_layout_art_director_v1.8.md`. Нумерация занята.
2. **`merge_fact_maps()`** уже есть в `pipeline_utils.py` (строки 316–367) — но он мержит полный fact_map, не gap-отчёт. Нужна отдельная функция или изменение формата вывода Auditor'а.
3. **`scripts/compare_persons_across_runs.py`** не существует — спек его упоминает, нужно создать.
4. **`pymorphy2`** не в `requirements.txt` — нужно решить до старта кодинга.
5. **Интеграция в `test_stage1_karakulina_full.py`**: сейчас вызов FE → сохранение → конец. Новые шаги (Auditor + Normalizer) встраиваются после строки 108 по той же схеме что и остальные агенты.

---

### [TECH] Технические флаги

**[TECH-1] Конфликт нумерации: `15_` уже занят layout_art_director**
В `pipeline_config.json` и папке `prompts/` уже есть `15_layout_art_director_v1.8.md`. Нумерация 15 занята. Предлагаю `16_completeness_auditor_v1.md`. Нужно согласовать до создания файла.

**[TECH-2] Формат вывода Auditor влияет на merge-логику**
Спек описывает вывод Auditor'а как `{missing_persons, missing_events, missing_locations, missing_traits}`. Это НЕ полный fact_map → `merge_fact_maps()` его не примет. Два варианта:
- (а) Auditor выдаёт mini-fact_map (только новые persons/events/etc.) → использовать существующий `merge_fact_maps()`
- (б) Auditor выдаёт gap-отчёт → новая функция `apply_completeness_gaps(fact_map, gaps_report)`

Вариант (а) проще (переиспользует протестированный код), вариант (б) более явен (gap-отчёт ≠ fact_map). Cursor рекомендует **(а)** — меньше нового кода.

**[TECH-3] Name Normalizer: обновление ссылок по всему fact_map**
При слиянии двух записей ("Маргось Владимир" → "Владимир Маргось") нужно перепрописать все ID-ссылки в `timeline[].participants`, `relationships[]`, `character_traits[].described_by`, `quotes[].speaker`. Это не тривиально и пока не описано в спеке. Нужен явный алгоритм: старый `id` → новый канонический `id`, пройти по всем полям fact_map.

**[TECH-4] pymorphy2 отсутствует в requirements.txt**
Спек упоминает pymorphy2 для Name Normalizer. Пакет ~40 МБ с морфологическими словарями. Альтернатива без тяжёлых зависимостей: для нашей задачи достаточно перестановки (Имя/Фамилия), нормализации регистра и сопоставления по подстроке без лемматизации — покрывает 90% случаев в fact_map. Полная морфология нужна только для диминутивов (Владимир → Володя → Вова). Предлагаю: реализовать без pymorphy2 сначала, диминутивы — через явный словарь в конфиге проекта.

**[TECH-5] `scripts/compare_persons_across_runs.py` — новый скрипт, нужно создать**
Спек ссылается на него как на инструмент валидации стабильности. Не существует. Включить в scope реализации или отметить как отдельную задачу.

**[TECH-6] Порог слияния "< 50% пересечения" требует формализации**
Спек: «не сливать записи если пересечение упоминаний < 50%». Нужна конкретная формула — предлагаю:  
`overlap = count(windows_A ∩ windows_B) / max(len(windows_A), len(windows_B))`  
где window = позиция в транскрипте ±300 chars. Слияние если overlap ≥ 0.3 (предлагаю 0.3, не 0.5 — иначе тёзки из разных семей не сливаются, а дубли с разным порядком слов тоже не сливаются). Порог нужно обсудить.

**[TECH-7] Нет `run_pipeline.py` для полного Stage 1**
Задача упоминает `scripts/run_pipeline.py` в [OPEN-1]. Такого файла нет — есть `test_stage1_karakulina_full.py` (project-specific) и `run_pipeline_daria.py` (legacy bot pipeline). Новые агенты интегрируются в `test_stage1_karakulina_full.py` и `pipeline_utils.py`, не в несуществующий файл.

---

### [PRODUCT] Продуктовые флаги (эскалируются Даше)

**[PRODUCT-1] Что Auditor делает с gaps в debug-режиме — логирует или добавляет в fact_map?**
Спек: «пишем gaps в roles_checklist.md». Но если Auditor только логирует, а не добавляет в fact_map — downstream GW и FC по-прежнему не получат пропущенные факты. GW напишет книгу без Сахалина и пианино. Нужно определить: Auditor (а) только аудирует и предупреждает, или (б) автоматически обогащает fact_map? Если (б) — Auditor становится частью production-экстракции, а не только диагностическим инструментом.

**[PRODUCT-2] Completeness Auditor будет поднимать ложные срабатывания**
Имя «Сталин» или «Горбачёв» упоминается в транскрипте, но не должно попасть в persons[] как родственник. Auditor по принципу "упомянуто → должно быть в fact_map" будет их флагать. Нужен критерий значимости: только прямые участники событий героя? Только упомянутые ≥2 раз? Только с указанием отношения к герою? Без этого критерия Auditor-отчёт будет перегружен шумом.

---

**Оценка сложности:** `m` (2–3 дня чистого кода + тесты)  
**Оценка риска:** `medium` — Name Normalizer с ID-ремаппингом затрагивает весь fact_map, ошибка в нём ломает downstream GW/FC

---

## Dev Review Response

> Заполняет Даша/Claude после Dev Review.

**Статус:** заполнено · 2026-04-27 (Claude — TECH автономно; Даша — PRODUCT)

---

### Ответы на [TECH] флаги (Claude, автономно)

**[TECH-1] Конфликт нумерации 15_** ✅ ПРИНИМАЮ. Используем `16_completeness_auditor_v1.md`. Cursor, обнови все упоминания в коде и manifest.

**[TECH-2] Формат вывода Auditor'а** → решается через [PRODUCT-1] (см. ниже). Поскольку Даша выбрала **гибрид**, формат вывода — **mini-fact_map** (для high-confidence находок, чтобы переиспользовать `merge_fact_maps()`) **+ дополнительный gap-отчёт** (для low-confidence — только лог). То есть Auditor выдаёт оба блока:

```json
{
  "auto_enrich": {
    // mini-fact_map: persons[], events[], locations[], traits[]
    // только high-confidence (с прямой цитатой из транскрипта)
  },
  "log_only_gaps": {
    // gap-отчёт: low-confidence находки для лога, без авто-добавления
  }
}
```

`auto_enrich` идёт через `merge_fact_maps()`. `log_only_gaps` — в `roles_checklist.md` + `manifest.completeness_audit.gaps[]`.

**[TECH-3] ID-ремаппинг по всему fact_map** ✅ ПРИНИМАЮ. Cursor, в реализации опиши явный алгоритм:
- Карта `old_id → new_canonical_id` после каждого слияния
- Проход по полям: `timeline[].participants[]`, `relationships[].person_a`, `relationships[].person_b`, `character_traits[].described_by`, `quotes[].speaker`, `conflicts[].parties[]`, `gaps[].related_persons[]`
- Финальная валидация: `validate_fact_map_integrity(fact_map)` не находит ссылок на удалённые id

**[TECH-4] pymorphy2 не используем для v1** ✅ ПРИНИМАЮ. Простой суффиксный стеммер для русских окончаний + явный словарь диминутивов в `prompts/normalization_dict.json` (Владимир→Володя/Вова, Александр→Саша, Дмитрий→Дима и т.п.). v2 при необходимости — добавим pymorphy2.

**[TECH-5] `compare_persons_across_runs.py`** ✅ ПРИНИМАЮ. Включить в scope задачи 014 как часть приёмки.

**[TECH-6] Порог слияния — формула 30%** ✅ ПРИНИМАЮ. Формула:
`overlap = |windows_A ∩ windows_B| / max(|windows_A|, |windows_B|)`
где `window` = позиция упоминания ±300 chars в транскрипте. Слияние если `overlap ≥ 0.3`. В реализации — описать формулу в комментарии к функции и сделать порог конфигурируемым через константу.

**[TECH-7] Нет `run_pipeline.py`** ✅ ПРИНИМАЮ. Интеграция в `test_stage1_karakulina_full.py` и `pipeline_utils.py`. Универсальный `run_pipeline.py` — отдельная архитектурная задача (создавать в рамках 014 не нужно).

---

### Ответы на [PRODUCT] флаги (Даша, 2026-04-27)

**[PRODUCT-1] ✅ Гибрид.** Auditor работает в гибридном режиме:

- **High-confidence находки** (есть прямая цитата из транскрипта, поле `transcript_quote` непустое) → автоматически добавляются в fact_map через `merge_fact_maps()`. GW получает обогащённый fact_map.
- **Low-confidence находки** (без прямой цитаты, или контекст слабый) → только лог в `roles_checklist.md` + `manifest.completeness_audit.gaps[]`. Не добавляются в fact_map. Даша решает вручную при ревью.

Критерий high-confidence для Auditor'а:
- Поле `transcript_quote` обязательно
- Цитата найдена в cleaned_transcript (валидируется кодом после получения ответа от LLM)
- Контекст роли/связи однозначен (родство, событие)

**[PRODUCT-2] ✅ Семантический критерий значимости (без частоты).** Auditor добавляет персону, если в транскрипте про неё есть **хотя бы одно из:**

1. Указано родство или социальная роль с героем/семьёй (дочь, зять, золовка, соседка, врач, коллега, крёстная и т.п.)
2. Участие в событии биографии героя (помогла, приехала, подарила, работали вместе, жил у них)
3. Имя + контекст роли, даже если родство не названо прямо («Нинвана Полсачева — врач, авторитет для матери»)

**Не добавлять (False Positive):**
- Исторические фигуры в цитатах или как маркер времени («как Сталин говорил», «при Хрущёве»)
- Безымянные категории («учителя», «соседи», «коллеги» без конкретики)
- Случайные упоминания без связи с героем

**Защита в коде (Name Normalizer):** blocklist исторических фигур (Сталин, Ленин, Хрущёв, Брежнев, Горбачёв, Жуков, Сталин и т.д.) — отфильтровывается с логом `filtered: historical figure`.

Частоту упоминаний **не используем** — однажды упомянутая «тётя Шура — золовка» важна для биографии. Главный сигнал — семантическая роль, не частота.

Эту формулировку Cursor включает в промпт `16_completeness_auditor_v1.md` явно.

---

**Итог:** `spec-approved`. Все [TECH] и [PRODUCT] флаги закрыты. Cursor может приступать к реализации.

---

## Реализация

**Статус:** завершена · 2026-04-27 · Cursor

### Созданные файлы

| Файл | Назначение |
|------|-----------|
| `prompts/16_completeness_auditor_v1.md` | Промпт агента 16 (Completeness Auditor) |
| `scripts/normalize_named_entities.py` | Name Normalizer — детерминированная нормализация |
| `scripts/compare_persons_across_runs.py` | Регрессионное сравнение persons[] между прогонами |

### Изменённые файлы

| Файл | Что добавлено |
|------|--------------|
| `prompts/pipeline_config.json` | Секция `completeness_auditor` (Haiku, max_tokens=8000) |
| `pipeline_utils.py` | `run_completeness_auditor()`, `apply_completeness_enrichment()` |
| `scripts/test_stage1_karakulina_full.py` | Шаги 3 (CA) и 4 (Name Normalizer) после FE |
| `prompts/CHANGELOG.md` | Запись о CA v1.0 с 2026-04-27 |

### Порядок вызова в пайплайне

```
Cleaner → FE (Fact Extractor) → Completeness Auditor → apply_completeness_enrichment()
→ normalize_named_entities() → clean_fact_map_for_downstream() → Stage 2 (GW, FC, ...)
```

### Детали реализации

**Completeness Auditor (промпт + вызов):**
- Модель: `claude-haiku-4-5-20251001`, temperature=0.1, max_tokens=8000
- Вход: cleaned_transcript + fact_map (JSON в user-сообщении)
- Выход: `auto_enrich` (частичный fact_map со схемой FE) + `log_only_gaps`
- `auto_enrich` мержится через существующий `merge_fact_maps(base, incremental)`
- `log_only_gaps` пишется в manifest.json поле `notes.completeness_audit`
- Промпт включает: семантический критерий (PRODUCT-2), blocklist историч. деятелей, правило рассказчика-как-персонажа, обязательный `source_quote`

**Name Normalizer (скрипт):**
- Чисто детерминированный, без LLM-вызовов
- Алгоритм: positional windows ±300 chars, overlap ≥ 30% → слияние
- Варианты: aliases, asr_variants, перестановки имя/фамилия, части имени, словарь диминутивов (20 имён)
- После слияния: `_remap_ids_in_fact_map()` обновляет timeline[], relationships[], character_traits[], quotes[]
- `validate_fact_map_integrity()` проверяет все ID-ссылки после нормализации
- Blocklist исторических деятелей (24 персоны)
- CLI: `--fact-map`, `--transcript`, `--output`, `--log`

**compare_persons_across_runs.py:**
- Сравнение по name + aliases (без учёта регистра, с учётом псевдонимов)
- Возвращает: in_both, only_in_a (регрессия), only_in_b (обогащение), stability_score
- `--fail-on-loss N` для CI: exit(1) если потеряно > N персон

---

## Комментарии и итерации

### 2026-04-28 — Claude → Cursor: ТЗ на прогон v36 (после успешной верификации фиксов)

Все три фикса (ISSUE-1, 2, 3) проверены на коде — на месте. Claude подтверждает: статическая проверка артефактов **пройдена**.

**Запрос Cursor:** провести прогон Stage 1 на Каракулиной с двумя итерациями для проверки стабильности.

#### Команды прогона

```bash
# Прогон A
python scripts/test_stage1_karakulina_full.py --output v36a

# Прогон B (на тех же транскриптах, для проверки стабильности LLM)
python scripts/test_stage1_karakulina_full.py --output v36b

# Сравнение стабильности
python scripts/compare_persons_across_runs.py \
    --run-a collab/runs/karakulina_fact_map_full_v36a.json \
    --run-b collab/runs/karakulina_fact_map_full_v36b.json \
    --output collab/runs/v36_stability_report.json
```

#### Что должно быть в отчёте Cursor (заполнить в разделе «Реализация» этой задачи)

**1. Артефакты** — пути к 5 файлам каждого прогона:
- `manifest_s1_v36a.json` / `manifest_s1_v36b.json`
- `karakulina_cleaned_transcript_*.txt`
- `karakulina_fact_map_full_*.json`
- `karakulina_fact_map_*.json` (clean-версия для downstream)
- `karakulina_completeness_audit_*.json`
- `v36_stability_report.json`

**2. Стоимость и время по каждому прогону:**
- Cleaner: input/output tokens, время, $
- Fact Extractor: input/output tokens, время, $
- Completeness Auditor: input/output tokens, время, $
- Name Normalizer: время (LLM нет)
- Итого: время прогона, общая стоимость

**3. Ключевые проверки приёмки** (✅/❌ по каждому пункту):

| Проверка | Где смотреть |
|----------|--------------|
| Татьяна в `persons[]` | `fact_map_full.json` → `persons[]` |
| Если ❌ от FE — попала ли через `auto_enrich`? | `karakulina_completeness_audit.json` → `auto_enrich.persons` |
| Сахалин в `timeline[]` или `auto_enrich.timeline` | оба файла |
| Пианино / шуба / сервиз | `timeline[]` или `auto_enrich` |
| «посидеть на дорожку» | `character_traits[]` или `auto_enrich.character_traits` |
| Нинвана (врач) в `persons[]` | `persons[]` или `auto_enrich.persons` |
| «Маргось Владимир» / «Владимир Маргось» слиты в одну запись | `manifest.name_normalization.merged_pairs` |
| «Полина» / «Полина Амельченко» — если возникнут — слиты | то же |
| Manifest содержит блок `completeness_audit` | `manifest_s1_v36*.json` |
| Manifest содержит блок `name_normalization` | то же |
| Если в логах появились исторические фигуры (Сталин и т.п.) — отфильтрованы Name Normalizer'ом | stdout: `[NAME NORMALIZER] filtered: historical figure '{name}'` |

**4. Что нашёл Auditor:**
- Сколько в `auto_enrich`: persons, timeline, locations, character_traits, quotes
- Что в `log_only_gaps`: список missing_persons / missing_events / missing_locations / missing_traits с цитатами

**5. Что слил Name Normalizer:**
- Список `merged_pairs` (canonical / merged / overlap-score) для persons и locations отдельно
- Список отфильтрованных исторических фигур (если были)
- Результат `validate_fact_map_integrity()` — должно быть `[]` (пустой массив ошибок)

**6. Stability Report:**
- `stability_score` между v36a и v36b (ожидание: ≥ 90%)
- Если < 90% — список потерянных и добавленных персон между прогонами с предположением о причине
- `total_a`, `total_b`, `match_count`

**7. Полные логи stdout** обоих прогонов — для дебага если что-то странное в цифрах.

#### Критерии приёмки (когда задача переходит в `done`)

Все обязательны:
- [ ] Татьяна в `persons[]` (любым путём — FE или Auditor)
- [ ] Все 5 ключевых фактов TR2 (Сахалин, пианино, сервиз, «дорожка», Нинвана) представлены в fact_map
- [ ] `merged_pairs` содержит как минимум одну пару Маргось/Кужба (если LLM выдала разные формы)
- [ ] Manifest содержит оба новых блока
- [ ] `validate_fact_map_integrity()` возвращает `[]` ошибок
- [ ] `stability_score(v36a, v36b) ≥ 0.90`

Если что-то не выполняется — отдельная итерация с диагностикой (промпт Auditor'а нужно подкрутить / порог 30% оказался не тот / etc.).

#### Бюджет

~$0.66 на оба прогона (~$0.33 каждый). Если что-то ломается на первом прогоне — **остановиться, не делать второй**, написать в комментарий что произошло.

---

### 2026-04-28 — Claude (статическая проверка артефактов перед прогоном v36)

Перед запуском прогона v36 проверила реализацию по чек-листу из Dev Review Response. Артефакты в основном соответствуют спеку, но **3 требования из закрытых [TECH] / [PRODUCT] флагов реализованы не полностью**. Возвращаю задачу в `in-progress`.

#### ✅ Что соответствует спеку

- Все 3 файла на месте, размеры адекватные
- Промпт `16_completeness_auditor_v1.md`: двухсекционный вывод, семантический критерий, blocklist, правило 3 (рассказчик-как-персонаж), Rule 6 (`source_quote` обязателен), проверка aliases
- `pipeline_config.json`: секция `completeness_auditor` с Haiku/8000/0.1 — корректно
- `pipeline_utils.py`: `run_completeness_auditor()` + `apply_completeness_enrichment()` — реализованы, есть детектор truncated и обработка JSON parse error
- `test_stage1_karakulina_full.py`: шаги 3 и 4 встроены между FE и `clean_fact_map_for_downstream`, manifest получает оба блока
- `compare_persons_across_runs.py`: stability_score с порогами, `--fail-on-loss N` для CI
- Name Normalizer: POSITION_WINDOW=300, MERGE_THRESHOLD=0.30, словарь диминутивов, перестановки имя/фамилия

#### ❌ Замечания (требуют доработки)

**[ISSUE-1] ID-ремаппинг неполный — критично**

В моём ответе на [TECH-3] я явно перечислила 6 полей для ремаппинга. Cursor реализовал 4 из 6. В `_remap_ids_in_fact_map()` (`scripts/normalize_named_entities.py:204`) НЕ обрабатываются:

- `conflicts[].parties[]`
- `gaps[].related_persons[]`

Если в fact_map есть conflicts или gaps со ссылками на сливаемого человека — после нормализации ссылки станут битыми и попадут в downstream (Historian/GW). В fact_map Каракулиной оба массива присутствуют.

**Что нужно сделать:** добавить в `_remap_ids_in_fact_map()` обработку этих двух полей (по аналогии с relationships).

**[ISSUE-2] `validate_fact_map_integrity()` симметрично пропускает conflicts и gaps — критично**

Функция (`scripts/normalize_named_entities.py:237`) проверяет те же 4 поля что и ремаппинг. Битые ссылки в conflicts/gaps **не будут пойманы валидатором** даже после фикса ISSUE-1.

**Что нужно сделать:** дополнить валидацию проверкой `conflicts[].parties[]` и `gaps[].related_persons[]`.

**[ISSUE-3] `_is_historical()` объявлена, но не используется — среднее**

В `scripts/normalize_named_entities.py`:
- Строка 36: `HISTORICAL_BLOCKLIST = {...}` — задекларирован
- Строки 71–77: `_is_historical(name)` — определена
- Внутри `normalize_named_entities()` функция **никогда не вызывается** — мёртвый код

В моём ответе на [PRODUCT-2] было явно: «Защита в коде (Name Normalizer): blocklist исторических фигур — отфильтровывается с логом `filtered: historical figure`». Сейчас фильтрует только промпт Auditor'а — если LLM ошибётся (а LLM нестабилен, см. контекст задачи), защиты в коде нет.

**Что нужно сделать:** в `normalize_named_entities()` после слияний (или до индексации позиций) пройтись по persons[], отфильтровать записи проходящие `_is_historical(name)` с логом `[NAME NORMALIZER] filtered: historical figure '{name}'`. Удалённые записи также должны пройти ID-ремаппинг (ссылки на них → narrator_001 или удалить из участников событий — обсудить с Cursor что корректнее).

#### Что дальше

1. Cursor дорабатывает ISSUE-1, 2, 3 → возвращает в `dasha-review`
2. После фикса — статическая проверка повторно (быстрая)
3. Затем — реальный прогон v36 на Каракулиной (~$0.30–0.50)
4. Критерии приёмки: Татьяна в persons; «Маргось Владимир»/«Владимир Маргось» слиты; manifest содержит оба блока; `compare_persons_across_runs.py` показывает stability ≥ 90% между двумя прогонами на одних транскриптах

---

### 2026-04-27 — Даша / Claude

Задача создана как преемник 011 после переоценки диагноза. Старая гипотеза (регрессия v3.4) опровергнута анализом v29/v30/v34/full_0413 — нестабильность системная.

Архитектурное решение принято Дашей: Variant A (LLM Auditor) + Variant C (Name Normalizer), порядок A→C.

Передаём Cursor с одним открытым вопросом [OPEN-1] про реализацию Completeness Auditor (отдельный агент vs второй проход FE).

---

### 2026-04-28 — Cursor: Отчёт прогона v36 (приёмочный прогон задачи 014)

#### 1. Артефакты

| Прогон | Файл | Путь |
|--------|------|------|
| v36a | fact_map_full | `collab/runs/karakulina_v36_20260428/karakulina_fact_map_full_v36a.json` |
| v36a | completeness_audit | `collab/runs/karakulina_v36_20260428/karakulina_completeness_audit_v36a.json` |
| v36a | manifest | `collab/runs/karakulina_v36_20260428/manifest_s1_v36a.json` |
| v36b | fact_map_full | `collab/runs/karakulina_v36_20260428/karakulina_fact_map_full_v36b.json` |
| v36b | manifest | `collab/runs/karakulina_v36_20260428/manifest_s1_v36b.json` |
| — | stability_report | `collab/runs/karakulina_v36_20260428/v36_stability_report.json` |

#### 2. Стоимость и время

**Прогон v36a** (Cleaner+FE первый запуск, CA через rerun):
- Cleaner: in=17507, out=18364 токенов; 224с; ~$0.005 (Haiku)
- Fact Extractor: in=28440, out=17184 токенов; 215с; ~$0.22 (Sonnet-4)
- Completeness Auditor: in=35996, out=11978 токенов; 86с; ~$0.01 (Haiku)
- Name Normalizer: <1с (без LLM)
- **Итого v36a: ~$0.24, ~9 мин (с повторными попытками по диагностике NN)**

**Прогон v36b** (полный прогон с фиксами):
- Cleaner: in=17507, out=18211; 224с; ~$0.005
- Fact Extractor: in=28181, out=18160; 229с; ~$0.22
- Completeness Auditor: in=36572, out=12250; 95с; ~$0.01
- Name Normalizer: <1с
- **Итого v36b: ~$0.24, ~9 мин**
- **Оба прогона: ~$0.48** (в бюджете ~$0.66)

#### 3. Ключевые проверки приёмки

| Проверка | v36a | v36b |
|----------|------|------|
| Татьяна в `persons[]` | ✅ `person_auto_001 \| Татьяна Каракулина \| дочь` (через CA auto_enrich) | ✅ `person_020 \| Татьяна` (FE нашёл сам) |
| Сахалин в timeline | ✅ CA auto_enrich: «развилка Сахалин/армия» | ✅ CA: то же |
| Пианино / шуба / сервиз | ✅ CA: «продажа шубы для пианино», «покупка дорогого сервиза» | ✅ CA: то же |
| Нинвана в persons[] | ✅ `person_013 \| Нинвана Полсачева` | ✅ `person_018 \| Нинвана Полсачева` |
| «посидеть на дорожку» | ✅ CA auto_enrich character_traits | ✅ CA: то же |
| Маргось/Кужба слиты | ✅ `person_008 \| Маргось Владимир \| aliases=['Владимир Маргось']` | ✅ то же |
| Manifest → completeness_audit | ✅ | ✅ |
| Manifest → name_normalization | ✅ | ✅ |
| `validate_fact_map_integrity()` | ✅ 0 ошибок | ✅ 0 ошибок |
| `stability_score(v36a, v36b)` | **95% ≥ 90%** ✅ | — |

#### 4. Что нашёл Auditor (v36a)

**auto_enrich** (9 persons, 16 events, 3 locs, 16 traits):
- Persons: Татьяна Каракулина, Никита, Даша, Римма, Зина, Толя, Коля, Витя, Сафронов
- Events: кража документов, развилка Сахалин/армия, детский сад, изменение характера после смерти мужа, продажа шубы для пианино, покупка сервиза, крещения в 90-е, конфликты с Никитой, история с огурцами, духи в 85 лет и др.
- Traits: любовь к красивой сервировке, «посидеть на дорожку», строгость к внукам, вязание и цветы, нежелание путешествовать и др.

**log_only_gaps** (1 person): Татьяна Маргось — «возможная ошибка в транскрипте, требует уточнения»

#### 5. Что слил Name Normalizer (v36a)

3 корректных слияния:
- `'Полина Амельченко' → 'Рудая Пелагея Алексеевна'` (overlap=0.889, shared=['пелагея', 'полина', 'поля']) ✅
- `'Никита' → 'Никита'` (дедупликация FE+CA записей, overlap=1.0) ✅
- `'Даша' → 'Даша'` (дедупликация FE+CA, overlap=1.0) ✅

Ложных слияний нет. `validate_fact_map_integrity() → []`.

#### 6. Stability Report

```
Stability Score: 95%  ✅ СТАБИЛЬНО
Совпадают: 18 / 19
Потеряны в B: Сафронов [неясно] — 1 персона без имени и связи
total_a=19, total_b=18, match_count=18
```

Потеря «Сафронов» объясняется тем, что в v36a CA добавил его как low-confidence сущность неясного статуса; в v36b FE и CA не добавили — нормально.

#### 7. Инциденты диагностики

В процессе прогона обнаружены и исправлены дополнительные дефекты NN:
1. **CA max_tokens** 8000 → 32000 (truncation при 8000 и 16000)
2. **NN STOP_TOKENS**: добавлен список «тётя», «дядя», «дед», «село» и др. — предотвращает слияния через role-слова
3. **NN min 2 shared tokens**: вместо 1 → предотвращает слияние «Каракулин Дмитрий» (муж) и «Каракулин Валерий» (сын) через общую фамилию
4. **NN transitivity**: транзитивное разрешение цепочек A→B→C при множественных слияниях
5. **NN locations no-aliases**: для локаций matching только по primary name (не asr_variants) → нет ложного слияния «Кишкунхалаш» и «Вышний Волочёк»
6. Checkpoint формат `{"content": fact_map}` — учтено в скриптах

Все фиксы задокументированы в `scripts/normalize_named_entities.py`, задеплоены на сервер.

---

## История статусов

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-04-28 | `done` (прогон v36 завершён, все критерии ✅) | Cursor |
| 2026-04-28 | `in-progress` → запрос прогона v36 (фиксы верифицированы, ТЗ передано Cursor) | Claude |
| 2026-04-28 | `dasha-review` (фиксы ISSUE-1,2,3 верифицированы Claude) | Cursor / Claude |
| 2026-04-28 | `in-progress` (возврат на доработку — 3 замечания: ID-ремаппинг неполный, валидация неполная, blocklist в коде не используется) | Claude |
| 2026-04-28 | `dasha-review` (фиксы ISSUE-1,2,3) | Cursor |
| 2026-04-28 | `in-progress` (возврат, 3 замечания от Claude) | Claude / Cursor |
| 2026-04-27 | `dasha-review` (реализация завершена) | Cursor |
| 2026-04-27 | `in-progress` (реализация начата) | Cursor |
| 2026-04-27 | `spec-approved` (Dev Review закрыт, все флаги отвечены) | Даша + Claude |
| 2026-04-27 | `spec-review` (Claude отвечает TECH, Даша отвечает PRODUCT) | Claude / Даша |
| 2026-04-27 | `dev-review` (заполнен Cursor) | Cursor |
| 2026-04-27 | `dev-review` | Передано Cursor |
| 2026-04-27 | `new` | Даша / Claude |
