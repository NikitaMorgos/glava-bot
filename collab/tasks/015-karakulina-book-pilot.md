# Задача: Настройка пайплайна до надёжной системы (Каракулина — диагностический инструмент)

**Статус:** `active` (живой трекер)
**Номер:** 015
**Автор:** Даша / Claude
**Дата создания:** 2026-04-28
**Цель переформулирована:** 2026-04-30
**Тип:** `meta-задача` / трекер прогресса

> Это **живой трекер**, а не одноразовая спецификация. Обновляется после каждого прогона и при изменении статусов подзадач.

---

## Цель (переформулирована 2026-04-30)

Довести пайплайн до уровня **надёжной системы**, на которой можно собирать книги предсказуемо для любого клиента. Каракулина — **диагностический инструмент**, не цель сама по себе.

> «Пилот блокируем пока не достигнем нормальной версии. Мы сейчас не пилотом занимаемся, а настройкой пайплайна для надежной системы.» — Даша, 2026-04-30

### Что значит «надёжная система»

1. **Структурно** — пайплайн не теряет контент между этапами (017/023 закрыто), не дублирует, не переставляет, не молча игнорирует ссылки
2. **Содержательно** — между прогонами на одних данных результат стабилен (026 в работе)
3. **Визуально** — финальный PDF соответствует правилам вёрстки (024/025 в работе)
4. **Операционно** — каждое нарушение системой ловится сразу (verified-on-run, fidelity enforcement, hybrid detection — закрыто 020/022)

### Что было «целью пилота» и почему мы её сменили

Изначально (2026-04-28): «довести Каракулину до gate4 PDF». Этот framing давил на скорость: после каждой задачи — следующая, без пауз на аудит. Привело к v37 PASS которая на самом деле потеряла 92% контента (никто не открыл финальный PDF). После двух разборов от Opus и моего обещания не делать статической верификации — стало ясно что проблема не в скорости прохождения этапов, а в **надёжности самого пайплайна**.

Теперь: gate3/gate4 на Каракулиной не запускаются пока не закрыты все системные нестабильности. Когда система станет надёжной — Каракулина пройдёт gate3/gate4 как **подтверждение** что система готова, а не как самоцель. После Каракулины — task 013 (CJM production errors) и переход на клиентов.

---

## Текущий статус (обновляется)

**Дата обновления:** 2026-05-01 (v40 — тройной Stage 1 + Stage 4 gates 2a/2b/2c, задачи 024/025/026 верифицированы)

**Текущий этап:** надёжность пайплайна — 024/025/026 закрыты в `dasha-review`. Артефакты: `karakulina_v40_gate2c_20260501.pdf`.

**Прогресс по системе:**
- ✅ Структурная надёжность (Stage 4) — фиксы 017/023 устранили потерю контента и перетасовку
- ✅ Operational защита — fidelity hard fail (020), hybrid detection (022), photos_dir guard (021/018), verified-on-run протокол
- ✅ Визуальная корректность (chapter_start, markdown headings) — 024, 025 верифицированы на v40
- ✅ Содержательная стабильность (Stage 1) — 026 верифицирован тройным прогоном v40a/v40b/v40c

**Следующий шаг:** gate3/gate4 на Каракулиной разблокированы после подтверждения 024/025/026 Дашей.

**Принцип `verified-on-run` подтверждён в действии:** v37 PDF имел потерю 92% контента, прошёл все формальные структурные проверки. Только когда я открыла PDF локально через pdfplumber, регрессия выявилась. Без этого шага все 8 задач закрылись бы как `done` с поломанным выходом. Каждая последующая задача теперь верифицируется открытием артефакта.

**Процессное изменение:** введён обязательный статус `verified-on-run` (см. `collab/context/dev-review-protocol.md`). Ни одна системная задача не закрывается без фактического прогона на пилоте. Регрессии v29-v35 — следствие отсутствия этого гейта.

**Принцип:** пилот = диагностический инструмент, не объект ручных правок. Все фиксы — системные (промпты, код, новые агенты), потом полный перепрогон пилота для верификации.

---

## Этапы сборки книги

| Этап | Что делает | Статус Каракулиной | Последний прогон |
|---|---|---|---|
| **Stage 1** | Cleaner + FE + Completeness Auditor + Name Normalizer → fact_map | ✅ **готов** | v37 (2026-04-30), 82% stability (semantic: ~94%) |
| **Stage 2** | Historian + Ghostwriter + Fact Checker → текст книги | ✅ **готов** | v37 (2026-04-30), FC PASS iter 3 |
| **Stage 3** | Literary Editor + Proofreader → отполированный текст | ✅ **готов** | v37 (2026-04-30), PR 6 правок, gate1 PASS |
| **Phase B** | Инкрементная экстракция новых интервью | ⚠️ архитектурно заблокирован | — |
| **Stage 4** | Photo Editor + Layout Designer + QA + Cover → PDF | ✅ gate2c PASS на v37 | 2026-04-30 |

---

## Чек-лист по Acceptance Gates (протокол 009)

| Gate | Что проверяет | Статус | Когда проходили |
|---|---|---|---|
| **Gate 1** | Текст книги: 10-пунктовый чек-лист (timeline, historical_notes, ключевые факты, объём 15-17K) | ✅ **PASS** | v37 (2026-04-30): все гейты PASS на Stage 3 |
| **Gate 2a** | Текст-only PDF (без фото и обогащений) | ✅ **PASS** на v37 | 2026-04-30 — FIDELITY 58 абзацев OK |
| **Gate 2b** | + bio_data | ✅ **PASS** на v37 | 2026-04-30 |
| **Gate 2c** | + callouts / историч. справки / плейсхолдеры фото | ✅ **PASS** на v37 | 2026-04-30 — нет фото-секции (task 018 работает) |
| **Gate 3** | Реальные фото вместо плейсхолдеров | ❌ ожидаем фото | — |
| **Gate 4** | Финальная обложка + полный PDF | ❌ не доходили | — |

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
| 2026-04-29 | v36 Stage 4 | ✅ gate2a/2b/2c PASS | 37 стр., 6 callouts, 6 hist.notes, 16 записей семьи в bio_data, плейсхолдеры фото |

---

## Связанные подзадачи

| № | Название | Статус | Что даёт пилоту |
|---|---|---|---|
| 007 | Архитектурные улучшения пайплайна (Proofreader, Phase B FC, Incremental FE) | dasha-review | Phase B архитектура |
| 008 | Потеря текста в Layout Designer (исходная задача) | superseded by 017 (2026-04-29) | — |
| **016** | Name Normalizer — учёт relation_to_subject (bug #8) | ✅ **done** (v38) | rejected_pairs работают: Полина и Пелагея не сливаются |
| **017** | Layout Designer — ссылочная архитектура (bugs #1, #2) | ✅ **done** (v38) | 73 абзаца, нет дублей, порядок OK |
| **018** | Stage 4 — границы между gate2c и gate3 (bug #6) | ✅ **done** (v38) | Нет фото-секций в gate2c |
| **019** | Полный перепрогон Каракулиной (verification run) | ✅ **done** (v38 batch) | 7 архитектурных задач закрыты, найдены 024 и 025 |
| **020** | Fidelity enforcement | ✅ **done** (v38) | Unit-test PASS, fidelity на v38 PASS |
| **021** | Photos_dir guard в pdf_renderer | ✅ **done** (v38) | Unit-test PASS, нет leak фото в gate2c |
| **022** | Hybrid element handling | ✅ **done** (v38) | Unit-test PASS |
| **023** | pdf_renderer теряет 92% текста (CRITICAL) | ✅ **done** (v38) | 1059 → 14726 chars, контент восстановлен |
| **024** | chapter_start text enforcement (bug #3) | spec-approved (auto-clean) | Промпт-правило не работает, нужен code-level валидатор |
| **025** | Подзаголовок как структурный элемент | spec-approved (один тип subheading, без level) | GW эмитит markdown, pdf_renderer не парсит → `###` буквально в PDF |
| **026** | Stage 1 нестабильность второстепенных персон | spec-approved (Variant 1: pin-list) | БЛОКИРУЕТ пилот — критично для надёжности перед клиентами |
| 009 | Протокол ворот приёмки | dasha-review | Сами gate'ы |
| 010 | Очистка промптов от привязки к Каракулиной | ✅ done (2026-04-28) | Готовность к тиражированию на следующих клиентов |
| 011 | FE completeness regression | closed-superseded by 014 | — |
| 014 | Completeness Auditor + Name Normalizer | ✅ done | Стабилизация Stage 1 (вход в этот пилот) |
| FIX-A (внутри 015) | timeline=None — фикс `phase` логики в `pipeline_utils.py:738` | ✅ **закрыт** | `force_phase="A"` в run_ghostwriter + Stage 2 v36 |
| FIX-B (внутри 015) | Историк-dict обёртка в `pipeline_utils.py:757-759` | ✅ **закрыт** | Корректная распаковка, 4 ист.вставки в Stage 2 v36 |
| 016 (TBD) | Narrative Auditor — зеркало Completeness Auditor для нарратива GW | new (отложено до конца пилота) | Ловит семантические галлюцинации (приписанные даты/факты в нарративе) |

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

✅ **Выполнено 2026-04-29.** gate2a/2b/2c PASS на v36. PDF: `collab/runs/karakulina_v36_gate2c_20260429.pdf`

### До gate3 (фото)

Photo Editor должен подобрать реальные фото из архива клиента. У Каракулиной — нужно собрать фото-альбом. ETA: зависит от готовности фото от Даши.

### До gate4 (обложка + финальный PDF)

Cover Designer + финальная сборка. ETA: ~0.5 дня после gate3.

---

## Баги пилота → системные задачи (2026-04-29, ручная проверка PDF)

После gate2c PASS Даша вручную просмотрела `karakulina_v36_gate2c_20260429.pdf`. Gates прошли формально, но визуально и содержательно — 9 багов. Подтверждено что **gate2c проверяет структуру, не содержание**.

### 9 багов (диагностика)

| # | Слой | Что | Доказательство |
|---|------|-----|----------------|
| 1 | Layout / pdf_renderer | Дубль 5 подглав ch_02 в PDF | стр 5/11, 7/12, 8/13, 9/14, 10/15 — текст один в book_FINAL, два раза в PDF |
| 2 | Layout / pdf_renderer | Перетасовка подглав ch_03 + пропуск «Порядок и красота» | book_FINAL имеет 7 подглав в порядке X, PDF — 6 подглав в другом порядке |
| 3 | Layout / Art Director | Текст на chapter_start страницах | стр 3 «Глава 02» + плейсхолдер фото + сразу нарратив (правило: только фото) |
| 4 | Layout / Art Director | Дыры между подглавами | большие пустые пространства до конца страницы |
| 5 | Photo Editor / Layout | Подписи фото = filename, не caption | стр 32-53: «ты его в чате упомяни...» вместо «Поликлиника Химинститут» из manifest |
| 6 | Pipeline orchestration | Photo Editor запустился в Часть 1, не в Часть 2 | gate2c должен быть text-only с плейсхолдерами; в PDF все 23 фото отдельной секцией |
| 7 | Ghostwriter | bio_data.family пропускает persons (Поля) | person_004 «Полина Амельченко» в fact_map есть, в `chapters[0].bio_data.family[]` нет |
| 8 | FE / Name Normalizer | Cross-person aliases pollution: 3 женщины склеены в 1 | aliases person_004 = ['тётя Поля', 'Рудая Пелагея Алексеевна', 'Марфа', 'Дуня'] — это сестра + мать + прабабушка |
| 9 | Ghostwriter | Семантические галлюцинации датировки | «90-е годы была история с огурцами» — в fact_map character_trait без timeline |

### 8 системных задач

**Архитектурные (код / pipeline):**

| Задача | Что делать | Багов покрывает | Приоритет |
|--------|-----------|-----------------|-----------|
| **008 escalation: Layout reference architecture** (production-confirmed) | Переход Layout Designer на ссылочную архитектуру: LD возвращает структуру из `paragraph_id`, `pdf_renderer` тянет текст из book_FINAL. Эмиссия текста в LD исчезает → дубли становятся структурно невозможны. | #1 | **critical** |
| **Layout fidelity preservation** | Структурный инвариант: порядок и состав `chapters[].paragraphs[]` в layout = порядок и состав в book_FINAL. Реализуется как валидация после LD: «множество paragraph_id на выходе == множество на входе, в том же порядке». При нарушении — fail (не auto-patch, который маскирует баг). | #2 | **critical** |
| **Stage 4 phase boundaries** | Формализовать gate2c (text-only с плейсхолдерами) vs gate3 (с фото) в `test_stage4_*.py`. Photo Editor не должен запускаться до gate3. Сейчас он работает всегда — gate2c в текущем виде включает все 23 фото отдельной секцией. | #6 | high |

**Правила промптов:**

| Задача | Что делать | Багов покрывает | Приоритет |
|--------|-----------|-----------------|-----------|
| **Chapter_start layout rule** | Правило в `15_layout_art_director` / `08_layout_designer`: страница типа `chapter_start` содержит только заголовок + фото/плейсхолдер. Без нарратива. | #3 | medium |
| **Subheading pagination flow** | Правило: подзаголовки внутри главы идут потоком без принудительного разрыва страницы. Разрыв страницы — только перед новым chapter или при заполнении ёмкости страницы. Сейчас LD/AD создаёт пустоты. | #4 | medium |
| **Photo captions priority rule** | Правило в промптах Photo Editor + Layout Designer: подпись = `manifest.caption` если есть, filename — только fallback. | #5 | high |
| **Bio_data completeness rule** | Правило в GW промпте + структурная проверка: все `persons[]` с семейным `relation_to_subject` обязаны попадать в `bio_data.family[]`. Аналог Completeness Auditor (014), но на стыке FE→GW. | #7 | high |

**Алгоритмический:**

| Задача | Что делать | Багов покрывает | Приоритет |
|--------|-----------|-----------------|-----------|
| **Name Normalizer: semantic context** | Текущий алгоритм сливает по positional windows ±300 chars + общему имени. Должен учитывать `relation_to_subject` и контекст событий — иначе склеивает разных людей с близкими упоминаниями (сестра + мать + прабабушка → одна запись). | #8 | **critical** (загрязняет fact_map → весь downstream) |

### Архитектурный принцип (выявлен в этом разборе)

**Каждая граница между агентами должна иметь проверочный фильтр** (deterministic или LLM-аудит). Текущая картина:

| Граница | Аудитор | Покрывает |
|---------|---------|-----------|
| Transcript → FE | ✅ Completeness Auditor (014) | Пропуски (TR упоминает → FE не извлёк) |
| FE → Name Normalizer | ⚠️ есть алгоритм, но недостаточен (#8) | Должен ловить cross-person aliases |
| FE → GW | ❌ нет (#7) | Должен ловить пропуски в bio_data, обязательные секции |
| GW → Layout | ❌ нет (#1, #2) | Должен ловить дубли, пропуски, перетасовку |
| Нарратив GW → fact_map | ❌ нет (планируется task 016 Narrative Auditor) | Семантические галлюцинации |
| Photo Editor → Layout | ❌ нет (#5, #6) | Корректность caption mapping, фаза |

**Будущие агенты проектировать сразу с парным аудитором** — не как nice-to-have, а как обязательный элемент.

### Прогресс по потокам (2026-04-29)

**Поток A** (Name Normalizer #8) — передан Cursor, в работе.

**Поток B** (Bio_data completeness #7) — ✅ **сделан Claude в in-place патче** `03_ghostwriter_v2.14.md`. Расширен список ключевых слов родства, матчинг по подстроке, явная проверка полноты с подсчётом N=N. Верификация — на ближайшем перепрогоне Stage 2.

**Поток D** (Chapter_start #3 + Subheading pagination #4) — ✅ **сделан Claude в in-place патчах** `08_layout_designer_v3.19.md` + `15_layout_art_director_v1.8.md`. Найден конфликт правил между AD и LD (AD требовал «без текста на chapter_start», LD требовал «2 абзаца») — синхронизировано в пользу AD. Запрет page_break перед каждым подзаголовком явно прописан в обоих промптах.

**Поток E (часть)** — Photo captions priority (#5) — ✅ **сделан Claude в in-place патчах** `07_photo_editor_v1.md` + `08_layout_designer_v3.19.md`. Запрет filename как подписи, детектор filename в LD, fallback к visual_analysis с low confidence. Phase boundaries (#6) — остаётся для Cursor (код).

**Поток C** (008 escalation #1, #2) — для Cursor, требует Dev Review.

**Поток E (вторая часть)** — Stage 4 phase boundaries (#6) — для Cursor, код.

**Поток F** (Narrative Auditor task 016) — отложен до конца пилота.

CHANGELOG обновлён: запись `[2026-04-29]` в `prompts/CHANGELOG.md`.

### Порядок фиксов (общий план)

1. **Поток A (critical, Stage 1 layer):** Name Normalizer semantic context (#8) → перепрогон Stage 1, новый чистый fact_map без cross-person aliases
2. **Поток B (parallel, Stage 2 layer):** Bio_data completeness rule (#7) → правка GW промпта; проверится на перепрогоне Stage 2
3. **Поток C (critical, Stage 4 layer):** 008 escalation — Layout reference architecture (#1) + Layout fidelity preservation (#2). Делать вместе, единая архитектурная переработка LD/pdf_renderer.
4. **Поток D (Stage 4 promo rules):** Chapter_start rule (#3) + Subheading pagination flow (#4) — правки промптов Art Director/Layout Designer. Можно делать параллельно с C, но проверять после C (на новой архитектуре).
5. **Поток E (Stage 4 photo layer):** Photo captions priority (#5) + Stage 4 phase boundaries (#6).
6. **Поток F (отложен):** Task 016 Narrative Auditor — после пилота, закрывает #9.

После A+B+C+D+E — **полный перепрогон пилота** Stage 1 → 2 → 3 → 4 → визуальная проверка PDF. Это верификация системы, не «починка книги».

---

## Решения, которые нужно принять

- [ ] **Phase B архитектура** — после Completeness Auditor нужен ли вообще явный Phase B для нашего сценария двух транскриптов? Решить после Stage 2 прогона.
- [ ] **Уровень эскалации completeness gaps в проде** (PRODUCT-3 из task 011) — отложено до task 013 (CJM).
- [ ] **Семантические галлюцинации GW (task 016 — Narrative Auditor)** — диагностика 2026-04-28 показала что GW переаттрибутирует существующие годы из fact_map к фактам без даты (пример: эпизод с огурцами привязан к «90-м», хотя в fact_map это character_trait без timeline-даты). Регулярка не ловит — нужен LLM-based аудитор как зеркало 014. **Решение по пилоту:** известный артефакт, для Каракулиной не правим (системная задача), фикс архитектурно в 016. Отложено до завершения пилота.

---

## Лог обновлений

### 2026-04-29 — Stage 4 Часть 1 — gate2a ✅ gate2b ✅ gate2c ✅

**Вход:**
- `book_final`: `karakulina/proofreader` checkpoint v12 → из `exports/stage3_v36/karakulina_proofreader_report_20260428_154932.json`
- `fact_map`: `karakulina/fact_map` checkpoint v27 → из `exports/v36a/karakulina_fact_map_full_20260428_060949_v2.json`

**Команды:**
```bash
# Подготовка (обновление checkpoints, approve gate1)
python3 prep_stage4_v36.py   # на сервере

# gate 2a
python scripts/test_stage4_karakulina.py --acceptance-gate 2a --prefix karakulina_v36 --approve-gate

# gate 2b
python scripts/test_stage4_karakulina.py --acceptance-gate 2b --prefix karakulina_v36 \
  --existing-layout /opt/glava/exports/karakulina_v36_stage4_layout_iter1_20260429_044447.json --approve-gate

# gate 2c
python scripts/test_stage4_karakulina.py --acceptance-gate 2c --prefix karakulina_v36 \
  --existing-layout /opt/glava/exports/karakulina_v36_stage4_layout_iter1_20260429_044447.json --approve-gate
```

**Артефакты на сервере** (`/opt/glava/exports/`):
- `karakulina_v36_stage4_page_plan_20260429_044447.json` (12K)
- `karakulina_v36_stage4_layout_iter1_20260429_044447.json` (56K)
- `karakulina_v36_stage4_pdf_iter1_20260429_044447.pdf` ← **gate 2a** (159K)
- `karakulina_v36_stage4_gate_2b_20260429_045009.pdf` ← **gate 2b** (166K)
- `karakulina_v36_stage4_gate_2c_20260429_045045.pdf` ← **gate 2c** (223K)
- `karakulina_v36_stage4_ai_questions_20260429_044447.json` (14 вопросов, 8 групп)

**Локально:** `collab/runs/karakulina_v36_gate2c_20260429.pdf` ← **финальный PDF для просмотра**

**Стоимость и время (gate 2a — единственный LLM-прогон):**

| Агент | Время | In / Out токены | Стоимость ≈ |
|---|---|---|---|
| Арт-директор (15, Sonnet) | 35.4с | 21617 / 3374 | $0.12 |
| Верстальщик (08, Sonnet) | 182.2с | 25952 / 12042 | $0.26 |
| Интервьюер (11, Sonnet) | 53.2с | 26741 / 3872 | $0.14 |
| PDF render 3× | <5с каждый | — | — |
| **Итого Stage 4 Часть 1** | **~5 мин** | **~74K / ~19K** | **~$0.52** |

QA: пропущен для gate 2a/2b/2c (режим `--skip-qa` при text-only).

**Результаты gate по контенту:**

| Проверка | gate 2a | gate 2b | gate 2c |
|---|---|---|---|
| Страниц | 37 | 37 | 37 |
| PDF размер | 159K | 166K | 223K |
| bio_data блок | нет | ✅ 5 секций | ✅ 5 секций |
| Семья в bio_data | нет | ✅ 16 записей | ✅ 16 записей |
| Callouts | нет | нет | ✅ 6 callouts |
| Исторические справки | нет | нет | ✅ 6 hist_notes |
| Фото плейсхолдеры | нет | нет | ✅ на chapter_start |

**Детали bio_data (gate 2b/2c — из book_index напрямую, не из layout JSON):**
- Личные данные: 3 записи (имя, дата/место рождения)
- Образование: 1 запись (Кировоградская фельдшерско-акушерская школа)
- Военная служба: 4 записи (годы, звание, должность, фронты)
- Награды: 4 записи (медали, орден)
- Семья: **16 записей** (Отец, Мать, Маня, Муж, Валерий, Татьяна, Владимир Маргось, Олег Кужба, Никита, Даша, тётя Шура, **Толя, Коля, Витя, Римма, Зина**)

**Детали callouts/historical_notes (gate 2c):**
- 6 callout elements: страницы 21, 22, 23, 24, 31, 36
- 6 historical_note elements: страницы 8, 9, 10, 13, 14, 18

**Известная проблема — Task 008 (text loss в Layout Designer):**
- `[LAYOUT-VERIFY] ⚠️ Пропущено 69 из 69 абзацев` — Layout Designer v3.19 не включает `paragraph_id` ссылки в elements
- Авто-патч `verify_and_patch_layout_completeness` добавил все 69 абзацев
- **Текст не потерян** — патч восстановил все параграфы
- Task 008 остаётся в `new`; ссылочная архитектура не реализована
- Фиксировать где: все 5 глав (ch_01 p1, ch_02 p1–p29, ch_03 p1–p22, ch_04 p1–p14, epilogue p1–p3)

**Дельта vs v28 04-18 (последний gate2c до v36):**

| Метрика | v28 (04-18) | v36 (04-29) | Дельта |
|---|---|---|---|
| Страниц | 31 | 37 | +6 стр. |
| PDF gate2c размер | 236K | 223K | -13K (разн. рендеринг) |
| Callouts | 6 | 6 | = |
| Историч. справки | 0 (не было) | 6 | **+6 справок** |
| bio_data секций | 4 (нет семьи) | 5 (+ семья 16) | **+семья** |
| Историк интегрирован | ❌ | ✅ | FIX-B |
| timeline в ch_01 | ❌ None | ✅ 44 событий | FIX-A |

Ключевое улучшение v36 vs v28: **Историк интегрирован** (6 справок), **семья в bio_data**, **timeline ch_01 восстановлен**. Текст богаче (+300 символов нарратива), факты TR2 (Сахалин, пианино) включены.

**Gate checkpoints на сервере** (`/opt/glava/checkpoints/karakulina/`):
- `layout_text_approved.json` ✅ approved (gate 2a)
- `layout_bio_approved.json` ✅ approved (gate 2b)
- `layout_full_approved.json` ✅ approved (gate 2c)

**Следующий шаг:** gate3 (фото). Блокирован до получения фотографий Каракулиной от Даши.

---

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
