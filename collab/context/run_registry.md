# Run Registry — Каракулина (и далее other subjects)

> **Источник правды** по версиям компонентов, конфигов и кода для каждого прогона пайплайна.
>
> **Дисциплина:** Опус **обязан** обновлять этот файл после каждого прогона (Правило 5 архитектора, dev-review-protocol.md).
>
> **Зачем:** reproducibility, diagnostic, сравнение runs, подключение новых subjects (Королькова получит те же версии что Каракулина PASS Ворот 1).
>
> **Создан:** 2026-05-17 (после v59, перед v60). Заполнено ретроспективно из git log + tasks + памяти Опуса. Где точно неизвестно — помечено `?` с пояснением.

---

## Структура записи (template для будущих subjects)

```
## v<N> (YYYY-MM-DD) — <short trigger>
**Branch + commit:** <branch> @ <sha>
**Status:** pending / verified / regression / superseded

### Components
- Cleaner: vX
- Fact Extractor: vX
- Historian: vX
- Completeness Auditor (CA): vX
- Ghostwriter (GW): vX
- Fact Checker (FC): vX
- Literary Editor (LE): vX
- Proofreader (PR): vX

### Configs (per subject)
- known_episodes_<subject>.md: vN
- gazeteer_<subject>.json: vN
- relation_overrides_<subject>.json: vN
- timeline_anchors_<subject>.json: vN
- discourse_markers_<subject>.json: vN
- chapter_sections_anchors_<subject>.json: vN
- temporal_place_names_<subject>.json: vN
- contributors_<subject>.json: vN

### Configs (generic)
- epilogue_stop_phrases.json: vN
- epilogue_rewrite_mapping.json: vN
- narrative_stop_phrases.json: vN

### Pipeline code
- pipeline_utils.py: @<sha>
- scripts/test_stage1_*.py: @<sha>
- scripts/test_stage2_pipeline.py: @<sha>
- scripts/test_stage3.py: @<sha>
- scripts/build_gate1_full_text.py: @<sha>

### Inputs
- Transcripts: TR1 / TR2 / TR1+TR2 (combined/split-extract)
- Pin-list as input: yes/no
- Diff baseline: vN

### Outputs
- Run artifacts branch: runs/<subject>-v<N>-artifacts @ <sha>
- text_FULL.md: path
- book_FINAL_stage3.json: path

### Verification
- FC verdict: PASS/FAIL
- gate1 product checklist: pending/PASS/FAIL
- pin-list coverage: X / Y full
- expected outcomes (если был): K / M PASS

### Notes
- Trigger waves (Batch 1 / 2 / 2-fix / sprint v60)
- Tasks shipped в этой версии
- Регрессии vs предыдущая
- Improvements vs предыдущая
```

---

# Каракулина — registry

## v54 (2026-05-10? — точная дата требует уточнения) — Этап 1 first run

**Branch + commit:** `claude/etap1-*` @ `00cd17e` (runs commit)
**Status:** superseded (9 эпизодов потеряны, Дашин feedback → RETRO + task 035/036)

### Components
- Cleaner: v1
- Fact Extractor: v3.4
- Historian: v3
- CA: v1.1 (или v1.0 — до task 035 расширения)
- **GW: v2.17** (Этап 1 ЗАПРЕТ 8 первый абзац)
- FC: v2.13
- **LE: v3.1** (Этап 1 ЗАПРЕТ 0 preserve structural fields)
- PR: v1

### Configs (per subject)
- known_episodes_karakulina.md: не существовал (создан в RETRO 2026-05-15)
- остальные конфиги: не существовали

### Pipeline code
- pipeline_utils.py: @ commit `00cd17e`-родственный
- + первая версия `preserve_chapter_structural_fields` (task 034)
- + `enforce_bio_data_completeness` (task 027)

### Inputs
- Transcripts: TR1+TR2 **combined** (старый режим)
- Pin-list: нет
- Diff baseline: нет (первый Этап 1 run)

### Outputs
- Run artifacts: `runs/karakulina-v54-artifacts`
- Total chars: 17 700
- bio_data.family: 18

### Verification
- FC: ?
- Дашин feedback: 9 потерянных эпизодов + 4 стилистических клише + 1 фактическая ошибка

### Notes
- **Триггер RETRO** → task 035 (split-extract + CA v1.2) + task 036 (GW v2.18)
- 5-я регрессия (#4 cross-chapter dedup, #5 Татьяна missing) исследовались на основе v54

---

## v55 (2026-05-15) — RETRO: split-extract + GW v2.18

**Branch + commit:** `runs/karakulina-v55-artifacts` @ `7f33684`
**Status:** superseded (2/9 эпизодов закрыто, новая регрессия — emotional valence inversion огурцы)

### Components
- Cleaner: v1, Fact Extractor: v3.4, Historian: v3
- **CA: v1.2** (task 035 — pin-list events расширение)
- **GW: v2.18** (task 036 — 5 стилистических фиксов: ЗАПРЕТ 8 на ВСЕ абзацы, СТОП-ФРАЗЫ +6, ЗАПРЕТ 9 X-по-Y, ЗАПРЕТ 10 вымышленные временные связки, characteristic words ≥3)
- FC: v2.13, LE: v3.1, PR: v1

### Configs
- **known_episodes_karakulina.md: v1** (создан в RETRO, 26+15+10+6 эпизодов)

### Pipeline code
- + split-extract mode в `scripts/test_stage1_karakulina_full.py` (task 035)

### Inputs
- Transcripts: TR1+TR2 **split-extract** (TR1 Phase A → TR2 Phase B → merge)
- Pin-list: yes (v1)
- Diff baseline: v54

### Outputs
- Run artifacts: `runs/karakulina-v55-artifacts`
- Total chars: 14 700
- bio_data.family: 23

### Verification
- 2/4 TR2-эпизодов в book
- Огурцы: emotional valence inversion (восторг вместо конфликта) — новый класс регрессии

### Notes
- task 035 + 036 shipped
- Триггер для v56 — добавить `--prev-fact-map=fact_map_v55` (pin-list events CA v1.2 активировать)

---

## v56 (2026-05-15/16) — pin-list events Ход 2

**Branch + commit:** `runs/karakulina-v56-artifacts` @ `bed4343`
**Status:** baseline для diff (используется как baseline для всех последующих по решению Никиты)

### Components
Same as v55:
- Cleaner: v1, FE: v3.4, Historian: v3
- CA: v1.2, GW: v2.18, FC: v2.13, LE: v3.1, PR: v1

### Configs
- known_episodes_karakulina.md: v1

### Inputs
- Transcripts: TR1+TR2 split-extract
- Pin-list: yes (v1)
- `--prev-fact-map=fact_map_v55` (pin-list events CA v1.2 fully activated)
- Diff baseline: v54 (не зафиксирован формально)

### Outputs
- Run artifacts: `runs/karakulina-v56-artifacts`
- Total chars: 16 495
- bio_data.family: 22
- historical_notes: 2 в field
- timeline периодов: 7
- ch_02 chars: 6 278

### Verification
- FC: FAIL iter3 (5 errors — Новомиргородский транслитерация + person_019 Марфа missing + неполные медали)
- Pin-list эпизодов закрыто: 4/9 (огурцы есть, но causal confabulation)
- Characteristic words: 3/5

### Notes
- **BASELINE для diff** (Никитино решение перед v57)
- Огурцы причина «потому что не привозит достаточно подарков» — class 1 CA confabulation
- Шуба→пианино date=1990 (реально 1962) — еще класс 1

---

## v57 (2026-05-17) — Batch 1 (script defenses)

**Branch + commit:** `feat/batch1-script-defenses` + `runs/karakulina-v57-artifacts` @ `993ade2`
**Status:** verified, classes 4/7/8 closed

### Components
Same as v56:
- Cleaner: v1, FE: v3.4, Historian: v3
- CA: v1.2, GW: v2.18, FC: v2.13, LE: v3.1, PR: v1

### Configs (per subject)
- known_episodes_karakulina.md: v1
- **gazeteer_karakulina.json: v1** (создан task 040 — 12 замен)

### Pipeline code
- + `enrich_timeline_with_subject_age` (task 042) — Stage 1
- + `normalize_topo_via_gazeteer` (task 040) — Stage 1 + Stage 3
- + `apply_relation_overrides`, `filter_bio_data_family_by_relation_whitelist`, `validate_bio_data_required_fields` (task 039)
- `pipeline_utils.py`: @ commit `6a16177`

### Inputs
- Transcripts: TR1+TR2 split-extract
- Pin-list: yes (v1)
- Diff baseline: v56

### Outputs
- Run artifacts: `runs/karakulina-v57-artifacts`
- Total chars: 17 411
- bio_data.family: 19 (JSON; render показал 21 включая Марфу из fact_map)
- historical_notes: 3 в field
- timeline периодов: 6 (склейка «учёба+война» — Класс 10 регрессия)

### Verification
- FC: iter1→финал чист (после нормализации топонимов)
- Pin-list: 4/9 (без изменений vs v56)
- task 042: ✅ 36/36 events с subject_age
- task 040: ✅ 0 находок старых ASR форм
- task 039: ⚠️ Марфа в render, не в JSON; тётя Маша в family

### Notes
- Batch 1: tasks 042 / 040 / 039 — verified
- Класс 4 (ASR транслитерация) ✅ закрыт
- Класс 7 (Geo misattribution) ✅ закрыт (GW сам)
- Класс 8 (Age markers) ✅ закрыт
- Дашин/Никитин feedback v57 → Batch 2

---

## v58 (a/b/c итерации, 2026-05-17) — Batch 2 (pin-list для GW + CA strict + structure anchors)

**Branch + commit:** `feat/batch2-pin-list-defenses` + `runs(v58)` @ `9eacaca` (a/b/c — итерации отладки configs)
**Status:** superseded by v59 (regression: CA over-strict, GW v2.19 not following pin-list, эпизоды потеряны)
**Финальный artifact:** v58c (с исправленным config lookup)

### Components
- Cleaner: v1, FE: v3.4, Historian: v3
- **CA: v1.3** (task 038 — ПРАВИЛА 4-5 strict description / relation_to_subject)
- **GW: v2.19** (task 041 — PIN_LIST_EVENTS блок в input; task 043 — ЗАПРЕТЫ 12-14: paspart format, epilogue antitriggers, Класс 11 awkward)
- FC: v2.13, LE: v3.1, PR: v1

### Configs (per subject)
- known_episodes_karakulina.md: **v2** (расширение after v56/v57 review: +6 эпизодов, +2 бытовых, anchors, overrides)
- gazeteer_karakulina.json: v1
- **relation_overrides_karakulina.json: v1** (task 044 — тётя Маша / баба Аня / Нинвана)
- **timeline_anchors_karakulina.json: v1** (task 045 — 7 anchors)
- **persona_notes_karakulina.json: v1** (task 044)

### Configs (generic)
- **epilogue_stop_phrases.json: v1** (task 043 — 4 фразы)

### Pipeline code
- + `parse_pin_list_from_markdown`, `validate_pin_list_coverage`, `diff_episodes_between_versions` (task 041)
- + `validate_description_drift`, `validate_relation_consistency`, `validate_historical_note_grounding`, `validate_motivation_attributions` (task 038)
- + `validate_epilogue_stop_phrases`, `validate_awkward_formulation`, `enforce_paspart_format` (task 043)
- + `apply_relation_overrides`, `enforce_persona_notes` (task 044)
- + `validate_timeline_anchors`, `enforce_timeline_anchors` (task 045)
- `pipeline_utils.py`: @ `7e1f6b6`

### Inputs
- Transcripts: TR1+TR2 split
- Pin-list: yes (v2)
- **Pin-list events в CA: НЕ передан** (bug discovered post-run) → CA не extract'ил огурцы/шубу/ложечки
- Diff baseline: v56

### Outputs
- Run artifacts: `runs(v58)` (на ветке feat/batch2)
- Total chars: ~16 700 (v58c)
- bio_data.family: 16
- historical_notes: 0 в field ⚠️ регрессия

### Verification
- FC: iter1 fail (медали, дубль огурцов), финал ОК
- Pin-list: 4/9 хронологических (counted by Курсор full=13/67); огурцы/счётчик/шуба regressed
- Класс 3 (family attribution): тётя Маша/баба Аня — closed ✅
- Класс 10 (timeline structure): 7 markdown / 0 JSON — bug script

### Notes
- 5 регрессий vs v57: огурцы исчезли, счётчик исчез, historical_notes 0, шуба cut, племянницы missing
- Diagnostic Опуса: CA v1.3 over-strict → отверг auto_enrich; Stage 1 runner не подал --known-episodes
- 2 новых класса обнаружены: Класс 12 (chronological), Класс 13 (discourse markers)
- → Batch 2-fix план

---

## v59 (2026-05-17) — Batch 2-fix (10 tasks)

**Branch + commit:** `feat/batch2fix-pin-list-and-classes` @ `26ce5cc`
**Status:** verified — best version yet, ~10/14 Никитиных пунктов v58 закрыто; 3 точечных block для PASS

### Components
- Cleaner: v1, FE: v3.4, Historian: v3
- **CA: v1.4** (task 038b — ПРАВИЛО 6 bypass strict для pin-list events)
- **GW: v2.20** (Batch 2-fix: ПРАВИЛО 6 discourse markers, ПРАВИЛО 7 subject_age, ПРАВИЛО 8 pin-list event min depth, ЗАПРЕТ 15 narrative антитриггеры)
- FC: v2.13, LE: v3.1, PR: v1

### Configs (per subject)
- **known_episodes_karakulina.md: v3** (Contributors раздел)
- gazeteer_karakulina.json: v1
- relation_overrides_karakulina.json: v1
- timeline_anchors_karakulina.json: v1
- **discourse_markers_karakulina.json: v1** (task 049 — rapporteurs + thresholds)
- persona_notes_karakulina.json: v1

### Configs (generic)
- epilogue_stop_phrases.json: v1
- **epilogue_rewrite_mapping.json: v1** (task 046 — 5 правил delete)
- **narrative_stop_phrases.json: v1** (task 043b — categorical patterns)

### Pipeline code
- + `validate_pin_list_in_auto_enrich` (task 038b)
- + `apply_relation_overrides` расширен force-add required_persons (task 044b)
- + `enforce_epilogue_stop_phrases` auto-rewrite (task 046)
- + `validate_chronological_consistency` (task 048 Класс 12)
- + `validate_discourse_markers` (task 049 Класс 13)
- + `validate_pin_list_depth` (task 050 Класс 14)
- + расширенная сводка в `build_gate1_full_text.py` (task 047)
- + Stage 1 runner обязательная подача `--known-episodes` (task 041b)
- + Stage 2 runner manifest version logging (task 049b)
- + Stage 3 runner timeline_anchors markdown parser (task 045b)
- `pipeline_utils.py`: @ `26ce5cc`

### Inputs
- Transcripts: TR1+TR2 split
- Pin-list: yes (v3)
- `--known-episodes=collab/context/known_episodes_karakulina.md` (task 041b activated)
- Diff baseline: v56

### Outputs
- Run artifacts: внутри `feat/batch2fix-pin-list-and-classes` ветки (`collab/runs/karakulina_v59/`)
- Total chars: 19 930
- bio_data.family: 24 (Марфа, Маня, Римма, Зина добавлены)
- historical_notes: 7 в field + 9 inline ✅✅
- ch_02 chars: 8 423

### Verification
- FC: PASS iter3
- Pin-list: ~9/9 расширенного (15 full / 7 partial / 45 skipped из 67 total включая antitriggers)
- Class 5 (Episode regression): большой прогресс — огурцы, счётчик, разные отцы, дача (?), Власьево, операция, ДК Синтетик, почерк, дороговизна, тёти Маши соседка, французская бабушка — все восстановлены
- Class 9 (historical_notes): closed ✅
- Class 12: detector работает, 3 errors (частично false positive)
- Class 13: detector работает, ch_02=2/8 (GW не выучил threshold)
- Class 14: detector работает, 8 errors (paspart строки as false positive — bug detector)
- 3 блокера для PASS:
  - Epilogue stop phrases 4 errors (порядок validators after auto_rewrite — bug task 046)
  - Баба Аня в bio_data.family как «Свекровь» (relation override не применён к final book)
  - GW сам confabulated «1973 встречала внучку Дашу из школы» (Даша ещё не родилась)
  - Тверь vs Калинин в нарративе 50-х
  - Сапоново vs Сафроново (gazeteer не покрыл падежи)

### Notes
- Batch 2-fix (10 tasks) — most fixes worked, но 3 точечных bug требуют v60 sprint
- Никитин review: лучшая версия, 11 комментариев + продуктовое нововведение Contributors
- 2 новых класса (15 temporal place names, 16 contributors)
- → v60 sprint план

---

## v60 (2026-05-17) — v60 sprint (10 final fix tasks) — **PENDING прогон Курсора**

**Branch + commit:** `feat/batch2fix-pin-list-and-classes` @ `1e13dec` (после 2 universality patches)
**Status:** **pending** — Курсор запускает `_run_v60_full.sh`

### Components
- Cleaner: v1, FE: v3.4, Historian: v3
- CA: v1.4 (без изменений с v59)
- **GW: v2.21** (task 049b — новые ПРАВИЛА 9 temporal place names, 10 contributors, 11 chapter sections anchors)
- FC: v2.13, LE: v3.1, PR: v1

### Configs (per subject)
- known_episodes_karakulina.md: v3
- **gazeteer_karakulina.json: v2** (task 040b — морфологические падежи: Сапонова/Сапонове/Сапонову/Сапоновом)
- relation_overrides_karakulina.json: v1 (task 044c — без изменений конфига, только использования)
- timeline_anchors_karakulina.json: v1
- discourse_markers_karakulina.json: v1
- persona_notes_karakulina.json: v1
- **chapter_sections_anchors_karakulina.json: v1** (task 045c — 7 anchors ch_03)
- **temporal_place_names_karakulina.json: v1** (task 051 — Калинин/Тверь и др.)
- **contributors_karakulina.json: v1** (task 052 — Татьяна / Никита / Даша / Кужба)

### Configs (generic)
- **epilogue_stop_phrases.json: v2** (task 043c — +4 фразы: верила в идеалы, не сломленная, такой ушла, сохранившая до конца)
- **epilogue_rewrite_mapping.json: v2** (task 043c — +5 правил delete)
- narrative_stop_phrases.json: v1

### Pipeline code
- + `remove_excluded_bio_data_family` (task 044c)
- + `_extract_prompt_version` + manifest tracking (task 049b)
- + Stage 3 runner reorder: auto_rewrite **до** validators (task 046b)
- + `validate_pin_list_depth` NARRATIVE_CHAPTERS = {"ch_02","ch_03","ch_04"} — epilogue excluded (task 050b)
- + `normalize_topo_via_gazeteer` морфологические формы (task 040b)
- + `validate_chronological_consistency` + grandchild_before_inferred_birth (task 048b)
- + `validate_temporal_place_names` + `enforce_temporal_place_names` (task 051)
- + `append_contributors_section` в `build_gate1_full_text.py` (task 052)
- + `validate_chapter_sections_anchors` (task 045c)
- `pipeline_utils.py`: @ `1e13dec`

### Inputs
- Transcripts: TR1+TR2 split
- Pin-list: yes (v3, with Contributors раздел)
- `--known-episodes` обязателен
- Diff baseline: v56

### Outputs (PENDING прогона)
- Run artifacts: `runs/karakulina-v60-artifacts` (ожидается)
- Expected:
  - Огурцы развёрнутый эпизод с цитатой + конкретный год (не 1990-е)
  - Шуба→пианино 1962 + цитата «тяжеловата»
  - Шарлотка, карты/домино, дача продали (если в TR)
  - Марфа/Маня/Римма/Зина в family
  - Баба Аня НЕ в family
  - Epilogue без stop phrases (4 категории)
  - Калинин в нарративе 50-60-х (не Тверь)
  - Сафронова/Сафронове (не Сапонова)
  - Раздел «Кто работал над этой Главой» в конце
  - ch_03 «Гостеприимство и кулинария» раздел
  - Discourse markers ch_02 ≥ 5 (минимум, threshold 8 идеально)

### Verification — pending после прогона

10 expected outcomes (см. PR #28 v60 sprint текст).

Если 10+ из 10 PASS → **РЕКОМЕНДАЦИЯ PASS Ворот 1** → RP-1 tag → Batch 3 (task 053 generic runners + подключение Корольковой) + Этап 2 (Proofreader scripted, task 030).

### Notes
- v60 sprint: 10 tasks (046b/044c/049b/043c/050b/040b/048b/051/052/045c) + 2 universality patches (NARRATIVE_CHAPTERS / GW v2.21 placeholders)
- Lesson learned: Universality check template недостаточен, нужен subject-replacement test построчно (зафиксирован в memory)

---

# Стандарт версионирования

## Components

- **GW (Ghostwriter):** v2.X (v2.17 Этап 1 → v2.18 task 036 → v2.19 Batch 2 → v2.20 Batch 2-fix → v2.21 v60 sprint)
- **CA (Completeness Auditor):** v1.X (v1.0 base → v1.1 → v1.2 task 035 pin-list events → v1.3 task 038 strict → v1.4 task 038b pin-list bypass)
- **LE (Literary Editor):** v3.X (v3.0 base → v3.1 Этап 1 task 034 preserve)
- **FC (Fact Checker):** v2.X (v2.13 fixed since 2026-05-07)

## Configs

Subject-specific:
- `known_episodes_<subject>.md` — v1/v2/v3 (по версиям расширений)
- `gazeteer_<subject>.json` — v1/v2 (морфологические расширения)
- `relation_overrides_<subject>.json` — v1
- `timeline_anchors_<subject>.json` — v1
- `discourse_markers_<subject>.json` — v1
- `chapter_sections_anchors_<subject>.json` — v1
- `temporal_place_names_<subject>.json` — v1
- `contributors_<subject>.json` — v1
- `persona_notes_<subject>.json` — v1

Generic:
- `epilogue_stop_phrases.json` — v1/v2
- `epilogue_rewrite_mapping.json` — v1/v2
- `narrative_stop_phrases.json` — v1

## Дисциплина (Правило 5 архитектора)

После каждого прогона:
1. Опус **обязан** добавить новую секцию `## v<N>` с заполненными всеми полями
2. Если значение неизвестно — `?` + комментарий «нужно восстановить из <источник>»
3. Manifest Stage 1/2/3 каждого прогона **должен** содержать секцию `versions` (task 049b закрепил для Stage 2; backlog — для Stage 1/3)
4. До обновления registry — прогон **не считается** final, RP-tag не выставляется

---

## История версий этого документа

| Версия | Дата | Изменение | Кто |
|---|---|---|---|
| v1 | 2026-05-17 | Создание ретроспективно для v54-v60 после Никитиного вопроса «ведёшь ли четкий реестр?» — признан пробел в дисциплине, восстановлено из git log + tasks + памяти | Опус |
