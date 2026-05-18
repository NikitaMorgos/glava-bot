# Архитектурный stocktake — 2026-05-17 (после v56)

> **Цель:** перед следующей волной — посмотреть на 3 закрытых волны (Этап 1 + task 035 + task 036) и v54→v55→v56 как на лес, не как на деревья. Классифицировать остающиеся проблемы по **классам багов** (не по симптомам), приоритизировать по **универсальности** (работает для всех биографий, не только Каракулиной) и **скрипт-friendly** (минимум промптов).
>
> **Триггер:** правило 3 архитектора (stocktake каждые 2-3 волны без напоминания).
>
> **Автор:** Опус. Согласовано: Никита (go-feedback 2026-05-17 после личного чтения v56).

---

## 1. Где мы сейчас

**Закрыто (3 волны после RP-0):**
- Этап 1 — gate1 infrastructure (`build_gate1_full_text.py`), GW v2.17 ЗАПРЕТ 8 первый абзац, LE v3.1 + `preserve_chapter_structural_fields`.
- task 035 — Stage 1 split-extract (TR1 Phase A → TR2 Phase B → merge), CA v1.2 events pin-list.
- task 036 — GW v2.18: 5 стилистических фиксов (ЗАПРЕТ 8 на ВСЕ абзацы, СТОП-ФРАЗЫ +6, ЗАПРЕТ 9 X-по-Y, ЗАПРЕТ 10 вымышленные временные связки, characteristic words ≥3).

**Текущее состояние v56:** объём 16.5K (✅ в диапазоне 14-18K), family=22 (стабильно с v55), characteristic words 3/5 (✅ цель достигнута), pin-list эпизодов 4/9 закрыто (прогресс с 2/9), огурцы найдены и НЕ инвертированы (✅), но **5 структурных классов проблем остаются**.

**НЕ закрыто:** Ворота 1 PASS не достигнут. RP-1 tag не выставлен.

---

## 2. Тренды v54 → v55 → v56

| Метрика | v54 | v55 | v56 | v57 | v58c | Тренд |
|---|---|---|---|---|---|---|
| Total chars | 17 700 | 14 700 | 16 495 | 17 411 | 16 700 | ➡ |
| ch_02 chars | ? | ? | 6 278 | 8 006 | ~8 200 | ↗ |
| ch_03 chars | ? | ? | 3 929 | 4 105 | ~4 000 | ✅ |
| ch_04 chars | ? | ? | 1 831 | 1 478 | ~1 700 | ↘ потери (огурцы, карты, грибы) |
| epilogue chars | ? | ? | 939 | 945 | ~900 | ✅ |
| bio_data.family JSON | 18 | 23 | 22 | 19 | **16** | ❌ потери Марфа+Маня+Римма+Зина |
| bio_data.timeline этапов | ? | ? | 7 | 6 | **7 (markdown)** | ✅ структурно |
| Pin-list эпизодов закрыто (из 9 + extensions) | 0/9 | 2/9 | 4/9 | 4/9 | 6 новых ↑, 2 регрессии ↓ | ↗↘ микс |
| Characteristic words (из 5/6) | 0/5 | 2/5 | 3/5 | 3/5 | **5/6** ⭐ | ↗ |
| FC verdict | — | — | FAIL iter3 | FAIL iter1→финал чист | iter1 fail (по медалям/огурцы дубль), финал ОК | ↗ |
| LE structural preservation | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | ⚠️ код держит, промпт LE v3.1 не выучил |
| **historical_notes (field)** | ? | ? | 2 | 3 | **0** | ⬇⬇ регрессия v58 |
| CA auto_enrich timeline events | ? | ? | 12 | ? | **10** (потеряны огурцы/шуба/ложечки) | ⬇ регрессия (CA v1.3 over-strict) |

**Что v56 потерял из v55** (Дашин/Никитин feedback):
- В паспортичке: год смерти Дмитрия 1978, год пенсии 1994, год рождения Валерия, звание «Ударник» (в паспортичке, в нарративе есть), факт «разные отцы у Валентины и Полины»
- В нарративе: операция на желудке 1960 (после которой стала мало есть), хрущевское сокращение армии 1962, церковь во Власьево, раздел «строгость / забота / простые радости» (заменён на узкий «принципиальность»), упоминания возраста типа «в 40 лет начала работать», «N лет посвятила работе»

**Что v56 закрыл vs v55:**
- Огурцы НЕ инвертированы (v55: «восторг + январь», v56: конфликт, чемодан, Молдавия)
- Счётчик 1977 найден
- Нинвана Полсачева добавлена (ch_03)
- Слово «выковыривал» — в тексте
- ch_04 первый абзац — про шубу→пианино (конкретно, не пластиково)

---

## 3. 11 классов багов после v56 + v57

| # | Класс | Корень | Симптомы v57 | Тип фикса | v57 статус |
|---|---|---|---|---|---|
| **1** | CA/GW confabulation (description/мотивация/контекст) | CA v1.2 пишет в description причинные связки которых нет в source; GW добавляет общие комментарии без основания | Огурцы «потому что не привозит подарки» (v56) → свёрнуто (v57); «1990-е многие пожилые остаются одни» (v57 фантазия); «воевала за идеалы» (v57); «посидели на дорожку перед Германией» (v57 — TR1 говорит об общей традиции, не про 1946) | **скрипт-валидация** + промпт CA v1.3 | ⏳ Batch 2 task 038 |
| **2** | bio_data note volatility | GW по-разному переписывает notes на персонах между прогонами | v56→v57: «Полина забрала из детдома» → «жила в Старобельске» (разный смысл); потери notes на племянниках («сын тёти Поли») | **скрипт** required-fields + persona note preservation | ⏳ task 044 (расширение 039) |
| **3** | family attribution mismatch | CA лейблит relation_to_subject="тётя" для соседки (TR называет «тётя Маша»); whitelist пропускает | Тётя Маша всё ещё в v57 family; баба Аня (свекровь рассказчика) в render | **скрипт** manual override + ужесточить whitelist | ⏳ task 044 |
| **4** | ASR транслитерация топонимов | ASR ошибки через всю цепочку | v57: 0 находок старых форм | ✅ закрыто (task 040) |
| **5** | Episode regression vs pin-list | GW не имеет pin-list для Stage 2 | v57: операция желудок ✅ (вернулась из v55), но: дача продали ❌, ДК Синтетик ❌, карты/домино ❌, грибы+тётя Маша ❌, разные отцы ❌, шарлотка ❌, «французская бабушка» ❌, дороговизна 90-х ❌, Химинститут «типичный посёлок» (historical) ❌ | **скрипт** pin-list events + diff | ⏳ Batch 2 task 041 |
| **6** | Epilogue/intro пафосные обобщения | GW тяготеет к шаблонам | v57: «прошла долгий путь...», «идеалы за которые воевала», «передались следующим поколениям», «жизнь была наполнена служением людям» | **скрипт** stop-phrase grep + промпт | ⏳ Batch 2 task 043 |
| **7** | Geo/regional misattribution | GW делает региональные домыслы | v57: Химинститут «на окраине Калинина» — корректно | ✅ закрыто (GW сам) |
| **8** | Age markers underused | Возраст не вычисляется | v57: 4+ markers в нарративе, 36/36 timeline events | ✅ закрыто (task 042) |
| **9** | `historical_notes` field underutilization | GW кладёт справки inline | v57: 3 в field (vs 2 v56) | ↗ улучшение, но scope task 043 |
| **10** | **bio_data.timeline structural regression** | GW не имеет жёсткой схемы периодов биографии | v56 7 разделённых этапов → v57 6, склейка «1938-1945 Учёба и война» (упущены детали войны) | **скрипт** structural anchors per subject | ⏳ task 045 (новый) |
| **11** | **GW awkward formulation — частный пример вместо обобщения** | GW заменяет общую формулировку конкретным примером, теряя обобщение | v57: «не любил советы по электричеству или поездкам» (реально — не любил советы в принципе; электричество/поездки — примеры) | **частный случай Класса 1**; пометить в style guide + post-GW grep | ⏳ task 043 расширение |

**11 классов универсальны.** Из 11: **2 закрыто** (4, 8) Batch 1; **2 улучшилось но не closed** (7, 9); **7 остаются для Batch 2** (1, 2, 3, 5, 6, 10, 11). 0 чисто промптовых решений — все скрипт-first.

**Новые классы из v57 review Никиты:**
- Класс 10 (timeline structural regression) — структура паспортички деградирует между прогонами без явного скриптового guarda.
- Класс 11 (awkward formulation) — стилистический подкласс Класса 1.

**Новые классы из v58c review Никиты + diagnostic:**
- **Класс 12 — chronological inconsistency**: GW упоминает persons в event period где они ещё не родились или уже умерли. Пример v58: «1946-48 сидела с детьми» (Валерий родился 1948). Универсальный для всех биографий.
- **Класс 13 — discourse markers regression**: GW при сжатии нарратива убирает упоминания рассказчика («как вспоминает дочь», «по словам Татьяны»), что снижает теплоту/человечность. Каждая биография имеет своего rapporteur'а; markers должны сохраняться.
- **Класс 14 — pin-list event minimum depth violation**: pin-list даёт **выбор** какие эпизоды, но не **глубину**. GW может свести эпизод к 1 фразе → формально `coverage: full`, но информационно беднее предыдущей версии. Пример v58: шуба→пианино свёрнут до 1 предложения (vs v56 = 3 с цитатой). Универсальный — каждая биография имеет ключевые эпизоды с required `min_sentences`.

**Новые классы из v59 review Никиты:**
- **Класс 15 — temporal place naming**: советские города переименовывались (Калинин→Тверь 1990, Ленинград→СПб 1991, Куйбышев→Самара 1991). В нарративе про конкретный год должно быть **исторически корректное** имя. v59: «в Твери родилась дочь Татьяна» в 1956 — неверно (тогда Калинин). Универсально для всех советских/постсоветских биографий.
- **Класс 16 — contributors section** (продуктовое нововведение): каждая книга-биография имеет служебный раздел «Кто работал над этой Главой» с contributors (родственники/друзья субъекта, чьи воспоминания записаны). Универсально для жанра.

**Расширения существующих классов после v59:**
- **Класс 6 extended**: новые stop-phrase categories — `motivation_attribution_ideals` («верила в идеалы за которые воевала»), `unbroken_by_circumstances`, `that_is_how_X_passed`, `kept_until_end`, `survived_all_X`, `embraced_milestones`.
- **Класс 10 extended**: chapter sections anchors не только для timeline (ch_01), но и для ch_03 (portrait) / ch_04 (episodes). Пример v59: пропал раздел «Гостеприимство и кулинария» в ch_03.
- **Класс 12 extended**: внуки в chronology — birth_year inferred через parent.birth_year + 16 (для галлюцинаций типа «1973 встречала внучку Дашу из школы» где Даша ещё не родилась).
- **Класс 4 extended**: gazeteer морфологические формы (родительный, дательный... падежи русских топонимов). Пример v59: «из Сапонова» (родительный) не матчился с «Сапоново» в gazeteer.

**Дополнительно — спецификация формата (не баг):**
- Паспортичка: писать «родился» / «умер» полностью, не «р.» / «ум.». → task 043 + GW input schema. ✅ в v58 работает.

---

## 4. Whack-a-mole анализ

**Закрытые классы не возвращаются** (good):
- регрессии #1-#4 v43 (historical_notes, callouts dedup, огурцы deletion, документы dedup) — стабильно закрыты с v51+
- task 027 bio_data.family completeness — Татьяна больше не теряется
- task 036 стилистика (5 стоп-фраз, ЗАПРЕТ 8 первый абзац) — v56 чист

**Новые классы появляются как побочка предыдущих волн** (warning, но не классический whack-a-mole):
- task 035 CA enrich активнее → **CA confabulation в description** (Класс 1) проявился именно в v55-v56
- task 036 GW стиль убран → **emotional valence inversion** на огурцах v55 → **causal confabulation** v56 (это **тот же Класс 1** но в GW). Корень — в CA description.
- Этап 1 LE preserve код → **промпт LE v3.1 расслабился** (5/5 дропает поля, код держит). Класс «промпт не учится когда защита в коде» — отдельная семья проблем.

**Вывод:** не whack-a-mole, но **скрипт защищает класс надёжнее чем промпт**. Каждый раз когда защита промптовая — она «расслабляется» в следующем поколении промпта. Это **подкрепляет** решение «скрипт-first».

---

## 5. План задач (обновлён после v57)

### Batch 1 — ✅ ЗАКРЫТА (v57 verified)
- task 042 subject_age ✅
- task 040 ASR normalize ✅
- task 039 bio_data integrity — частично (Марфа в render, не в JSON; тётя Маша всё ещё в family)

### Batch 2 — ⚠️ ЧАСТИЧНО ЗАКРЫТА (v58c verified)

| Task | Класс | Тип | v58 результат |
|---|---|---|---|
| **044 — family whitelist hotfix + manual override** | 3 | скрипт | ✅ тётя Маша/баба Аня НЕТ; но Марфа/Маня/Римма/Зина отсутствуют |
| **038 — CA strict description + confabulation guards** | 1 | промпт CA + скрипт | ⚠️ critical=0, но **CA over-strict** — пропустил огурцы/шубу/ложечки auto_enrich |
| **041 — pin-list events для GW + diff-валидация** | 5 | промпт GW + скрипт | ⚠️ парсер ОК, но Stage 1 runner не подал pin-list в CA → события не extract |
| **043 — epilogue stop-phrases + format spec («родился»/«умер»)** | 6 + 11 + формат | скрипт + минор промпт | ⚠️ paspart ✅, но detector не ловит падежи; GW v2.19 не выучил ЗАПРЕТЫ |
| **045 — bio_data.timeline structural anchor** | 10 | скрипт | ⚠️ JSON array пуст; markdown имеет 7 периодов, скрипт смотрит JSON → 0/7 |

### Batch 2-fix — точечные доработки для v59

**Главное открытие после v58c diagnostic:** корень регрессий — **CA v1.3 over-strict + Stage 1 runner не подал pin-list в CA**, не парсер pin-list (он работает).

| Task | Что | Тип | Сложность |
|---|---|---|---|
| **[041b](../tasks/041b-stage1-pinlist-events-required.md)** | Stage 1 runner: обязательная подача `--known-episodes` в CA | скрипт | `xs` |
| **[038b](../tasks/038b-ca-strict-bypass-for-pinlist.md)** | CA v1.3 → v1.4: bypass strict для pin-list events (ПРАВИЛО 6) | промпт CA + скрипт | `s` |
| **[044b](../tasks/044b-ca-required-persons-pinlist.md)** | CA required persons: Марфа, Маня, Римма, Зина — force extract | конфиг + скрипт | `xs` |
| **[045b](../tasks/045b-timeline-anchors-markdown-parser.md)** | Timeline anchors — парсить markdown ch_01.content (fallback от JSON) | скрипт | `s` |
| **[043b](../tasks/043b-stop-phrases-lemmatize.md)** | Stop-phrases lemmatize (падежи) + narrative categorical anti-triggers | скрипт + конфиг | `s` |
| **[046](../tasks/046-epilogue-auto-rewrite.md)** | Epilogue auto-rewrite — generic mapping stop→delete (был мой нерешённый loop в 043) | скрипт | `xs` |
| **[047](../tasks/047-text-full-summary-header.md)** | Расширенная сводка в text_FULL (Никитин запрос «каждую версию такой сводкой») | скрипт | `s` |
| **[048](../tasks/048-chronological-consistency-check.md)** | **Класс 12** — chronological inconsistency check (1946 + дети-1948) | скрипт | `m` |
| **[049](../tasks/049-discourse-markers-preservation.md)** | **Класс 13** — discourse markers preservation (метрика + GW v2.20 ПРАВИЛО 6) | скрипт + минор промпт | `s` |
| **[050](../tasks/050-pinlist-event-minimum-depth.md)** | **Класс 14** — pin-list event minimum depth (3 предл. для хронологических, 2 для бытовых) + GW v2.20 ПРАВИЛО 8 | скрипт + минор промпт | `s` |
| **GW v2.20** | Universal categorical правила (БЕЗ subject-конкретики, placeholders `[субъект]`, `[рассказчик]`) — мерж в task 043b/049/050 | промпт | `xs` |

### v60 sprint — финальная доводка после Никитиного review v59 (11 задач)

После v59 verified Никита одобрил план финальной доводки:

| Task | Что | Тип | Сложность |
|---|---|---|---|
| **[046b](../tasks/046b-stage3-runner-order-fix.md)** | Stage 3 runner: auto_rewrite **до** validators (порядок) | скрипт | `xs` |
| **[044c](../tasks/044c-relation-overrides-apply-to-final-book.md)** | Override применить к final book — debug почему баба Аня в family | скрипт | `xs` |
| **[043c](../tasks/043c-stop-phrases-extended-categorical.md)** | Stop-phrases extended categorical (мотивация идеалов, не сломленная, такой ушла и т.п.) | конфиг + regex | `xs` |
| **[049b](../tasks/049b-gw-v220-activation.md)** | GW v2.20 verify активирован в Stage 2 (Курсор подтвердил «нужен v60 pass») | implementation fix | `xs` |
| **[050b](../tasks/050b-pinlist-depth-paragraph-filter.md)** | Pin-list depth — фильтровать paspart, искать только в narrative | скрипт | `xs` |
| **[040b](../tasks/040b-gazeteer-morphology-cases.md)** | Gazeteer морфологические формы (падежи русских топонимов) | скрипт | `s` |
| **[048b](../tasks/048b-chronology-grandchildren.md)** | Chronology extension — внуки (parent.birth_year + 16, если grandchild birth неизвестен) | скрипт | `s` |
| **[051](../tasks/051-temporal-place-naming.md)** | **Класс 15** — temporal place naming (Калинин/Тверь, Ленинград/СПб) | конфиг + скрипт + минор промпт | `s` |
| **[052](../tasks/052-contributors-section.md)** | **Класс 16** — contributors section в конце книги (продуктовое нововведение) | конфиг + скрипт + минор промпт | `s` |
| **[045c](../tasks/045c-chapter-sections-anchors.md)** | **Класс 10 extension** — chapter sections anchors для ch_03 (гостеприимство/кулинария) | конфиг + скрипт + минор промпт | `s` |
| **verify-universality** | Отчёт об universality findings (см. ниже) | анализ | `xs` done |

**Universality findings (verify-universality):**
- ✅ `pipeline_utils.py` — generic, нет hardcoded «karakulina»
- ✅ `scripts/build_gate1_full_text.py` — параметризован CLI
- ❌ `scripts/test_stage1_karakulina_full.py` — name + PROJECT_ID hardcoded
- ❌ `scripts/test_stage2_pipeline.py` — PROJECT_ID + defaults hardcoded
- ❌ `scripts/test_stage3.py` — PROJECT_ID + DEFAULT_BOOK_DRAFT hardcoded

→ `task 053 — Generic Stage runners refactor` отложен в **Batch 3** (prework для Корольковой, не блокер PASS Ворот 1).

### Batch 3 — backlog после v60 PASS

- **task 053** — generic Stage runners (`test_stage1_full.py --subject X`, etc.)
- Подключение Корольковой / Дмитриева — генерализация на 2-й и 3-й subject
- Этап 2 (Proofreader scripted, task 030)
- Phase B механика (корректировки от клиента)

### v62a sprint — 10 точечных scripted fixes (NO GW change) после v61 review

**Триггер:** v61 verified — content quality v59 восстановлен, но Никитин review дал 13 замечаний + 5 моих блокеров. После verify + дедуп = 14 unique → 10 точечных + 1 meta (per Правилу 6 «медленно без откатов»).

**Подход:** все 10 fixes — scripted (NO GW prompt change). Никитины 2 features (ch_03 кулинария, epilogue extend) и historical_notes inline restoration отложены в backlog **по одной prompt-bump за раз** (v63/v64/v65).

| Task | Что |
|---|---|
| 044d | Render bug `?: ?` в bio_data.family (build_gate1 skip override entries) |
| 044e | Бабушка Марфа force-add в bio_data.family (debug task 044b cherry-pick) |
| 044f | Внук/Внучка notes preservation («сын/дочь Татьяны») |
| 049c | Discourse markers validator fix (rapporteurs config + aliases) |
| 051c | Paspart-only temporal name (Тверь→Калинин в bio_data только, не narrative) |
| 048c | Chronology check grandchildren (Class 12 false negative «1973 + Даша») |
| 052c | Contributors раздел как **чистый скрипт** из pin-list v4 (4 имени) |
| 043d | narrative_stop_phrases расширение (Class 1 «определило жизнь», «помогая в важные моменты») |
| 045e | Timeline anchors widowhood enforce as separate period (1978-1996 от khim_institute 1962-1978) |
| 043e | Anti_facts pin-list секция + scripted check (Class 1 predicate-object confabulation: варенье+салат, акушерство+«определило») |
| meta | gate1_product_checklist target 14-18K → **20K+** (Никитино решение) |

Spec: [v62a-pointed-fixes-sprint.md](../tasks/v62a-pointed-fixes-sprint.md)

Финансово v62a: 1 прогон $2-3. NO GW change = safe per Правило 6.

### Backlog после v62a (по одной GW prompt-bump за раз)

| v63 | ch_03 «Гостеприимство и кулинария» раздел | GW prompt-bump (1 правило) |
| v64 | Epilogue expand 676 → ~900 без stop phrases | GW prompt-bump (1 правило) |
| v65 | historical_notes inline restoration (vs v59 9 inline) | scripted reclassify ИЛИ GW prompt-bump |
| v66+ | task 053 generic Stage runners → подключение Корольковой | refactor scripts (NO GW) |

Каждая = $2-3 один прогон verify. Per Правилу 6 — нельзя bundle, нужно verify что предыдущие правила не деteriorировали.

### v61 sprint — Hybrid rollback (Вариант 1) после v60 регрессии

**Решение:** v60 регрессировал content (5+ Никитиных favorites потеряны) из-за **GW v2.21 cognitive overhead** (3 новых ПРАВИЛА одним bump). Diagnostic: Stage 1 (CA v1.4) данные сохранил — GW не использовал.

**Стратегия:** branch off v59 + cherry-pick ТОЛЬКО проверенные scripted fixes из v60. Никитины 3 features (contributors / temporal / chapter sections) — отложены в backlog после RP-1, добавляем **по одному**.

**Baseline для diff v61: v59** (не v56). Никитино решение «v59 — самый удачный бенч».

#### Cherry-pick из v60 (8 scripted fixes, все `low` risk)

| Task | Что |
|---|---|
| 044c | `remove_excluded_bio_data_family` |
| 045b | `validate_timeline_anchors` markdown parser |
| 046b | Stage 3 runner reorder (auto_rewrite ДО validators) |
| 049b | `_extract_prompt_version` + manifest tracking |
| 050b | `NARRATIVE_CHAPTERS` excludes epilogue |
| 040b | Gazeteer морфо падежи |
| 043c | epilogue_stop_phrases v2 + 4 категории stop |
| 048b | chronology check grandchildren (parent_birth + 15) |

#### Plus 1 минор fix

| Task | Что |
|---|---|
| [046c](../tasks/046c-epilogue-regex-intermediate-words.md) | Epilogue rewrite regex с intermediate words («путь от сироты ИЗ X до Y») |

#### НЕ берём из v60

- **GW v2.21 промпт** — откат к v2.20 (battle-tested в v59)
- task 051 temporal_place_names (wrong direction, multi-rename history not supported)
- task 052 contributors (галлюцинация «Наталья» + только 2/4 контрибьюторов)
- task 045c chapter_sections_anchors (config не передан в GW input)

#### Отложено в backlog после v61 PASS (по одному за раз!)

| Feature | Реализация | Когда |
|---|---|---|
| Contributors раздел | Чистый скрипт из pin-list v3 (без GW v2.X+1) | После RP-1 |
| Temporal place naming | Скрипт с multi-rename history (Тверь→Калинин 1931→Тверь 1990) | После RP-1 |
| Chapter sections (ch_03 кулинария) | GW prompt-bump **только эта 1 правка** + config в Stage 2 system context | После RP-1 |

**Финансово v61:** 1 прогон $2-3.

**Ожидаемый результат v61:**
- ✅ Content quality v59 восстановлен (Власьево, разные отцы, Маня, French бабушка, детский сад, ...)
- ✅ Все 8 scripted fixes v60 работают (timeline anchors 7/7, family clean, manifest tracking, depth scope, морфо)
- ✅ Epilogue без «путь от сироты ИЗ X до Y» (task 046c regex)
- ✅ Baseline v59 для diff
- ⚠️ Contributors / temporal / кулинария ch_03 — пока **отсутствуют** (backlog после RP-1)

### Принципы команды (зафиксированы 2026-05-17, постоянно держим в голове)

1. **Лес/деревья** — не устранять конкретные баги в ущерб общей картине; класс ≠ симптом
2. **Универсальность** — не Каракулино-специфика, а универсальное решение для любого subject
3. **Класс багов, не симптом** — лечим класс целиком, а не конкретный эпизод
4. **Скрипт-first** — максимум в скрипты, минимум в промпты
5. **Логирование** — каждое изменение промптов / спеков / прогонов фиксируется (run_registry + Правило 5)
6. **Медленные шаги без откатов** — лучше медленно, но без регрессий; backlog features добавляем по одному, отдельные verify-прогоны (Правило 6)

Batch 2-fix финансово: 1 прогон v59 покрывает все 9 (~$2-3).

### Batch 3 — backlog после v59

Зависит от того что v59 покажет. Сейчас не финализируем.

### Старый план (для истории)

Приоритет: **скрипт-only → скрипт+промпт → гибрид**.

### Batch 1 — скриптовые (минимальный risk, можно делать параллельно)

**task 042: subject_age algorithmic enrichment** (Класс 8)
- Post-Stage 1 скрипт: к каждому event в fact_map.timeline добавить поле `subject_age = year − birth_year`.
- GW сразу видит возраст, не вычисляет.
- Промпт GW не меняется (но в шаблоне input уже есть возраст).
- Универсально, риск нулевой.
- Тесты: pytest на корректность вычисления.

**task 040: post-FC ASR normalize gazeteer** (Класс 4)
- Скрипт между FC и LE: gazeteer-словарь канонических топонимов per subject + общий русский geo-словарь.
- Для Каракулиной: `Капашвара → Капошвара`, `Керсанов → Кирсанов`, `Новомергородский → Новомиргородский`.
- Тесты: pytest на gazeteer + integration на v56 артефактах (3/5 FC errors закрываются).
- **Решает FC FAIL iter3 на 3/5.**
- Универсально (gazeteer per subject, генерируется или хранится в `collab/context/gazeteer_<subject>.json`).

**task 039: bio_data integrity script** (Классы 2 + 3)
- Скрипт post-GW:
  - **Required fields check**: если в fact_map есть `death_year` супруга → bio_data.family.spouse имеет `death_year`. Аналогично: `retirement_year`, `birth_year` детей, главные звания.
  - **Family relation whitelist**: filter `bio_data.family` — только persons с relation ∈ {отец, мать, муж, жена, сын, дочь, брат, сестра, бабушка, дедушка, внук, внучка, тётя, дядя, племянник, племянница, золовка, свекровь}. Соседи, друзья, коллеги — НЕ в family.
  - **Дебаг** почему `enforce_bio_data_completeness` v56 пропустил Марфу (person_019).
- Универсально.
- **Решает FC err_004 (Марфа) + чистит family от тёти Маши + восстанавливает год смерти Дмитрия в паспортичке.**

### Batch 2 — гибридные (промпт + скрипт-валидация)

**task 038: CA v1.3 — strict description = source_quote** (Класс 1)
- **Промпт CA**: правило «description = парафраз source_quote, без добавления причинных связей которых нет в источнике. Запрещены `потому что`, `это произошло так как`, если их нет в source_quote».
- **Скрипт-валидация**: post-CA проверка `description` vs `source_quote`:
  - Word overlap ≥ X% (gen threshold, calibrate на v56)
  - Запрет causal connectors которых нет в source
  - На FAIL — флаг `description_drift: true` в audit
- **Тесты**: pytest на синтетических кейсах + integration на v56 (огурцы причина, шуба дата).
- Универсально.
- **Решает огурцы causal confabulation + шуба дата + любые будущие.**

**task 041: pin-list events для GW + diff-валидация** (Класс 5)
- **Промпт GW v2.19** (короткий патч, не 50 строк): новый раздел input — `pin_list_events` — обязательно развёрнуто рассказать.
- **Расширить pin-list** для Каракулиной (после подтверждения TR1 2026-05-17):
  - Операция на желудке 1960 + следствие «мало ела» (TR1)
  - Хрущевское сокращение армии 1962 (контекст Сахалин-развилки — historical_note)
  - Церковь во Власьево 1990-е (CA event_auto_005)
  - **Разные отцы у Валентины и старших сестёр** (TR1 подтверждено: «У бабушки был разный отец с её сёстрами»)
  - **Масштаб трагедии 1933:** мать умерла + младший брат умер + отец ушёл на заработки (TR1) — не сводить к «мать умерла»
  - Шарлотка (TR2), тётя Маша-соседка/грибы (TR1), «Французская бабушка»/Баба Аня (TR2), продажа дачи (TR2), дороговизна 90-х (TR1)
- **Скрипт diff-валидация**: после каждого прогона v_N → сравнить с предыдущей good-версией. Если v_N теряет ≥3 эпизода из v_(N-1) которые были в pin-list → flag.
- Универсально.
- **Решает Класс 5 episode regression + восстанавливает 5 потерянных эпизодов.**

### Batch 3 — финальный гибрид

**task 043: epilogue / geo / historical_notes guards** (Классы 6 + 7 + 9)
- **Скрипт post-GW** на epilogue: stop-phrase grep на пафосные обобщения из gate1 чек-листа + новые («человек своего времени», «история обычной советской женщины»).
- **Скрипт post-GW** на geo claims: cross-check региональных прилагательных («подмосковный», «сибирский», «уральский», ...) с fact_map.locations + русский geo-словарь.
- **Скрипт post-GW** на historical_notes reclassify: inline `***...***` справки промoute в `historical_notes` field либо обратно. Или промпт GW: запрет inline `***...***` в нарративе глав, только в field.
- Универсально.
- **Решает epilogue пластик + Химинститут=«подмосковный» + historical_notes underutilization.**

---

## 6. Финансовый план (batch verification, по протоколу Даши)

Вместо 6 прогонов после каждой задачи — **2 прогона**:

| Прогон | После задач | Verify |
|---|---|---|
| **v57** | 042 + 040 + 039 (Batch 1 скриптовый) | subject_age в timeline, FC errors 3/5 закрыто, Марфа есть в family, тётя Маша из family убрана, год смерти Дмитрия в паспортичке |
| **v58** | 038 + 041 + 043 (Batch 2-3 гибрид) | description drift нет в CA, pin-list эпизодов 7-8/9 закрыто, diff vs v57 не теряет эпизодов, epilogue без пластика, Химинститут не «подмосковный» |

**Стоимость:** 2 × $2-3 = $4-6 за полный цикл (vs $12-18 если по одной задаче).

**Решение по PASS Ворот 1:**
- Если v58 даёт 7+/9 эпизодов закрыто, описания без confabulation, FC PASS, geo корректно, epilogue без пластика → **RP-1 tag**, Ворота 1 PASS → Этап 2 (Proofreader scripted, task 030 unblocked).
- Если ещё проблемы — RETRO + новый план (но не whack-a-mole).

---

## 7. Что НЕ делаем сейчас (явный список)

- ❌ GW v2.19 как 50-строчный промпт-патч с 3 фиксами (валенс-инверсия + selectivity + characteristic words) — task 036 уже частично закрыл characteristic words 3/5; остальное лечится скриптами 038/041, не промптом.
- ❌ task 037 (GW prompt refactor ≥2000 строк) — отложить до Batch 2 (когда добавится pin-list блок в input, GW промпт может вырасти, но input расширяется, а правил — нет).
- ❌ LE v3.2 промпт-фикс — код держит, не блокер для Ворот 1.
- ❌ Новый прогон v57 до закрытия Batch 1.
- ❌ Этап 2 (Proofreader scripted, task 030) — до Ворот 1 PASS.
- ❌ Генерализация на Королькову/Дмитриева — после Ворот 1.

---

## 8. Открытые вопросы

1. **Порядок Batch 1**: делать 042 + 040 + 039 параллельно (3 спецификации Курсору) или последовательно? Параллельно дешевле по времени, но 1 прогон verify покрывает всех 3.
2. **Pin-list пополнение**: кто пишет (Даша / Опус / Курсор)? Я готов написать draft v2 `known_episodes_karakulina.md` после Batch 1 sign-off.
3. **diff-валидация baseline**: какая версия — «good baseline» для сравнения? Вариант: v56 как baseline для v57 (v56 уже неплох), v57 как baseline для v58.
4. **CA description threshold**: какой % word overlap считать pass? Калибровать на v56 артефактах (огурцы должны FAIL, остальное PASS) — это часть task 038 spec.

---

## 9. Что мы зафиксировали как принципы (для будущих сессий)

1. **Скрипт-first**: 7 из 9 классов багов решаются скриптами. Промпт — последнее средство, когда скрипт невозможен.
2. **Универсальность over субъект-специфичность**: pin-list, gazeteer, schema паспортички — всё параметризуется per subject, код не привязан к Каракулиной.
3. **Класс багов, не симптом**: огурцы причина — Класс 1, лечится один раз для всех causal confabulations, не патч для конкретно огурцов.
4. **Диф между версиями**: каждый новый прогон сравнивать с предыдущим good — episode regression диагностируется на этапе верификации, не «через 2 версии».
5. **Лес, не деревья**: между прогонами держать в голове 9 классов, не 5 эпизодов и 5 топонимов. Конкретные баги — это симптомы, классы — это корни.

---

## История версий

| Версия | Дата | Изменение | Кто |
|---|---|---|---|
| v1 | 2026-05-17 | Создание после v56 + Никитин feedback + TR1 verify | Опус |
