# Задача: Сборка книги Каракулиной — пилот до gate4

**Статус:** `active` (живой трекер)
**Номер:** 015
**Автор:** Даша / Claude
**Дата создания:** 2026-04-28
**Тип:** `meta-задача` / трекер прогресса

> Это **живой трекер**, а не одноразовая спецификация. Обновляется после каждого прогона и при изменении статусов подзадач. Закрывается только когда Каракулина пройдёт gate4 (готовый PDF).

---

## Цель

Довести пилотный проект «Каракулина Валентина Ивановна» до готовой книги (PDF) через все 6 gate'ов протокола приёмки (см. задача 009).

Это пилот, на котором отлаживается весь пайплайн. После gate4 на Каракулиной — переход к продакшен-флоу (task 013, 016 web orders).

---

## Текущий статус (обновляется)

**Дата обновления:** 2026-04-28 (Stage 3 PASS, gate1 after stage3 PASS ✅)

**Текущий этап:** Stage 3 ✅ → gate1 (after stage3) ✅ → **следующий: Stage 4 (вёрстка)**

**Блокеры:** нет. Двигаемся к Stage 4.

---

## Этапы сборки книги

| Этап | Что делает | Статус Каракулиной | Последний прогон |
|---|---|---|---|
| **Stage 1** | Cleaner + FE + Completeness Auditor + Name Normalizer → fact_map | ✅ **готов** | v36 (2026-04-28), 95% stability |
| **Stage 2** | Historian + Ghostwriter + Fact Checker → текст книги | ✅ **готов** | v36 (2026-04-28), 4 ист.вставки, FC PASS iter 2 |
| **Stage 3** | Literary Editor + Proofreader → отполированный текст | ✅ **готов** | v36 (2026-04-28), LE PASS, PR 6 правок, готово к вёрстке |
| **Phase B** | Инкрементная экстракция новых интервью | ⚠️ архитектурно заблокирован | — |
| **Stage 4** | Photo Editor + Layout Designer + QA + Cover → PDF | ✅ один раз проходили в v_stable | 04-09 |

---

## Чек-лист по Acceptance Gates (протокол 009)

| Gate | Что проверяет | Статус | Когда проходили |
|---|---|---|---|
| **Gate 1** | Текст книги: 10-пунктовый чек-лист (timeline, historical_notes, ключевые факты, объём 15-17K) | ✅ **PASS** | v36 (2026-04-28): 10/10 critical, FC PASS, bio_struct PASS, 4 ист.вставки |
| **Gate 2a** | Текст-only PDF (без фото и обогащений) | ✅ проходили | 04-14 |
| **Gate 2b** | + bio_data | ✅ проходили | v28 04-18 |
| **Gate 2c** | + callouts / историч. справки / плейсхолдеры фото | ✅ проходили (но потом откат) | v28 04-18 |
| **Gate 3** | Реальные фото вместо плейсхолдеров | ❌ не доходили | — |
| **Gate 4** | Финальная обложка + полный PDF | ❌ не доходили (был coverfix в 04-09, не gate4) | — |

---

## История регрессий (хронология)

| Дата | Версия | Что произошло |
|---|---|---|
| 2026-04-09 | v_stable | ✅ Stage4 + QA → PASS, обложка с coverfix |
| 2026-04-12 | runs | 🔴 Stage1-3 FAIL — Cleaner обрезал транскрипт (лимит токенов) |
| 2026-04-13 | runs | 🔴 Stage1-3 FAIL — Proofreader пустой JSON |
| 2026-04-14 062711 | — | 🔴 Stage2 FAIL — деплой: флаг `--variant-b` не на сервере |
| 2026-04-14 062711 | — | ✅ ПОЛНЫЙ ПРОГОН Stage1→4 с фото — gate2a артефакты готовы |
| 2026-04-17 | v27 | Phase B текст |
| 2026-04-18 | v28 | ✅ gate2b → gate2c (вёрстка с bio, callouts, справками); 6 итераций gate2b |
| 2026-04-20 | v29 | 🔴 gate1 FAIL — откат на текстовые ворота |
| 2026-04-20 | v30 | 🔴 gate1 FAIL |
| 2026-04-21 | v31 | 🔴 gate1 FAIL |
| 2026-04-21 | v32 | 🔴 gate1 FAIL |
| 2026-04-22 | v34 | 🔴 gate1 FAIL → анализ → v35 |
| 2026-04-23 | v35 | 🔴 gate1 FAIL: 3 критич. проблемы (timeline=None, Историк не мержится, факты TR2 потеряны) |
| 2026-04-28 | v36 Stage 3 | ✅ LE PASS + PR 6 правок, gate1 after stage3 PASS | 12716→13216 симв, 6 callouts, 6 hist.notes, style_passport 11 имён |

---

## Связанные подзадачи

| № | Название | Статус | Что даёт пилоту |
|---|---|---|---|
| 007 | Архитектурные улучшения пайплайна (Proofreader, Phase B FC, Incremental FE) | dasha-review | Phase B архитектура |
| 008 | Потеря текста в Layout Designer: ссылочная архитектура | new | Защита текста на Stage 4 |
| 009 | Протокол ворот приёмки | dasha-review | Сами gate'ы |
| 010 | Очистка промптов от привязки к Каракулиной | ✅ done (2026-04-28) | Готовность к тиражированию на следующих клиентов |
| 011 | FE completeness regression | closed-superseded by 014 | — |
| 014 | Completeness Auditor + Name Normalizer | ✅ done | Стабилизация Stage 1 (вход в этот пилот) |
| FIX-A (внутри 015) | timeline=None — фикс `phase` логики в `pipeline_utils.py:738` | ✅ **закрыт** | `force_phase="A"` в run_ghostwriter + Stage 2 v36 |
| FIX-B (внутри 015) | Историк-dict обёртка в `pipeline_utils.py:757-759` | ✅ **закрыт** | Корректная распаковка, 4 ист.вставки в Stage 2 v36 |

---

## Что осталось до каждого gate

### До gate1 (текст книги PASS)

1. ✅ Диагностика обоих багов получена и верифицирована (Cursor + Claude, 2026-04-28)
2. ✅ FIX-A выполнен (`force_phase` в `run_ghostwriter()`, commit b26059f)
3. ✅ FIX-B выполнен (распаковка historian-dict, commit b26059f)
4. ✅ Прогон Stage 2 на v36 fact_map — FC PASS на итерации 2, 4 ист.вставки
5. ⚠️ `gate_required_entities` падает — проблема в `pipeline_quality_gates.py`:
   - `critical_keywords` матчит "дочь" как подстроку в `relation_to_subject` племянников → ложно критические
   - gate не сканирует `bio_data.family` в ch_01 — там personы есть, но в структуре, не в тексте
   - **Варианты:** (a) фикс quality gate конфига — 30 мин; (b) запуск Stage 3 с `--no-strict-gates` и ручная проверка текста

### До gate2a/2b/2c (вёрстка)

После gate1 — прогнать Stage 4 без фото и без обложки. У нас уже проходили в апреле, должно сработать. Но fact_map изменился — могут вылезти новые edge-cases. ETA: ~1 день после gate1.

### До gate3 (фото)

Photo Editor должен подобрать реальные фото из архива клиента. У Каракулиной — нужно собрать фото-альбом. ETA: зависит от готовности фото от Даши.

### До gate4 (обложка + финальный PDF)

Cover Designer + финальная сборка. ETA: ~0.5 дня после gate3.

---

## Решения, которые нужно принять

- [ ] **Phase B архитектура** — после Completeness Auditor нужен ли вообще явный Phase B для нашего сценария двух транскриптов? Решить после Stage 2 прогона.
- [ ] **Уровень эскалации completeness gaps в проде** (PRODUCT-3 из task 011) — отложено до task 013 (CJM).

---

## Лог обновлений

### 2026-04-28 (поздний вечер) — Stage 3 PASS ✅, gate1 после Stage 3 PASS ✅

**Команда:**
```bash
python scripts/test_stage3.py \
    --book-draft /opt/glava/exports/stage2_v36/karakulina_book_FINAL_20260428_083959.json \
    --fc-warnings /opt/glava/exports/stage2_v36/karakulina_fc_report_iter2_20260428_083959.json \
    --fact-map /opt/glava/exports/v36a/karakulina_fact_map_full_20260428_060949_v2.json \
    --output-dir /opt/glava/exports/stage3_v36 --prefix karakulina
```

**Артефакты:** `collab/runs/karakulina_v36_20260428/` (book_FINAL_stage3_v36.json, liteditor_report.json, proofreader_report.json, FINAL_stage3_v36.txt, gate1_after_stage3.json)

**Стоимость и время:**

| Агент | Время | In / Out токены |
|---|---|---|
| Литредактор (Sonnet) | 149с | 26354 / 8874 |
| Корректор ch_02 (Sonnet) | 51с | 9732 / 5341 |
| Корректор ch_03 | 33с | 10006 / 4021 |
| Корректор ch_04 | 33с | 9446 / 3584 |
| Корректор epilogue | 23с | 8538 / 2577 |
| **Итого Stage 3** | **~5 мин** | **~64K / ~24K** (~$0.30 est.) |

**Дельта vs Stage 2:**
- Символов: 12716 → 13103 (LE, +387) → 13216 (PR, +113) = **+500 символов total**
- Глав LE отредактировал: 1/5 (ch_02)
- Глав PR исправил: 2/5 (ch_02 — 6 правок, остальные — 0)
- Callouts: 3 kept + 3 added = **6 callouts**
- Исторические вставки: 4 оригинальных (edited) + 2 added LE = **6 hist.notes** в итоге

**Правки Литредактора (9 записей в edits_log):**
- 3× `anti_cliche` — убраны клишированные зачины: «Трагедия обрушилась на семью» → исторический контекст голода 1933 в маркере `***...***`; обобщение о свадьбах → прямой факт; оценочное «1960-е были временем больших надежд» → убрано
- 3× `transition_fix` — улучшены переходы: добавлен контекст мобилизации медработников, пояснение об интернате в Венгрии
- 3× `callout_fix` — добавлены callouts ch_03/ch_04/epilogue

**Паспорт стиля Корректора (11 имён):**
- Субъект: Валентина Ивановна Рудая (Каракулина) — «Валентина Ивановна» / «Валентина»
- Нормализованы: Иван Андреевич Рудай (отец), Пелагея Алексеевна Рудая (мать), Полина/тётя Поля, Дмитрий Каракулин, Валерий, Татьяна, Владимир Маргось, Олег Кужба, Никита, Даша
- Топонимы: Химинститут с заглавной, тире длинное (—) в пунктуации, среднее (–) в диапазонах дат
- Никаких переименований vs Stage 2 — PR подтвердил консистентность

**Gate1 after Stage 3:**
- `passed: True` — 10/10 critical, 0 optional missing
- LE/PR ничего не сломали по сущностям

**Следующий шаг:** Stage 4 (вёрстка). Входной файл: `collab/runs/karakulina_v36_20260428/book_FINAL_stage3_v36.json`

---

### 2026-04-28 (ночь) — gate1 PASS ✅

**Quality gates фикс** (`pipeline_quality_gates.py`, commit 960f7d2):
- `_split_critical_optional_entities`: заменён substring-match на token-level + добавлены `INDIRECT_RELATION_MARKERS` (тёт/дяд/племянник/внук/двоюродн). Теперь "дочь тёти Поли" не помечает племянников как critical.
- `gate_required_entities`: расширен scan на `bio_data` (все sections) и `sidebars`. Отчёт теперь содержит `found_in: "narrative" | "bio_data" | "sidebars"` для каждой matched сущности.
- Добавлены хелперы `_bio_data_text()` и `_sidebars_text()`.

**Повторный прогон gate1** на `book_FINAL_stage2.json` (без перезапуска Stage 2):
- `passed: True`
- `critical_total: 10`, `critical_matched_total: 10`, `critical_missing: []`
- 3 персоны найдены в `bio_data` (а не в нарративе): Мария, Поля, Шура — периферийные родственники
- `optional_missing: []`

**Артефакт:** `collab/runs/karakulina_v36_20260428/gate1_recheck.json`

**gate1 PASS подтверждён без перезапуска Stage 2.** Следующий: Stage 3.

---

### 2026-04-28 (поздно вечером) — Stage 2 прогон v36 выполнен, FIX-A + FIX-B закрыты

**Прогон:** `stage2_v36` (2026-04-28, сервер `/opt/glava/exports/stage2_v36/`)

**Артефакты:**
- Историк: `karakulina_historian_20260428_083959.json` — 7291 out_tokens, 113с
- Черновик v1 (initial): `karakulina_book_draft_v1_20260428_083959.json` — 17399 tok, 239с
- Черновик v2 (historian integration): `karakulina_book_draft_v2_20260428_083959.json` — 18057 tok, **`Ист.вставок: 4`** ✅
- FC итерация 1: FAIL (2 critical, 8 major — пропущены племянники в ch_01, галлюцинации)
- Черновик v3 (after FC fix): `karakulina_book_draft_v3_20260428_083959.json`
- FC итерация 2: **PASS** ✅ (0 critical, 0 major, 2 warnings)
- Финальная книга: `karakulina_book_FINAL_20260428_083959.json` — 12716 символов, 5 глав, 3 выноски, 4 ист.вставки
- Text gates: `karakulina_stage2_text_gates_20260428_083959.json`
- Manifest: `karakulina_stage2_run_manifest_20260428_083959.json`

**Локальные копии:** `collab/runs/karakulina_v36_20260428/` (book_FINAL_stage2.json, stage2_text_gates.json, manifest_s2.json)

**Статус FIX-A и FIX-B:**
- ✅ **FIX-A ЗАКРЫТ** — добавлен `force_phase` в `run_ghostwriter()`, в Stage 2 передаётся `force_phase="A"`. `ch01_bio` gate: `has_bio_struct=true`. `Ист.вставок: 4` (было 0 в v35) — Phase A pass 2 работает корректно.
- ✅ **FIX-B ЗАКРЫТ** — historian-dict теперь корректно распаковывается. `ctx_list = historical_context["historical_context"]`, `era_glossary` отдельно. GW получает плоский массив periods с `suggested_insertions`.

**Gate1 чек-лист после Stage 2 v36:**

| Проверка | Статус | Деталь |
|---|---|---|
| FC PASS | ✅ | итерация 2 (0 crit, 0 maj) |
| `ch_01` имеет bio_struct | ✅ | `has_bio_struct=true`, `has_birth_year`, `has_birth_place` |
| Ист.вставки > 0 | ✅ | 4 вставки |
| cross_chapter_repetition | ✅ | 0 нарушений |
| required_entities (critical) | ❌ | 6 из 13 критических не в тексте: Мария, Римма, Зина, Толя, Коля, Витя |
| Объём глав | ⚠️ | ch_01: 0 симв (структурный, ожидаемо), ch_02: 5183, ch_03: 4078, ch_04: 2571 |

**Причина FAIL required_entities:**
- Мария/Римма/Зина/Толя/Коля/Витя — периферийные родственники (племянники, тётя Маня), добавлены CA в Stage 1
- Gate помечает их critical из-за подстроки "дочь" в поле `relation_to_subject` ("племянник, сын/дочь тёти Поли")
- В ch_01 они добавлены в `bio_data.family` (структура), а не в `content` (текст) — gate сканирует только content
- Это **двойная проблема quality gates**: (a) `critical_keywords` не учитывает контекст "дочь" в relation; (b) gate не сканирует bio_data.family
- **Это НЕ регрессия пайплайна** — два исходных бага FIX-A/FIX-B закрыты

**Следующий шаг:**
- Gate1 пройдёт после фикса `gate_required_entities` в `pipeline_quality_gates.py`:
  - Исключить `племянник/племянница/тётя/дядя` из critical_keywords (или уточнить как "прямые родственники субъекта")
  - ИЛИ добавить сканирование `bio_data.family[]` в `collect_required_entities`
- Это не блокирует движение к Stage 3 — можно запустить с `--no-strict-gates` для проверки текста.

---

### 2026-04-28 (вечер) — диагностика блокеров получена и верифицирована

Cursor (на стороне Никиты) провёл диагностику обоих багов с конкретными ссылками на код:

- **FIX-A:** `pipeline_utils.py:738` — `phase = "B" if (current_book is not None and call_type == "revision") else "A"` всегда уходит в B при revision+current_book. Промпт v2.14 ожидает Phase A pass 2 для historian-интеграции.
- **FIX-B:** `pipeline_utils.py:757-759` — historian-dict оборачивается в `[dict]` вместо распаковки. GW получает структуру без `suggested_insertions` на верхнем уровне.

Claude верифицировала оба диагноза самостоятельно (читала код + промпты GW v2.14 и Historian v3) — оба подтверждены. Зелёный свет на фиксы.

Оба фикса — однострочники в одном файле (`pipeline_utils.py`). Решено не выделять в отдельные task-файлы (016/017), а трекать как FIX-A / FIX-B внутри 015. По сложности это «fix, не feature».

Уточнение по FIX-A: предложен явный аргумент `force_phase` в `run_ghostwriter()` вместо неявной логики по `revision_scope.type` — сохраняет кейс «historian_integration на готовой книге = Phase B» для будущего.

**Следующий шаг:** Cursor делает оба фикса + Stage 2 прогон + gate1 чек, отчитывается в этот файл.

---

### 2026-04-28 — создан трекер (Claude)

Восстановили картину после долгого периода технических задач. Поняли что **Stage 1 в смысле fact_map дотюнен (v36)**, но **Stage 1 в смысле gate1 — нет** (последний gate1 PASS был в апреле на v_stable, потом серия регрессий v29-v35).

Идентифицированы 2 блокирующих технических бага (timeline + Историк). Передано Cursor на стороне Никиты — ждём ответ.

Создан этот трекер чтобы не теряться в технических деталях и видеть общий прогресс пилота.

---

## История статусов

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-04-28 | `active` (живой трекер создан) | Даша / Claude |
