# Handoff Курсору — 2026-05-18 (для нового окна, перед v62a sprint)

> **Документ-страховка для нового окна Курсора.** Если предыдущая сессия Курсора кончилась, новое окно читает этот файл **первым** (5-10 мин) → готов работать на v62a sprint.
>
> **Назначение:** дать Курсору cold-start контекст по архитектурной дисциплине + истории прогонов + почему именно v62a именно так. Без этого Курсор может пропустить дисциплину (NO GW change, Universality check, медленно без откатов).

---

## За 30 секунд: где мы

**Glava — Telegram-сервис AI-биографий.** Каракулина — тренировочный кейс, цель — отладить пайплайн так чтобы он работал на любом subject. Сейчас на Ворота 1 (текст до вёрстки).

**Текущая фаза:** Ворота 1 PASS pending. v60 sprint регрессировал контент (GW v2.21 cognitive overload — добавили 3 правила одним bump). v61 Hybrid rollback (GW v2.20 + cherry-pick 8 scripted fixes из v60) — близко к PASS, 14 минорных пунктов остались.

**v62a sprint:** 10 точечных scripted fixes БЕЗ GW prompt change (Правило 6 «не bundle prompt правил»). После v62a → tag RP-1 → backlog v63/v64/v65 (каждый = одна GW prompt-bump, отдельный verify).

**Baseline для diff:** v59 (Никитино решение — «v59 самый удачный бенч»).

---

## Команда и роли

| Роль | Кто | Доступ |
|------|-----|---------|
| Owner / Product Lead | Никита | Финальный sign-off на все архитектурные ходы |
| **Архитектор + Продакт (объединённо с 2026-05-17)** | **Опус** (AI) | План перед волной (Правило 1), артефакт перед проектированием (Правило 2), spec'и, stocktake, run_registry |
| Исполнитель | **Курсор** (AI, ты) | Реализация по spec'ам, прогоны на сервере, verified-on-run отчёты |
| ~~Продакт (Даша)~~ | ~~Даша + Дашин Клод~~ | **Отстранены с 2026-05-17** (временно). Опус закрывает их роль. |

---

## ОБЯЗАТЕЛЬНО прочитать (15 мин)

В порядке приоритета:

1. **`collab/context/architecture-stocktake-2026-05-17.md`** — текущее состояние (16+ классов багов, тренды v54→v61, v62a план, backlog)
2. **`collab/context/dev-review-protocol.md`** — **6 правил архитектора** (особенно Правило 4 Universality check, Правило 6 prompt engineering discipline)
3. **`collab/context/run_registry.md`** — реестр версий всех прогонов v54-v62a, baselines, что использовалось
4. **`collab/context/known_episodes_karakulina.md`** v4 — pin-list source of truth (включая новую секцию **Anti-facts** для task 043e)
5. **`collab/context/product-goal.md`** — продуктовая цель + Ворота 1-4
6. **`collab/tasks/v62a-pointed-fixes-sprint.md`** — главный spec для v62a sprint (10 sub-tasks)
7. **`collab/context/gate1_product_checklist.md`** — критерии Ворот 1 (target обновлён: **20K+ chars**)

---

## 6 правил архитектора (Опус соблюдает, ты сверяешь)

1. **План перед волной** — Опус даёт spec, ты реализуешь по spec'у. Не «давай делать X» без плана.
2. **Артефакт перед проектированием** — Опус открывает фактические артефакты в репо (правило 2 verified-on-run применимо и к review кода).
3. **Stocktake каждые 2-3 волны** — после v60/v61/v62a — обязательный stocktake (Опус ведёт).
4. **Universality check (для каждой задачи)** — 4 вопроса в template `collab/tasks/_template.md`: Промпт без конкретики subject? Subject-specific конкретика в JSON конфигах? Алгоритм generic? Subject-replacement test пройден?
5. **Run registry update** — после каждого прогона `run_registry.md` обновляется со всеми версиями (Опус делает; ты — версии в Stage manifests).
6. **Prompt engineering дисциплина** — **1 новое правило per GW prompt-bump**, не bundle. Альтернатива: реализовать через скрипт. **Прецедент v60:** GW v2.21 = v2.20 + 3 правил одним bump → content regression. **В v62a — NO GW prompt change.**

---

## 6 принципов команды (Никита **постоянно** повторяет)

1. **Лес/деревья** — лечим классы багов, не точечные эпизоды
2. **Универсальность** — пайплайн для всех биографий, не только Каракулины (per-subject configs, generic код)
3. **Класс багов, не симптом** — Никитин feedback по эпизодам → Опус обобщает до класса
4. **Скрипт-first** — максимум в скрипты, минимум в промпты; новые features = скрипты, не GW extensions
5. **Логирование** — все версии прогонов / промптов / спеков в run_registry
6. **Медленно без откатов** — Никита явно сказал: «лучше медленно, но без регрессий, пусть темп и не высокий»

---

## История прогонов v54-v61 (краткая, для context)

| Run | Триггер | Результат | Lesson |
|-----|---------|-----------|--------|
| v54 | Этап 1 (GW v2.17 + LE v3.1) | 9 эпизодов потеряны (Дашин feedback) | → task 035 split-extract + 036 GW v2.18 |
| v55 | task 035/036 | 2/9 эпизодов восстановлены, новый класс emotional valence inversion | → task 038/041 |
| v56 | pin-list events CA v1.2 | 4/9, огурцы causal confabulation | → Batch 1 scripted defenses |
| v57 | Batch 1 (042/040/039) | Classes 4/7/8 closed | → Batch 2 (CA strict, GW pin-list, anchors) |
| v58 | Batch 2 | CA over-strict, эпизоды снова потеряны | → Batch 2-fix |
| v59 | Batch 2-fix (10 tasks) | Best version yet, 7 expected outcomes PASS, 3 нужны v60 | **= baseline для diff** (Никитино решение) |
| v60 | v60 sprint (10 tasks + GW v2.21) | **Content regression** — GW cognitive overload (3 правила одним bump). Diagnostic: CA v1.4 данные сохранил, GW не использовал | → Hybrid rollback Вариант 1 |
| **v61** | **Hybrid rollback** (GW v2.20 + cherry-pick 8 scripted из v60) | **Close-but-not-PASS**. Content v59 90% восстановлен. 14 минорных пунктов (5 моих + 13 Никитиных − 2 false alarm) | → v62a 10 точечных scripted fixes |
| **v62a** | **PENDING — твой следующий sprint** | TBD | — |

---

## v62a sprint — что делать (полный spec в `collab/tasks/v62a-pointed-fixes-sprint.md`)

**10 scripted fixes + 1 meta, NO GW prompt change:**

| Task | Что | Где |
|---|---|---|
| 044d | Build_gate1 render bug: skip `?: ?` override entries + dedup «Основные даты жизни» | `scripts/build_gate1_full_text.py` |
| 044e | Бабушка Марфа force-add в bio_data.family | `pipeline_utils.py` `enforce_bio_data_completeness` |
| 044f | Внук/Внучка notes «сын/дочь Татьяны» | `persona_notes_karakulina.json` + `enforce_persona_notes` |
| 049c | Discourse markers validator fix (rapporteurs + aliases) | `pipeline_utils.py` `validate_discourse_markers` |
| 051c | Paspart-only temporal (Тверь→Калинин **только** в bio_data) | `pipeline_utils.py` новая `apply_temporal_naming_to_paspart_only` |
| 048c | Chronology grandchildren (Class 12 «1973 + Даша» false negative) | `pipeline_utils.py` `validate_chronological_consistency` |
| 052c | Contributors раздел clean rewrite из pin-list v4 (4 имени) | `scripts/build_gate1_full_text.py` `append_contributors_section` |
| 043d | narrative_stop_phrases расширение Class 1 patterns | `narrative_stop_phrases.json` v2 |
| 045e | Timeline anchors widowhood enforce as separate period | `pipeline_utils.py` `validate_timeline_anchors` |
| 043e | Anti_facts pin-list + scripted check (Class 1 predicate-object confabulation) | `pipeline_utils.py` новая `validate_anti_facts` |
| meta | gate1_product_checklist target 14-18K → **20K+** | `collab/context/gate1_product_checklist.md` |

**Ветка:** `feat/v62a-pointed-fixes` off v61 commit `a8809aa`.

**Прогон:** `bash scripts/_run_v62_full.sh` (или эквивалент).

**Артефакты:** push в `runs/karakulina-v62-artifacts` ветку.

**Verified-on-run:** одно конкретное наблюдение per task (см. spec).

---

## Backlog после v62a PASS (Правило 6 — по одной GW prompt-bump за раз)

| Volna | Trigger | GW change |
|---|---|---|
| v63 | ch_03 «Гостеприимство и кулинария» раздел | GW prompt-bump (**1** правило: section anchor в ch_03) |
| v64 | Epilogue extend 676→~900 без stop phrases | GW prompt-bump (**1** правило: depth target epilogue) |
| v65 | historical_notes inline restoration (vs v59 9 inline) | investigation: scripted reclassify ИЛИ GW prompt-bump |
| v66+ | task 053 generic Stage runners → подключение Корольковой | NO GW change (refactor scripts) |

**Каждая = $2-3 один прогон verify.** Никогда не bundle 2+ GW правил в один bump.

---

## Дисциплина для Курсора в v62a

1. **NO GW prompt change.** Файл `prompts/03_ghostwriter_v2.22.md` НЕ создавать. GW v2.20 остаётся (pipeline_config.json без правок).
2. **Universality check** для каждой sub-task — 4 вопроса + trap warning. Открой `collab/tasks/_template.md` секцию Universality check.
3. **Verified-on-run = одно конкретное наблюдение** про артефакт. Не «PASS / exit 0», а «открыл text_FULL.md line 111: «Бабушка: Марфа», note: мать отца Валентины».
4. **Manifest versions** — Stage 2/3 manifest должны содержать `ghostwriter_version`, `completeness_auditor_version` (task 049b закрепил, продолжай).
5. **Git push** обеих веток (`feat/v62a-pointed-fixes` + `runs/karakulina-v62-artifacts`) — забывал в v59/v60 sprints, исправил после напоминания. Не забывай.
6. **Push артефактов отдельной веткой** (как в v57/v58/v59/v60).

---

## Финансово

v62a = 1 прогон $2-3. Никита подтвердил готовность.

---

## Когда v62 готов

1. Отчёт verified-on-run в PR #28 (или новом PR `feat/v62a-pointed-fixes`)
2. Опус откроет артефакты сам (правило 2), сравнит с **v59 baseline** через text_FULL diff
3. Если 11 expected outcomes сходятся → **PASS Ворот 1** → tag RP-1 → разблокировка backlog v63 + параллельная Королькова (task 053)
4. Если не PASS → Опус diagnostic + точечный v62b sprint

---

## Открытые ссылки

- **PR #28** (главный): https://github.com/NikitaMorgos/glava-bot/pull/28
- **v59 артефакты** (baseline): ветка `feat/batch2fix-pin-list-and-classes` коммит `26ce5cc`, файл `collab/runs/karakulina_v59/karakulina_v59_text_FULL.md`
- **v61 артефакты** (последний прогон): ветка `runs/karakulina-v61-artifacts` коммит `df6f3f3`
- **v62a spec**: `collab/tasks/v62a-pointed-fixes-sprint.md` в PR #28 (commit `357baf7`)

---

## Версии этого документа

| Версия | Дата | Изменение | Кто |
|---|---|---|---|
| v1 | 2026-05-18 | Создание перед v62a sprint после Никитиного вопроса «Курсору нужен handoff для нового окна?» | Опус |
