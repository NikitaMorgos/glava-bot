# Задача 049d: GW v2.22 ПРАВИЛО 12 — Narrative depth + voice rapporteurs + объём ≥20K

**Статус:** `new`
**Номер:** 049d
**Автор:** Опус (роль архитектор+продакт)
**Дата создания:** 2026-05-18
**Тип:** `промпт` GW (prompt-bump)
**Sprint:** v63
**Связано:** Mои 3 блокера v62a — M1 (объём 17 750 < 20K), M2 (pin-list depth 5 errors), M3 (discourse markers all 3 chapters below threshold). v60 GW v2.21 (откатанная) — superseded; base = GW v2.20 (battle-tested v59/v61/v62a).

---

## Контекст

### Три блокера v62a (все GW-related, скрипты не лечат)

| # | Проблема | Эффект |
|---|----------|--------|
| M1 | Объём 17 750 chars < 20K target | ch_02 sub-7K, epilogue 785, regression vs v59 (19 930) и v61 (20 272) |
| M2 | Pin-list depth 5 errors (свадьба, операция, Кирсанов, пенсия, Капошвара, перелом — 2 sentences вместо 3+) | GW сжимает narrative по pin-list events |
| M3 | Discourse markers all 3 chapters below threshold (ch_02=0/8, ch_03=2/5, ch_04=0/3) | GW не пишет rapporteur attribution phrases вообще |

**Корень всех трёх:** GW v2.20 (без ПРАВИЛА 6/7/8 из откатанной v2.21) не имеет в промпте:
- Explicit target chars (sub-K vs ≥20K)
- Explicit instruction для depth (≥3 sentences per pin-list event)
- Explicit instruction для discourse markers (rapporteur voice in narrative)

Validators (049c, 050b) — корректно flag, но **GW не инструктирован**. **Класс «GW prompt не учит правило → validator flag не имеет эффекта»** — устранён только prompt-bump.

### Per Правило 6 — 1 rule per bump

ПРАВИЛО 12 объединяет **3 metrics одной семьи** (depth+voice+volume — все о «как разворачивать narrative»):
- Конкретные targets numeric (chars, sentences, markers count)
- Все 3 metrics сейчас **низко** в v62a → одно правило с тремя targets, не три отдельных
- Bundle 3 metrics в одно правило, **не 3 отдельных правила** (per Правило 6)

**Альтернативное прочтение Правила 6** — 1 правило про **одну ментальную операцию** «как разворачивать narrative» (объём + глубина + голос). Это не bundle разных concerns (e.g. style + factual + structure). Это family of related metrics.

### Версионирование GW

- GW v2.20 — battle-tested base (v59, v61, v62a)
- GW v2.21 — superseded (v60 rules 9/10/11 откатаны)
- **GW v2.22** = v2.20 + ПРАВИЛО 12 (chosen — избегает collision с v2.21 файлом)

---

## Universality check (КРИТИЧНО — Правило 4 архитектора)

- [x] Промпт без конкретики subject? Targets numeric, primary subject — generic placeholders (`[субъект]`, `[рассказчик]`, `[характерное слово]`)
- [x] Subject-specific конкретика — в config/pin-list per subject (discourse markers rapporteurs в `discourse_markers_<subject>.json`; pin-list events в `known_episodes_<subject>.md`)
- [x] Алгоритм generic — targets применимы к любой 90-минутной биографии
- [x] **Subject-replacement test построчно** — см. секцию ниже

**Trap warning:** не зашить Каракулино-конкретику в текст промпта. Все examples — generic, через placeholders.

---

## Спек

### 1. Promptbump — GW v2.20 → GW v2.22

**Файл:** `prompts/03_ghostwriter_v2.22.md` (новый, копия v2.20 + ПРАВИЛО 12)

**Шапка обновляется:**
```
# Системный промпт: Писатель (Ghostwriter)
## Роль 03 в пайплайне Glava
## Версия: v2.22 (2026-05-18, Opus, task 049d, v63 sprint)
### Изменения v2.22 (v63 sprint): 1 новое правило, расширенный scope:
### • НОВОЕ ПРАВИЛО 12: NARRATIVE DEPTH + VOICE + ОБЪЁМ — explicit targets для глубины разворачивания, голоса рассказчика и общего объёма book content
###
### v2.22 = v2.20 + ПРАВИЛО 12 (НЕ продолжение откатанной v2.21).
### v2.21 содержала ПРАВИЛА 9-11 (temporal place names, contributors, chapter sections)
### которые показали регрессию в v60 — откат к v2.20 в v61 (Hybrid rollback).
### v2.22 берёт base v2.20 (battle-tested) + добавляет ПРАВИЛО 12.
###
### Per Правило 6 архитектора (prompt engineering discipline):
### одно новое правило per prompt-bump. ПРАВИЛО 12 содержит 3 связанных
### metrics (depth/voice/volume) — все одной ментальной операции
### «как разворачивать narrative». Не 3 отдельных правила.
```

**Тело правила** — добавить в раздел ПРАВИЛА (после ПРАВИЛА 5 v2.20):

```
══════════════════════════════════════════════════════════════════
ПРАВИЛО 12 — NARRATIVE DEPTH + VOICE + ОБЪЁМ (v2.22)
══════════════════════════════════════════════════════════════════

Биографическое жизнеописание для 90-минутного интервью должно
быть достаточно объёмным, разворачивать ключевые события и
сохранять голос рассказчика. Это правило фиксирует три связанных
target'а.

A. ОБЪЁМ BOOK CONTENT — ≥ 20 000 chars

   Total chars (только narrative content: ch_01.content +
   ch_02.content + ch_03.content + ch_04.content +
   epilogue.content; БЕЗ paspart structured fields, БЕЗ callouts
   metadata) — целевой минимум **20 000 chars**.

   Per-chapter floor (минимум):
   - ch_02 (хронологический): ≥ 8 000 chars (главная глава)
   - ch_03 (портрет/характер): ≥ 4 000 chars
   - ch_04 (эпизоды/факты): ≥ 2 500 chars
   - epilogue: 800–1 500 chars (узкий диапазон — не разрастаться)

   Если по pin-list events / fact_map не хватает материала
   для floor конкретной главы → не выдумывай факты для добивки
   объёма. Расширяй ТОЛЬКО разворачиванием существующих фактов
   (контекст эпохи через historical_notes, дополнительные
   sentences per event из pin-list, voice цитаты рассказчика).

   ⛔ НЕЛЬЗЯ ради объёма:
   — добавлять выдуманные эмоции, мотивы, причинные связи
   — повторять одни и те же факты в нескольких главах
     (это нарушение cross-chapter dedup, Правило 5)
   — расширять epilogue пафосными обобщениями
     (см. ЗАПРЕТ 8 + epilogue_stop_phrases config)

   ✅ МОЖНО ради объёма:
   — разворачивать pin-list events на ≥ 3 sentences с конкретикой
     (см. подпункт B ниже)
   — добавлять voice рассказчика — цитаты из transcripts,
     atribution phrases (см. подпункт C ниже)
   — historical_notes контекст (1–3 sentence связки между фактами)

B. NARRATIVE DEPTH — pin-list events ≥ 3 sentences

   Каждый эпизод из PIN_LIST_EVENTS блока в input должен быть
   развёрнут на **≥ 3 sentences** в narrative главы, где он
   рассказан подробно (main chapter per cross-chapter dedup).

   Структура развёрнутого эпизода (типовая):
   1. Setup (год + место + кто) — 1 sentence
   2. Что произошло (action / event core) — 1+ sentence
   3. Деталь из источника или последствие — 1+ sentence

   ❌ ПЛОХО (depth=2 sentences):
     "В 1946 году Валентина вышла замуж за [супруга]. Свадьба
      прошла в [городе]."
     ↑ нет деталей: знакомства, время до свадьбы, источник

   ✅ ХОРОШО (depth=3+ sentences):
     "Знакомство с [супругом] было быстрым — две недели от
      встречи до свадьбы. Расписались 12 июля 1946 года в
      [городе]. Источник вспоминает: «[характерная цитата]»."

   Pin-list event с year_confidence=unknown — НЕ привязывать к
   конкретному году в narrative (см. PIN_LIST_EVENTS input).

C. VOICE — DISCOURSE MARKERS ≥ THRESHOLD PER CHAPTER

   В нарративе обязательно присутствие голоса рассказчика — фраз
   которые явно атрибутируют источник:

   Discourse marker = одна из:
   - "[рассказчик] вспоминает / рассказывает / отмечает / говорит"
   - "по словам [рассказчика] / по воспоминаниям [рассказчика]"
   - "источник интервью отмечает / говорит"
   - "как вспоминает [родственное_отношение]" (e.g. «как вспоминает дочь»)
   - "интервьюер [имя_внука] спрашивает / уточняет" (опционально, если
     был со-интервьюер)
   - указание авторства реплики: "«цитата», — [говорит] [рассказчик]"

   ⛔ Discourse marker ≠ просто упоминание имени рассказчика
     ("у [рассказчика] была дача" — это narrative, не voice).
     Voice = explicit attribution **речи** или **воспоминания**.

   Минимум discourse markers per chapter:
   - ch_02 (хронологический, главная): ≥ 8
   - ch_03 (портрет): ≥ 5
   - ch_04 (эпизоды): ≥ 3
   - epilogue: 0–2 (не обязательно; spokoyno без markers)

   Rapporteurs config — список actual rapporteurs interview'а
   (в input — `discourse_markers.rapporteurs` / aliases).
   Используй ИХ имена/aliases, не generic «рассказчик» если есть
   конкретный rapporteur.

══════════════════════════════════════════════════════════════════

EXAMPLES (placeholder-based — все слова субъекта/рассказчика/мест
заменены на абстрактные плейсхолдеры, чтобы LLM учил **структуру**
паттерна, не запоминал конкретный subject):

Плейсхолдеры (генерик):
  [Субъект]      = биографируемая персона
  [Рассказчик]   = primary interview source (имя из rapporteurs config)
  [Близкий]      = родственное лицо из fact_map.persons
  [Город_канон]  = canonical place name (после Name Normalizer / gazeteer)
  [YYYY]         = конкретный год из fact_map.timeline
  [деталь_из_TR] = характерная цитата/слово из transcripts
  [событие_X]    = pin-list event description

✅ Pin-list event развёрнут с voice (ch_02 паттерн, 3 sentences):
   "В [YYYY] году [Субъект] [глагол] [событие_X] — [деталь_из_TR
    про обстановку/время/конкретику]. [Рассказчик] вспоминает:
    «[прямая цитата из transcripts]». [Дополнительная деталь
    события: место/последствие/связка]."

   Метрики паттерна:
   - depth = 3 sentences ✅
   - discourse marker = «[Рассказчик] вспоминает: ...» ✅
   - year + место/имя + конкретика из TR ✅
   - chars ≈ 220–260

   Если для каждого pin-list event использовать аналогичный паттерн
   + historical_notes для эпохального контекста → общий объём
   ch_02 8 000+ chars достижим естественно, без выдумывания фактов.

❌ Pin-list event схлопнут без voice (depth=2, без attribution):
   "В [YYYY] году [Субъект] [глагол] [событие_X]. [Краткая привязка]."

   Метрики:
   - depth = 2 sentences ❌
   - discourse markers = 0 ❌
   - chars ≈ 50
   - факт формально сохранён, но книга превращается в bullet-list

Subject-replacement test (для саморевизии): замени плейсхолдеры на
имена/даты другого subject (например другую персону, другие годы,
другой город) — структура паттерна должна работать без правок.

══════════════════════════════════════════════════════════════════

PROOF OF ATTENTION — required at output:

В `writing_notes` (output поле) укажи:
- "rule12_chars_estimate": приблизительный count total book content chars
- "rule12_pin_list_depth_pass": true если все pin-list events ≥3 sentences
- "rule12_voice_count_per_chapter": {"ch_02": N, "ch_03": M, "ch_04": K}

Эти поля помогают валидаторам (build_gate1, validate_discourse_markers,
validate_pin_list_depth) cross-check заявленное vs реально написанное.

══════════════════════════════════════════════════════════════════
```

### 2. Подключение

`prompts/pipeline_config.json` — `ghostwriter.prompt_file` → `"03_ghostwriter_v2.22.md"`; `_notes` обновить.

### 3. Subject-replacement test (Правило 4 архитектора)

**Каждая строка** ПРАВИЛА 12 проверена построчно — ни одного:
- «Каракулина» / «Татьяна» / «Валентина» (placeholder `[Субъект]`, `[Рассказчик]`)
- «Химинститут» / «Сафроново» / «Калинин» в правиле (placeholder `[Город_канон]`)
- «1956» / «1946» как specific anchor (примеры years указаны для **демонстрации структуры** — calibrate с reviewer)

**Mental test:** замена `[Субъект]` → «Иван Дмитриев», `[Рассказчик]` → «сын Алексей», `[Город_канон]` → «Тула» → правило **работает без правок** ✅

Subject-specific values приходят через **input data**:
- pin-list events (per subject) — описывают что разворачивать
- discourse_markers rapporteurs config (per subject) — actual names
- fact_map.persons / locations (per subject) — canonical names

### 4. Тесты

`tests/test_gw_v222_proof_of_attention.py` (новый):
- GW output должен содержать `writing_notes.rule12_chars_estimate` (number)
- `writing_notes.rule12_pin_list_depth_pass` (boolean)
- `writing_notes.rule12_voice_count_per_chapter` (dict с ch_02/ch_03/ch_04 keys)
- Если поля отсутствуют — flag warning «rule12 proof missing»

Note: эти тесты — на schema. Реальное соблюдение depth/voice/volume проверяют existing validators (049c, 050b, build_gate1 chars counter).

### Какой результат ожидается

В v63:
- `karakulina_v63_text_FULL.md` Total chars ≥ 20 000
- ch_02 chars ≥ 8 000
- ch_03 chars ≥ 4 000
- ch_04 chars ≥ 2 500
- epilogue chars 800–1 500
- `discourse_markers.json`: ch_02 ≥ 8, ch_03 ≥ 5, ch_04 ≥ 3
- `pin_list_depth.json`: 0 errors (все pin-list events ≥ 3 sentences)
- `book_FINAL.writing_notes.rule12_*` filled
- Stage 2 manifest: `ghostwriter_version: v2.22`

### Как проверить

1. **Unit-тесты** (schema only) — см. выше
2. **Integration на v62a** не возможна (это новый промпт, нужен прогон)
3. **Verified-on-run** v63:
   - Открыть text_FULL.md — Total chars ≥ 20 000
   - Per-chapter chars ≥ thresholds
   - discourse_markers, pin_list_depth — все ≥ thresholds / 0 errors
   - writing_notes содержит rule12 proof fields

---

## Risk и mitigation

**Risk:** **stochastic LLM variance** — v62a vs v59/v61 показала ±18% в ch_02 без изменений config. GW может outputs 18-19K даже с rule 12.

**Mitigation:**
1. Explicit target chars **в промпте** (а не только в config) — самый сильный сигнал LLM
2. Per-chapter floor — препятствует «всё в ch_02, ничего в ch_04»
3. Proof-of-attention writing_notes — заставляет LLM подсчитать estimate
4. **Backlog v64** если v63 даёт <20K — GW revision loop (volume-based revision):
   - После Stage 2 — если chars < 20K, автоматический revision pass с targeted hint «Расширь narrative по pin-list events, depth ≥3 sentences each»
   - НЕ в v63 scope — отдельный prompt-bump (Правило 6)

**Risk:** **cognitive overhead** — 12-е правило в длинном промпте (≥2 000 lines). LLM может «забыть» предыдущие правила.

**Mitigation:**
1. ПРАВИЛО 12 размещено **после** существующих ПРАВИЛ (priority по позиции снижается, но это не критично — правило **дополняет** narrative разворачивание, не conflict'ит с existing)
2. Per Правило 6 — после v63 verify: если предыдущие правила деteriorировали → откат
3. Триггер task 037 (GW prompt refactor ≥2 000 lines) — backlog после v63 если структура промпта становится unwieldy

---

## Ограничения

- [ ] **Один промпт-bump v2.20 → v2.22** (НЕ через v2.21 — collision)
- [ ] **Per Правило 6** — одно новое правило (ПРАВИЛО 12), не 3 отдельных
- [ ] **3 metrics одной семьи** (depth+voice+volume — все про разворачивание narrative)
- [ ] **Universality** — никакой subject-конкретики в правиле (placeholders)
- [ ] **Subject-replacement test построчно** — выполнен
- [ ] **Proof of attention** в output (writing_notes) — обязательно
- [ ] **Не enforce volume через выдумку** — расширять только разворачиванием существующих фактов

---

## Dev Review

**Статус:** ожидает

**[TECH]** — pre-answer от Опуса:
- Файл: `prompts/03_ghostwriter_v2.22.md` (новый, копия v2.20 + ПРАВИЛО 12). НЕ переписывать существующий `03_ghostwriter_v2.21.md` — оставить как archived
- `pipeline_config.json.ghostwriter.prompt_file` → `"03_ghostwriter_v2.22.md"`
- В _notes обновить — текущая версия v2.22 + причина (task 049d, ПРАВИЛО 12)
- writing_notes proof fields — добавить в output schema, validator чекает presence (не values — values как hint, реальная verification через existing validators)
- Если v2.20 имеет ПРАВИЛО 11 (старое) — переименовать НЕ нужно; новое = ПРАВИЛО 12 (next номер)

**[PRODUCT]** — нет (Никитин target 20K — gate1 checklist updated в v62a meta)

**Сложность:** `s` (1-3 ч — копия v2.20 + добавление текста ПРАВИЛА 12 + schema test)
**Риск:** `medium` (GW prompt-bump, stochastic variance risk; mitigated через explicit targets + proof-of-attention)

---

## Verified-on-run

**Cursor:** [после v63 прогона] — отчёт по chars, discourse markers, pin-list depth
**Опус:** независимо откроет `karakulina_v63_text_FULL.md`, посчитает chars per chapter, проверит writing_notes

---

## История

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-18 | `new` | Опус |
