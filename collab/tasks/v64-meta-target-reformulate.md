# Задача v64-meta: gate1_product_checklist target reformulate — Distribution (15K narrative + 3K paspart + 2K historical_notes)

**Статус:** `new`
**Номер:** v64-meta
**Автор:** Опус (роль архитектор+продакт)
**Дата создания:** 2026-05-18
**Тип:** docs (product-decision)
**Sprint:** v64
**Связано:** Никитин feedback v63 «писатель нагоняет объем знаков»; Никитино решение развилка 2b 2026-05-18; v63 stocktake

---

## Контекст

**Никитин feedback v63:**
> «местами кажется, что писатель нагоняет объем знаков. это плохо. может не так жестко ставить таргет по количеству знаков или добивать его врезками историка»

**Текущее состояние:**
- gate1_product_checklist target = **Total chars ≥ 20K** (Вариант А, build_gate1 counter, включая ch_01.content паспортичку-в-тексте)
- Эта метрика подталкивает GW к **padding** — нагон знаков через narrative-многословие (Class 17 «констатация очевидного» возникает)
- Чистый narrative (ch_02..epilogue) рекорд = v61 17 027; v63 = 15 123. Для 90-минутного интервью без выдумок — это **физический потолок**

**Никитино решение развилка 2b:**
> Target 20K = 15K narrative + 3K paspart + **2K historical_notes** (objective context — врезки эпохи)

Это **distribution gate**, не single number. **Каждый компонент measurable**:
- narrative (ch_02..epilogue) = build_gate1 sum chars без ch_01.content
- paspart = ch_01.content + bio_data structured fields rendered
- historical_notes = field count × avg chars + inline `***...***` markers

---

## Universality check

- [x] Метрики generic — применимы к любому subject
- [x] Distribution соотношения reasonable для 90-минутного интервью
- [x] Каждый компонент measurable программно (build_gate1)

---

## Спек

### 1. Обновить `gate1_product_checklist.md` секцию «1. Объём текста»

Заменить existing single-target секцию на distribution gate:

```markdown
## 1. Объём текста (Distribution gate)

**Новый target формат (Никитин 2026-05-18, развилка 2b):**

Target 20K Total = **15K narrative + 3K paspart + 2K historical_notes**

Distribution gate — все три компонента **measurable независимо**, чтобы избежать
GW padding через narrative-многословие. Если narrative <15K — добивать
**historical_notes** (objective context от историка), НЕ narrative-truism.

| Component | Цель | Как считать | Источник правды |
|-----------|------|-------------|-----------------|
| **Narrative (ch_02..epilogue)** | ≥ 15 000 chars | sum chars `content` глав ch_02 + ch_03 + ch_04 + epilogue | build_gate1 per-chapter chars |
| **Paspart (ch_01)** | ~ 3 000 chars | `len(ch_01.content)` (включает «Биография в фактах» markdown) + bio_data structured rendered | build_gate1 ch_01 chars |
| **Historical_notes** | ≥ 2 000 chars | sum chars `historical_notes[].text` (field) + chars в `***...***` markers (inline) | build_gate1 historical_notes summary |
| **Total** | ≥ 20 000 chars | sum выше | build_gate1 Total chars |

### Per-chapter floors (внутри narrative)

| Глава | Floor |
|-------|-------|
| ch_02 (хронология) | ≥ 7 000 chars (главная глава) |
| ch_03 (портрет) | ≥ 4 000 chars |
| ch_04 (эпизоды) | ≥ 2 500 chars |
| epilogue | 800–1 500 chars (узкий диапазон, не разрастаться) |

Sum floors = 14 300 — допускает 700 chars buffer до 15K цели.

### Historical_notes минимумы (per task 046d)

- **Field:** ≥ 3 historical_notes (existing minimum)
- **Inline (`***...***`):** ≥ 5 inline markers (восстановление v62a уровня)
- **Avg note length:** 150-250 chars per note

### Anti-padding принцип

Если narrative <15K и есть свободное место до 20K:
- ✅ **МОЖНО** добивать через `enrich_historical_notes_inline` (task 046d) — objective context от historian
- ✅ **МОЖНО** разворачивать pin-list events до depth ≥3 sentences (per ПРАВИЛО 12)
- ❌ **НЕЛЬЗЯ** padding через narrative-многословие (Class 17 detector flag)
- ❌ **НЕЛЬЗЯ** padding через пафос (Class 6 detector flag)

### Если v64 даёт narrative 16K + historical 1K + paspart 3K = 20K total ✓

Это **PASS distribution gate**. Если narrative 17K + historical 0K + paspart 3K = 20K → **NOT pass** (historical missing).

Если narrative 14K + historical 3K + paspart 3K = 20K → **PASS** (within 1K narrative tolerance).
```

### 2. Стоп-фразы (раздел 4) — extend mention Class 17

В секцию 4 «Стилистика» добавить ссылку на Class 17 patterns:

```markdown
### Class 17 — narrative truism (констатация очевидного)

См. task 043h + `narrative_stop_phrases.json` v4+ categories:
- obvious_responsibility_constatation («брал на себя ответственность... всё ложилось на плечи»)
- accepted_calmly («приняла спокойно», «отнеслась с пониманием»)
- required_strength_and_character («требовало силы и характера»)
- was_not_easy_in_those_years
- ...

Validator flags в `narrative_stop_phrases_check.json` → revision pass переписывает.
```

### 3. Стоп-фразы (раздел 4) — extend mention Class 18 voice

```markdown
### Class 18 — personal-historical voice (требуемая категория)

См. task 046e + pin-list `narrator_voice_anchors` секция.

Validator `personal_historical_voice_check.json` ожидает ≥3 markers ch_02 / ≥2 ch_03 / ≥1 ch_04.

Examples markers:
- «как [rapporteur] помнит, в [период]...»
- «тогда у нас в семье...»
- «когда [rapporteur] был ребёнком, ...»

В отличие от discourse_markers (attribution) и historical_notes (objective) — personal-historical voice = **сочетание** personal pronoun + temporal/era marker + контекст.
```

### 4. Раздел «Финальное решение» — обновить

```markdown
## Финальное решение

| Категория | Кол-во ✅ | Кол-во ⚠️ | Кол-во ❌ |
|-----------|----------|----------|----------|
| 1. Объём (distribution gate: narrative 15K / paspart 3K / hist 2K) | / | / | / |
| 2. Bio_data | / | / | / |
| 3. Известные эпизоды | / | / | / |
| 4. Стилистика (incl. Class 17 narrative truism) | / | / | / |
| 5. Структура | / | / | / |
| 6. Cross-chapter dedup | / | / | / |
| 7. Voice (Class 18 personal-historical) | / | / | / |
| 8. Дашина категория (по возвращении) | / | / | / |

**Решение:** ☐ PASS / ☐ RETRO (>3 ❌ разных категорий) / ☐ POINT_FIX (1-3 ❌)
```

### 5. История версий

```markdown
| v2 | 2026-05-18 | Distribution gate: target 20K Total = 15K narrative + 3K paspart + 2K historical_notes (Никитин decision развилка 2b после v63 «нагон объёма»). Class 17 truism + Class 18 voice добавлены в checklist | Опус |
```

---

## Risk и mitigation

**Risk A: Distribution gate сложнее single number — Niki/Daшa могут запутаться.**

**Mitigation:**
- Сводка в начале text_FULL.md явно показывает все компоненты (build_gate1 уже выводит per-chapter chars + historical_notes count)
- Дополнить build_gate1 output: «Distribution: narrative=15.2K ✅ / paspart=3.1K ✅ / historical=1.7K ⚠️»

**Risk B: Если v64 даёт narrative 14K (точно ниже 15K) — это PASS или fail?**

**Mitigation:**
- Явно зафиксировать tolerance: 14-15K narrative — warning, не error (если total ≥20K). <14K — error.
- В checklist таблице добавить tolerance column

**Risk C: Перераспределение может скрыть проблемы narrative quality.**

**Mitigation:**
- Distribution gate **сочетается** с другими качественными метриками (depth, voice, Class 17 truism, pin-list coverage)
- Объём — necessary, не sufficient
- Финальное решение PASS требует **всех** 8 категорий, не только distribution

---

## Ограничения

- [ ] Никаких изменений в коде build_gate1 (counts уже есть)
- [ ] Дополнить summary вывод distribution breakdown
- [ ] Generic для всех subjects (не Каракулино-специфика)
- [ ] Tolerance явно зафиксирована (14-15K narrative = warning)

---

## Dev Review

**Статус:** ожидает

**[TECH]** — pre-answer от Опуса:
- Изменения только в `collab/context/gate1_product_checklist.md`
- Build_gate1 summary дополнить distribution breakdown (минор code change в task 047 style)
- Никаких новых validators в meta task — distribution use existing build_gate1 counts

**[PRODUCT]** — это сам product decision (Никита sign-off на 2b)

**Сложность:** `xs` (<1 ч — markdown edit)
**Риск:** `low`

---

## Verified-on-run v64

**Cursor:** [после v64] — build_gate1 output показывает distribution breakdown
**Опус:** проверит:
- ✅ Distribution breakdown в text_FULL.md summary header
- ✅ narrative ≥15K (или 14-15K warning), paspart ~3K, historical ≥2K
- ✅ Total ≥20K
- ✅ Checklist gate1_product_checklist.md обновлён

---

## История

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-18 | `new` | Опус |
