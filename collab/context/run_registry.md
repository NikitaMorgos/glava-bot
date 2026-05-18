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

### Components (LLM agents в пайплайне Glava)
- Cleaner: vX
- Fact Extractor: vX
- Historian: vX
- Completeness Auditor (CA): vX
- Ghostwriter (GW): vX
- Fact Checker (FC): vX
- Literary Editor (LE): vX
- Proofreader (PR): vX

### Environment (IDE + LLM для разработки/реализации)
- Cursor agent: chat / Composer 1 / Composer 2 / другое
- Cursor model: Sonnet / Opus / Haiku / другое
- Note: смена model или agent режима → **отдельная** строка в registry (новая переменная, может влиять на quality)

### Configs (per subject)
- known_episodes_<subject>.md: vN
- gazeteer_<subject>.json: vN
- relation_overrides_<subject>.json: vN
- timeline_anchors_<subject>.json: vN
- discourse_markers_<subject>.json: vN
- chapter_sections_anchors_<subject>.json: vN
- temporal_place_names_<subject>.json: vN
- contributors_<subject>.json: vN
- persona_notes_<subject>.json: vN

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

## Политика выбора Cursor agent / model

**Текущая (с 2026-05-18):** Cursor Sonnet до финальной вёрстки (Ворота 4). После — обсуждаем эксперимент с Composer 2 или cheap моделями.

**Изменение Cursor agent/model = новая строка в registry.** При смене:
- Зафиксировать **в каком прогоне** произошла смена
- Verify quality на 1 простой task **до** применения на всём sprint
- Если regression — return предыдущий agent/model + lesson learned

**Прецедент v54-v61:** все прогоны Cursor Sonnet (chat mode). Регрессии (v60 «Наталья», temporal wrong direction) — **не от Cursor model**, а от пробелов в spec'ах (мои) + GW pipeline prompt issues. Sonnet делал свою часть качественно.

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

### Outputs
- Run artifacts: `runs/karakulina-v60-artifacts` @ `3c9b84d` (12 файлов)
- text_FULL.md: 17 427 chars (ch_01=3308 / ch_02=6266 / ch_03=5043 / ch_04=1961 / epilogue=849)
- bio_data.family: 23 (баба Аня excluded ✅)
- historical_notes: 5 field + 0 inline ⚠️ (vs v59 7+9)
- Pin-list: full 15, partial 7, skipped 45 / 67
- Timeline anchors: 7/7 found ✅
- Stage 2 manifest: `ghostwriter_version: v2.21` ✅
- FC verdict: PASS iter2
- Proofreader: 14 исправлений, Δ+3310 chars

### Verification — НЕ PASS Ворот 1 (5 блокеров)

**Закрытые задачи (✅ 7/10):**
- 046b порядок Stage 3 — ✅ (style_checks на финальном тексте)
- 044c relation overrides → final book — ✅ (excluded_by_override отчёт)
- 049b GW manifest tracking — ✅ (v2.21 зафиксирован)
- 043c stop-phrases extended — ✅ (только 1 error + 1 warning vs v59 4 errors)
- 050b pin-list depth scope — ✅ (только narrative ch_02-04)
- 040b gazeteer морфо — ✅ (Сапон 0 в тексте; Сафроново в narrative)
- 048b chronology grandchildren — ⚠️ детектор реализован, сценарий «1973 + внучка» не активировался (GW не написал галлюцинацию)

**Блокеры (❌ 5/10):**
- **052 Contributors галлюцинация** — «Наталья Каракулина» вместо «Татьяна»; только 2 из 4 контрибьюторов; формат другой («роли», не «список людей»). config rogue, не из pin-list v3
- **051 Temporal place names wrong direction** — 3 replacements автоматических все wrong: Тверь→Калинин в context 1920 (когда было Тверь, переименовали в Калинин только в 1931); + 1 warning не fix'ил 1996 «Калинин» (когда уже Тверь). Bug: single transition_year не покрывает multi-rename history
- **046 epilogue auto_rewrite pattern bug** — «прошла путь от сироты ИЗ УКРАИНСКОГО СЕЛА до уважаемой» не покрыт regex (intermediate words между `\w+` и `(до|к)`)
- **045c chapter sections в GW** — config не передаётся в Stage 2 GW system context (Курсор подтвердил follow-up)
- **GW v2.21 промпт не выучил** ПРАВИЛО 6 (discourse markers ch_02=2/8) + ПРАВИЛО 8 (pin-list depth 3 errors)

**Регрессии vs v59:**
- ❌ Власьево / Воскресенская церковь — пропало
- ❌ «У сестёр был разный отец с Валентиной» — пропало
- ❌ Детский сад № 95 — пропало
- ❌ Тётя Маня в bio_data.family — пропала
- ❌ Французская бабушка сравнение с бабой Аней — пропало
- ❌ historical_notes inline 0 (vs v59 9)
- ↘ Total chars 17 427 (vs v59 19 930)

**Не закрылось из Никитиного feedback v59:**
- ❌ Шарлотка, карты подробно, грибы+тётя Маша эпизод, продажа дачи
- ❌ ch_03 раздел «Гостеприимство и кулинария»

### Notes
- v60 sprint: 10 tasks shipped, 7 закрылись формально, 5 блокеров для PASS
- Новые баги обнаружены: 052 contributors галлюцинация, 051 temporal wrong direction, 046 mapping pattern
- Mixed picture: structural improvements (timeline anchors 7/7, family clean, manifest tracking) + content regressions (Власьево, разные отцы, Маня, и т.д.)
- **PASS Ворот 1: НЕ достигнут. Требуется v61 sprint.**

### План v61 sprint — ИЗМЕНЁН (Вариант 1: Hybrid rollback, Никитино решение 2026-05-17)

**Стратегия:** branch off v59 + cherry-pick ТОЛЬКО проверенные scripted fixes из v60. Никитины 3 features отложены в backlog после RP-1, добавляем **по одному**.

**Baseline для diff v61: v59** (изменено с v56 — Никитино решение «v59 — самый удачный бенч»).

#### Cherry-pick из v60 (8 scripted fixes)

| Task | Что |
|---|---|
| 044c | `remove_excluded_bio_data_family` |
| 045b | `validate_timeline_anchors` markdown parser |
| 046b | Stage 3 runner reorder |
| 049b | `_extract_prompt_version` + manifest tracking |
| 050b | `NARRATIVE_CHAPTERS` excludes epilogue |
| 040b | Gazeteer морфо падежи |
| 043c | epilogue_stop_phrases v2 + 4 категории |
| 048b | chronology check grandchildren |

#### Plus 1 минор fix
- **046c** — epilogue rewrite regex с intermediate words («путь от X ИЗ ... до Y»)

#### НЕ берём
- **GW v2.21** → откат к v2.20
- task 051 (temporal — wrong direction)
- task 052 (contributors — галлюцинация)
- task 045c (chapter sections — config not in GW input)

#### Backlog после v61 PASS (по одному за раз!)
- Contributors как чистый скрипт
- Temporal place names с multi-rename history
- Chapter sections (GW prompt-bump только эта 1 правка)

Финансово v61: $2-3.

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

---

## v61 (2026-05-18) — Вариант 1 Hybrid rollback — verified, близко к PASS

**Branch + commit:** `feat/v61-hybrid-rollback` @ `a8809aa`; артефакты `runs/karakulina-v61-artifacts` @ `df6f3f3`
**Status:** verified, БЛИЗКО К PASS Ворот 1 (3 серьёзных + 2 минор блокера для v62 sprint)

### Components
- Cleaner: v1, FE: v3.4, Historian: v3
- CA: v1.4 (как в v59 — pin-list bypass strict)
- **GW: v2.20** (откат от v2.21; battle-tested в v59)
- FC: v2.13, LE: v3.1, PR: v1

### Configs (per subject)
- known_episodes_karakulina.md: v3 (без изменений)
- **gazeteer_karakulina.json: v2** (cherry-pick 040b морфо)
- relation_overrides_karakulina.json: v1
- timeline_anchors_karakulina.json: v1
- discourse_markers_karakulina.json: v1
- persona_notes_karakulina.json: v1
- ❌ chapter_sections_anchors_karakulina.json — НЕ применяется (config not in GW input — backlog)
- ❌ temporal_place_names_karakulina.json — НЕ применяется (broken — backlog)
- ❌ contributors_karakulina.json — НЕ применяется (галлюцинация — backlog)

### Configs (generic)
- **epilogue_stop_phrases.json: v2** (cherry-pick 043c — generic stop phrases расширены)
- **epilogue_rewrite_mapping.json: v2 + 046c fix** (intermediate words в pattern)
- narrative_stop_phrases.json: v1

### Pipeline code (cherry-pick из v60)
- `pipeline_utils.py`:
  - + `remove_excluded_bio_data_family` (044c)
  - + `validate_timeline_anchors` markdown parser (045b)
  - + `validate_chronological_consistency` grandchildren (048b)
  - + `validate_pin_list_depth` NARRATIVE_CHAPTERS excludes epilogue (050b)
  - + `normalize_topo_via_gazeteer` морфо (040b)
  - ❌ НЕ применяется: `validate_temporal_place_names` / `enforce_temporal_place_names` (051 broken)
  - ❌ НЕ применяется: `validate_chapter_sections_anchors` (045c not effective)
- `scripts/test_stage3.py`: reorder auto_rewrite ДО validators (046b)
- `scripts/test_stage2_pipeline.py`: + `_extract_prompt_version` manifest tracking (049b)
- `scripts/build_gate1_full_text.py`: ❌ append_contributors_section НЕ применяется (052 broken)

### Inputs
- Transcripts: TR1+TR2 split-extract
- Pin-list: yes (v3)
- `--known-episodes=collab/context/known_episodes_karakulina.md`
- **Diff baseline: v59** (Никитино решение «v59 — самый удачный бенч»)

### Outputs
- Run artifacts: `runs/karakulina-v61-artifacts` @ `df6f3f3` (10 файлов)
- text_FULL.md: **20 272 chars** (рекорд) — ch_01=3245 / ch_02=8359 / ch_03=5358 / ch_04=2634 / epilogue=676
- bio_data.family: 22 (Марфа отсутствует ⚠️; Мария есть)
- callouts: 9 (vs v59 ?)
- historical_notes: 2 field + 0 inline ⚠️
- Pin-list: full 14, partial 8, skipped 45 / 67
- Stage 2 manifest: `ghostwriter_version: v2.20` ✅
- FC verdict: PASS iter2

### Verification — БЛИЗКО К PASS, 5 точечных блокеров

**Восстановлено vs v60 (контент v59):**
- ✅ Власьево / Воскресенская: 1+2 hits
- ✅ Детский сад № 95: 1
- ✅ Разные отцы у В/П: 1
- ✅ Полина (включая «забрала из детдома»): 3
- ✅ Мария (старшая сестра): 1
- ✅ Французская бабушка (3 hits — comparison)
- ✅ Огурцы развёрнуто, чемодан, Молдавия
- ✅ Карты + домино
- ✅ Шуба + тяжеловат
- ✅ Сервиз + 120 рубл
- ✅ Сафроново (морфо падежи task 040b)
- ✅ Калинин в нарративе, 0 Тверь
- ✅ Почерк, Синтетик, мельхиор
- ✅ Племянницы Римма + Зина в family

**Все 8 cherry-pick fixes работают:**
- 044c family clean (баба Аня excluded ✅)
- 045b timeline anchors 7/7 ✅
- 046b runner order ✅
- 049b manifest tracking (GW v2.20 зафиксирован) ✅
- 050b NARRATIVE_CHAPTERS depth scope ✅
- 040b gazeteer морфо (0 «Сапон» в тексте) ✅
- 043c epilogue stop phrases 0 errors ✅
- 046c epilogue intermediate words ✅
- 048b chronology grandchildren — детектор реализован, не сработал (GW не написал галлюцинацию)

**5 блокеров для PASS:**
1. ❌ Серьёзно: **Бабушка Марфа отсутствует** в bio_data.family (регрессия vs v59 render) — task 044b required persons cherry-pick неполный
2. ❌ Серьёзно: **Render bug `?: ?`** в bio_data.family для тёти Маши / бабы Ани / Нинваны (override entries показываются без имени)
3. ❌ Серьёзно: **«родилась в 1956 году в Твери»** в paspart Татьяны (должно быть «в Калинине»). Task 051 не cherry-picked, paspart-only fix нужен
4. ⚠️ Минор: Внук Никита / Внучка Даша БЕЗ note «сын/дочь Татьяны» (потеряно из v59)
5. ⚠️ Минор: **Discourse markers validator = 0** при реально 10 hits ручного grep + 13 mentions Татьяны (validator overstrict, требует точное имя из rapporteurs config)

### Notes
- v61 sprint = Вариант 1 Hybrid rollback (Никитино решение) — успешно восстановлено 90% content v59 + scripted fixes v60
- v60 GW v2.21 cognitive overhead подтверждён: v61 GW v2.20 (откат) восстановил content
- **Решение по PASS Ворот 1 — ждёт Никитино go:**
  - Опция А: PASS RC (3 минор блокера в build_gate1/bio_data validators — отдельная волна без re-run)
  - Опция Б: **v62 sprint** 5 точечных fixes ($2-3) → чистый PASS — **моя рекомендация**
  - Опция В: отложить точечные fixes на backlog после RP-1
- Lessons learned зафиксированы: Правило 5 (run_registry), Правило 6 (prompt engineering discipline), Universality check построчно

---

## v62a (2026-05-18) — 10 точечных scripted fixes — **НЕ PASS**, регрессия объёма

**Branch + commit:** `feat/v62a-pointed-fixes` @ `db03743` (5 commits 3b3c9df→db03743); артефакты `runs/karakulina-v62-artifacts`
**Status:** verified, **НЕ PASS Ворот 1** (3 блокера: объём, pin-list depth, discourse markers)

### Components
- Cleaner: v1, FE: v3.4, Historian: v3
- CA: v1.4
- **GW: v2.20** (NO change — per Правилу 6 «не bundle prompt правил»)
- FC: v2.13, LE: v3.1, PR: v1

### Configs (per subject)
- **known_episodes_karakulina.md: v4** (+ Anti-facts секция task 043e, + persona_notes для Никита/Даша task 044f)
- gazeteer_karakulina.json: **v2 + paspart-only temporal_place_names** (task 051c — minor subset task 051, только bio_data)
- relation_overrides_karakulina.json: v1
- timeline_anchors_karakulina.json: v1 + widowhood strict separation (task 045e)
- discourse_markers_karakulina.json: v1
- persona_notes_karakulina.json: v1 + Никита/Даша entries (task 044f)

### Configs (generic)
- epilogue_stop_phrases.json: v2 (как v61)
- epilogue_rewrite_mapping.json: v2 + 046c fix (как v61)
- **narrative_stop_phrases.json: v2** (task 043d — +2 categories: speciality_defined_life, helping_at_important_moments)

### Pipeline code (additions/fixes к v61 base)
- `pipeline_utils.py`:
  - + `validate_anti_facts` (task 043e — scripted check pin-list anti_facts pairs)
  - + `apply_temporal_naming_to_paspart_only` (task 051c — minor temporal fix только bio_data)
  - + расширение `validate_chronological_consistency` для grandchildren patterns (task 048c)
  - + `validate_timeline_anchors` strict period separation (task 045e — widowhood)
  - + fix `validate_discourse_markers` rapporteurs config (task 049c)
- `scripts/build_gate1_full_text.py`:
  - + skip `?: ?` override entries (task 044d)
  - + remove duplicate «Основные даты жизни» рендер (task 044d)
  - + append_contributors_section из pin-list v4 (task 052c — clean rewrite)
- `enforce_persona_notes` (task 044f) — read persona_notes_karakulina.json updated с Никита/Даша

### Inputs
- Transcripts: TR1+TR2 split-extract
- Pin-list: yes (v4)
- `--known-episodes=collab/context/known_episodes_karakulina.md`
- **Diff baseline: v59** (Никитино решение от v61 sprint)

### Outputs
- Run artifacts: `runs/karakulina-v62-artifacts` (20+ файлов включая VERIFIED_ON_RUN_v62.md)
- **text_FULL.md book content: 17 750 chars** ⚠️ (NOT 22 927 — Курсор ошибочно использовал file_size как metric; реальный gate1 chars = build_gate1 own counter)
- ch_01=3354 / ch_02=6834 / ch_03=4450 / ch_04=2327 / epilogue=785
- **historical_notes: 10 field + 10 inline** ⭐ (отличное улучшение vs v59 7+9, v61 2+0)
- bio_data.family: 23 (Марфа есть с note «мать отца Валентины» ✅)
- callouts: 7
- Pin-list: full 15, partial 7, skipped 45 / 67
- Timeline anchors: 7/7 found ✅
- Stage 2 manifest: `ghostwriter_version: v2.20` ✅
- FC verdict: PASS iter1 (0 critical, 0 major)

### Verification — НЕ PASS, 3 блокера

**Закрытые задачи (10/11 ✅):**
- 044d render bug ✅ (text_FULL чистый)
- 044e Марфа ✅ (в bio_data.family с note)
- 044f Внук/Внучка notes ✅
- 049c validator fix ✅ работает (но GW не пишет markers → backlog v63)
- 051c paspart Тверь→Калинин ✅
- 048c chronology grandchildren ✅ (1 error в epilogue — partial false positive «1933 + внуки» semantic)
- 052c Contributors clean rewrite ✅ (4 имени из pin-list)
- 043d narrative stop phrases ✅ (1 warning «определило жизнь»)
- 045e timeline anchors widowhood ✅ (7/7 found)
- 043e anti_facts ✅ (af_002 акушерство fired)

**Блокеры для PASS:**

1. ❌ **Объём 17 750 < 20K+ target** (регрессия vs v59 19 930 и v61 20 272). GW v2.20 написал короче — stochastic LLM variance или config recompilation effect (anti_facts введён). ch_02 −18% vs v61.

2. ❌ **Pin-list depth 5 errors** (vs v61 2): ep_005 свадьба, ep_011 операция, ep_012 Кирсанов, ep_027 пенсия, ep_028 Капошвара, ep_030 перелом — все 2 sentences (min 3). GW сжимает narrative.

3. ❌ **Discourse markers all 3 chapters below threshold** (ch_02=0/8, ch_03=2/5, ch_04=0/3). GW v2.20 не пишет rapporteur attribution phrases. Validator fix 049c works, root cause — **GW prompt не инструктирует** → backlog v63 (1 GW правило).

4. ⚠️ Chronology 1 error: «Голод 1933 года... дождалась внуков» в epilogue — semantic false positive (general life summary, не linked timing). Acceptable warning level (errors_count=1, не block).

### Bugs found & fixed during sprint (бонус Курсора)

1. narrative_stop_phrases.json: speciality_defined_life + helping_at_important_moments не в `scoped_to_narrative_and_epilogue` → fix
2. narrative_stop_phrases.json: `\\s+` → `\\s*` в pattern (не матчил «специальность,»)
3. test_stage3.py: build_gate1_text() без pin_list_path → Contributors skipped, fix
4. known_episodes_karakulina.md локально v2 (без Contributors/Anti-facts) → обновлено до v4

### Lesson learned — chars metric ambiguity

Курсор отчитал «Gate-1 text: 22 927 chars >> 20K+ target ✅», но это **`len(file_text)`** всего text_FULL.md (включая summary header, paspart markdown, Contributors раздел, decorations). **Реальный book content** = build_gate1 own counter = **17 750 chars** (только narrative paragraphs).

Lesson: при measuring chars target — что именно меряем? Build_gate1 «Total chars» в сводке = **source of truth** для gate1 metrics. File size — не gate1 metric.

Зафиксировано: при verified-on-run уточнять metric источник.

### Notes
- v62a sprint: 10 scripted + 1 meta, NO GW change. 10/11 tasks succeed как scripts, но GW регрессировал объём.
- Регрессия объёма ch_02 18% — likely stochastic LLM variance (same prompts → разный output) либо subtle config effect.
- **Решение PASS Ворот 1 — ждёт Никитино go (Опции A/B/C/D):**
  - A: v62a-rerun stochastic check ($2-3)
  - B: v63 GW prompt-bump «narrative depth + voice» ($2-3)
  - C: tag RP-1 на v59 (не приемлемо — Никитины items missing)
  - D Hybrid (моё предложение): v62a-rerun first, если <18K → v63 prompt-bump

---

## История версий этого документа

| Версия | Дата | Изменение | Кто |
|---|---|---|---|
| v1 | 2026-05-17 | Создание ретроспективно для v54-v60 после Никитиного вопроса «ведёшь ли четкий реестр?» — признан пробел в дисциплине, восстановлено из git log + tasks + памяти | Опус |
| v2 | 2026-05-17 | + v60 outputs/verification (НЕ PASS, 5 блокеров); + план v61 (Вариант 1 Hybrid rollback после Никитиного решения); baseline для diff изменён v56→v59 | Опус |
| v3 | 2026-05-18 | + v61 verification (близко к PASS, 5 блокеров); + план v62a sprint (10 точечных scripted fixes NO GW change + 11 meta); + backlog v63-v66 (по одной GW правке за раз); target 20K+ | Опус |
| **v4** | **2026-05-18** | **+ v63 verification (НЕ PASS, 4 блокера: Total 18 372<20K, pin-list depth 3 err, discourse markers ch_02/ch_04, Class 5 regression Мария+баба Аня); + lessons (GW v2.22 ПРАВИЛО 12 частично — ch_03/epilogue выросли, ch_02 не сдвинулся; Class 1 confabulation на огурцах новая форма motivation вместо location; чистый narrative ≤17K — рекорд v61); + lesson: VERIFIED_ON_RUN Курсора может содержать self-report ошибки (Татьяна «1952 estimated» — реально в config 1956 high) — cross-check артефактом обязателен** | **Опус** |

---

## v63 (2026-05-18) — combined sprint (9 scripted + 1 CA + 1 GW prompt-bump) — НЕ PASS

**Branch + commit:** `feat/v63-combined-sprint` @ `84a145d`; артефакты `runs/karakulina-v63-artifacts`
**Status:** verified, **НЕ PASS Ворот 1** (4 блокера + 3 минор регрессии)

### Components
- Cleaner: v1, FE: v3.4, Historian: v3
- **CA: v1.5** (task 038c — ПРАВИЛО 7 named entity preservation: location/name/year/characteristic-word)
- **GW: v2.22** (task 049d — ПРАВИЛО 12 narrative depth + voice + объём ≥20K, per-chapter floors, proof-of-attention writing_notes; per Правилу 6 одно правило per bump с 3 metrics одной семьи; **skip v2.21** collision с откатанной v60 версией)
- FC: v2.13, LE: v3.1, PR: v1

### Environment
- Cursor agent: Cursor Agent (chat)
- Cursor model: Sonnet 4
- Без смены vs v62a → не отдельная переменная в registry

### Configs (per subject)
- known_episodes_karakulina.md: **v5** (ep_029 продажа дачи year=unknown, year_confidence=low; task 051d)
- gazeteer_karakulina.json: v2
- relation_overrides_karakulina.json: v1
- timeline_anchors_karakulina.json: v1
- discourse_markers_karakulina.json: v1
- persona_notes_karakulina.json: v1 (+ Никита/Даша)
- **chronology_periods_karakulina.json: v1** (новый, task 048d) — содержит `daughter_tatyana_birth.year=1956 (high)` ✅. NB: в VERIFIED_ON_RUN_v63 Курсор ошибочно написал «1952 (estimated)» — это **bug в self-report**, не в config'е. Reality: config корректен. Lesson: cross-check VERIFIED отчёт с реальным артефактом (Правило 2 архитектора)
- **bio_data_format_config.json: v1** (новый, task 044g) — generic для всех subjects

### Configs (generic)
- **narrative_stop_phrases.json: v3** (task 043g — +event_that_changed_life, typical_for_generation, in_this_typicality_uniqueness, class11_not_loved_x_by_y_and_z)
- **epilogue_rewrite_mapping.json: v3** (task 043g — +typical_for_generation, in_this_typicality_uniqueness rewrite rules)
- epilogue_stop_phrases.json: v2

### Pipeline code
- `pipeline_utils.py`:
  - + `validate_children_before_birth` (task 048d Class 12 extend)
  - + `validate_epilogue_quote_density` (task 043e-2 Class 6 density)
  - + `validate_entity_substitution` stem regex inflection-aware (task 038c scripted defense)
  - + `validate_bio_data_family_format` + locative case check (task 044g)
  - + `parse_pin_list_year_field` поддержка `unknown` / `~1990-е` / `year_confidence` (task 051d)
- `scripts/build_gate1_full_text.py`:
  - + skip empty `### Дополнительный текст ch_01` heading (task 044d-2)
  - + skip malformed override entries в bio_data.family render (task 044d-2)
  - + Contributors render ФИО+родство only (task 052d — `interview_role` + `notes` в data, но не рендерятся)
- `scripts/_run_v63_full.sh` — новый run script (Option X combined sprint)
- `tests/test_v63_sprint.py` — **35/35 snapshot tests** PASS

### Inputs
- Transcripts: TR1+TR2 split-extract
- Pin-list: v5 (with year_confidence support)
- `--known-episodes=collab/context/known_episodes_karakulina.md` (обязателен)
- **Diff baseline: v62a** (incremental); reference: v59 (Никитин «удачный бенч»)

### Outputs
- Run artifacts: `runs/karakulina-v63-artifacts` (21 файл, включая VERIFIED_ON_RUN_v63.md)
- text_FULL.md: **18 372 chars Total** (build_gate1 own counter)
  - ch_01 (паспортичка-в-тексте): 3 249
  - ch_02 (хронология): 6 872 (target ≥8K — **fail**, +38 vs v62a — ≈ноль роста на главной главе)
  - ch_03 (портрет): 5 053 (target ≥4K — pass, +603 vs v62a)
  - ch_04 (эпизоды): 2 230 (target ≥2.5K — **fail**, −97 vs v62a)
  - epilogue: 968 (target 800-1500 — pass, +183 vs v62a)
- text_FULL.md file_size: 38 308 chars (не gate metric, lesson v62a applied)
- bio_data.family: 21 (**Мария и баба Аня выпали** vs v62a 23 — Class 5 regression; Марфа есть)
- historical_notes: 3 field + 0 inline (vs v62a 10+10 — большая регрессия)
- callouts: 6
- Pin-list: full 15, partial 7, skipped 45 / 67 (same as v62a)
- Timeline anchors: 7/7 ✅
- Stage 1 manifest: `ghostwriter_version: v2.22`, `completeness_auditor_version: v1.5` ✅
- FC verdict: не зафиксировано явно в artifacts (нужно уточнить у Курсора)

### Verification — НЕ PASS, 4 блокера + 3 минор регрессии

**Закрытые tasks по форме (11/11 PASS code-side):**
- 048d chronology «1946 + дети» flagged error ✅
- 044d-2 render bug → 0 malformed, empty heading скрыт ✅
- 043g «событие изменило» + «типичной для поколения» → 0 в narrative ✅
- 051d ep_029 year=unknown + parser ✅
- 043f Class 11 awkward → 0 в тексте + snapshot test ✅
- 043e-2 epilogue density → 0 quotes в epilogue ✅
- 044g bio_data единый формат ✅ (минор: «Калинин» в дочери Татьяны без locative case)
- 052d Contributors ФИО+родство only ✅
- 038c CA v1.5 ПРАВИЛО 7 → «из Молдавии» preserved в description ✅
- 049d GW v2.22 ПРАВИЛО 12 → активен ✅ (target effect не достигнут)
- configs v3/v1 ✅

**4 блокера для PASS:**
1. ❌ **Объём Total 18 372 < 20 000 target** (Никита confirmed metric = Total chars build_gate1, не file_size). Дефицит 1 628 chars. ch_02 +38 chars vs v62a (≈ноль роста на главной хронологической главе)
2. ❌ **Pin-list depth 3 errors:** ep_003 призыв 1941 (2 предл.), ep_027 пенсия 1994 (1 предл!), ep_028 свадьба Татьяны 1996 (2 предл.), ep_030 перелом 2005. Прогресс vs v62a 5→3, но не 0
3. ❌ **Discourse markers ch_02=2/8, ch_04=0/3** (ch_03=5/5 pass ✅). GW v2.22 ПРАВИЛО 12 не убедило писать rapporteur attribution в хронологии и эпизодах
4. ❌ **Class 5 regression: Мария + баба Аня выпали** из bio_data.family (были в v59/v61/v62a; 21 vs 23). Курсор сам отчитал «Кандидаты для pin_list v6 / required_persons»

**3 минор регрессии:**
1. ⚠️ **Огурцы — новая Class 1 confabulation:** v62a «не привозит подарки из командировок» (location generalisation), v63 «ей казалось, что родственники мужа должны присылать больше подарков» (motivation confabulation). Task 038c защитил location ✅, но не закрыл causal mechanism
2. ⚠️ **Epilogue — новые Class 6 клише:** «принадлежала к поколению, которое строило советскую страну, воевало за неё и верило в её идеалы», «человек долга, который всегда знал, что правильно». Task 043g закрыл 2 конкретных pattern'а, GW нашёл аналогичные для заполнения объёма
3. ⚠️ **historical_notes 0 inline + 3 field** (vs v62a 10+10). Не блокер v63, но потенциально критично для содержательности

**Style checks (other warnings):**
- 1 warning «определило жизнь» в ch_02 (`speciality_defined_life`, не закрыто из v62a)
- 1 warning «судьба распорядилась» в ch_02 (новое клише — кандидат для расширения patterns)

### Lesson learned v63

1. **GW v2.22 ПРАВИЛО 12 (3 metrics одной семьи) — частично сработало:**
   - ch_03 +603 chars + discourse markers 0→5 (target ✅)
   - epilogue +183 chars, без overcrowded quotes ✅
   - **НО:** ch_02 +38 chars (main chapter), pin-list depth ep_003/027/028/030 не развёрнуты, ch_02 markers 0→2 (target 8)
   - Гипотеза: на ch_02 пересекается max-density существующих правил (ЗАПРЕТЫ 8/9/10/11/12 + ПРАВИЛА 5/6/7/8/12) → cognitive overload именно на главной главе. ПРАВИЛО 12 повысило depth где было свободнее (ch_03/epilogue), не там где плотнее (ch_02)
   - **Триггер task 037 (GW prompt refactor) сработал давно** (GW v2.22 ≈2200 строк), пора рассматривать

2. **Recurring patterns Class 1 продолжают возвращаться в новых формах:**
   - v56 → v60 → v62a → v63 — каждый раз GW находит новую форму причинно-следственного confabulation на огурцах
   - Lesson v62a (snapshot tests mandatory) применён в v63 (043f Class 11 поймал), но Class 1 на огурцах **по форме** не fit любому из current patterns
   - Backlog: расширить snapshot tests для Class 1 на новые формы (motivation confabulation, не только location)

3. **«Чистый narrative» (без ch_01) рекорд = 17K, никогда не было 20K:**
   - v59 ≈16K, v61 = 17 027, v62a = 14 396, v63 = 15 123
   - Target 20K Total включает ch_01.content (паспортичка-в-тексте ≈3.2K chars). Никита confirmed metric = Total build_gate1 (Вариант А)
   - На метрике «чисто narrative ch_02..epilogue» рекорд = v61 17K — для 90-минутного интервью без выдумывания может быть физический потолок

### Notes

- 11/11 tasks PASS code-side, но 4 блокера на effect → НЕ PASS Ворот 1
- v63 sprint = первый combined (Опция X) — scripted + CA minor + GW prompt-bump в одном прогоне
- **Решение по v64 — ждёт Никитино go (Опции A/B/C/D):**
  - A: stochastic rerun v63 (same code, $2-3) — проверить variance гипотезу
  - B: v64 GW revision loop volume-based (1 правило prompt-bump, $4-6 за 2 LLM-passes)
  - C: pin-list v6 (Мария + баба Аня в required_persons, $2-3) — закрывает Class 5 regression, не решает M1 объём
  - D: tag RP-1 на v63 как-есть, items в backlog после RP-1
