# Задача: LE удаляет ch_01.timeline (6 этапов → 0) — Stage 3 регрессия

**Статус:** `new`
**Номер:** 034
**Автор:** Опус
**Дата создания:** 2026-05-08
**Тип:** `cco-скрипт` + `промпт` (defense Stage 3)
**Связано:** task 015 (пилот), task 027 (bio_data completeness, в работе), task 033 (отменённая волна 1.4.0 — over-engineering на фантомный класс), `karakulina-versions-metrics.md`

---

## Контекст

При диагностике v53b обнаружена **реальная регрессия Stage 3 Literary Editor** — но не та которую мы первоначально предполагали:

- **Stage 2 GW v2.16 на TR2 правильно генерирует** `chapters[ch_01].timeline` — массив из 6 этапов жизни (1920-1933 детство, 1938-1945 война, 1946-1962 семья, 1962-1978 работа, 1978-1994 самостоятельность, 1994-2005 пенсия). Каждый этап содержит `period`, `title`, `text` — соответствует спеке GW v2.16 (4-7 этапов).

- **Stage 3 LE (`05_literary_editor_v3.md`)** в выходе **не содержит** `chapters[ch_01].timeline`. Поле полностью отсутствует. LE возвращает только `content` для каждой главы + `callouts[]` + `historical_notes[]` + `edits_log[]`.

Файлы для подтверждения (в ветке `feat/v53-artifacts`):
- `collab/runs/karakulina_v53b/karakulina_v53b_book_FINAL_stage2_20260508_051041.json` — `chapters[ch_01].timeline` = 6 items
- `collab/runs/karakulina_v53b/karakulina_v53b_book_FINAL_stage3_20260508_053229.json` — `chapters[ch_01].timeline` = 0 items
- `collab/runs/karakulina_v53b/karakulina_v53b_liteditor_report_20260508_053229.json` — verdict: pass, edits_log: 5 правок (без timeline-related)

LE делает 5 cтилистических правок (callout-добавления, fact-corrections), `verdict="pass"` — **формально проходит**. Но `timeline` поле просто **не возвращается в output** — LE его игнорирует.

---

## Корень

**LE промпт v3 не описывает правила обработки `chapters[ch_01].timeline` поля.** В output schema LE есть только `chapters[].content` + callouts + historical_notes + edits_log. Поля `bio_data` и `timeline` в schema LE отсутствуют → модель их не возвращает → они теряются в book_FINAL_stage3.

**Это паттерн «output schema mismatch»** — LE «не знает» что нужно сохранять структурированные поля главы. Промпт-уровень не покрывает структурное preservation, только текстовое.

**Это похоже на task 027** (bio_data.family деградация в v40), но другой сценарий:
- 027: GW в Stage 2 неправильно генерирует bio_data.family (3 вместо 16) — Stage 2 проблема
- 034: LE в Stage 3 теряет уже созданное в Stage 2 chapters[ch_01].timeline — Stage 3 проблема

---

## Сравнительные данные v36 vs v53b

| Поле | v36 Stage 3 | v53b Stage 2 | v53b Stage 3 |
|---|---|---|---|
| `bio_data.family` | 16 | 16 | 16 ✅ |
| `bio_data.awards` | 7 | 7 | 7 ✅ |
| `bio_data.timeline` | 0 | 0 | 0 (не заполнен GW) |
| `chapters[ch_01].timeline` | 0 | **6** ✅ | **0 ❌ — LE удалил** |
| `ch_01.content` | "Каракулина...Родилась 1920..." (109 chars) | "" | "Каракулина Валентина Ивановна. Родилась 1920." (45 chars, ensure_ch01_bio_content fallback) |

**Важное наблюдение:** в v36 Stage 3 timeline тоже пуст. Значит это **не та регрессия которая объясняет почему Никите v36 нравится больше v53b**. v36 «нравится» из-за вёрстки (53 стр с дублями LD-багов), не из-за ch_01.timeline.

Тем не менее — поле `chapters[ch_01].timeline` существует в спеке GW v2.16 (строки 779-793), GW его правильно создаёт, и LE не должен его удалять. Это объективно регрессия в Stage 3, независимо от того связана ли она с восприятием конкретных версий.

---

## Спецификация

### Что нужно

**1. Промпт-уровень — LE v3 → v3.1.**

Расширить output schema LE: `chapters[]` должны включать **byte-identical preservation** всех структурных полей кроме `content`/`callouts`/`historical_notes`. Перечислить явно:
- `chapters[].id` (preserve)
- `chapters[].title` (preserve, могут быть мелкие правки)
- `chapters[].order` (preserve)
- `chapters[].bio_data` (preserve byte-identical для ch_01)
- `chapters[].timeline` (preserve byte-identical для ch_01)
- `chapters[].facts_used` (preserve)
- `chapters[].is_modified` (LE проставляет true/false)
- `chapters[].content` (LE редактирует)
- `chapters[].paragraphs` (LE может потерять — это ОК, это derived от content)

Добавить top-priority правило в начале промпта:
> ⚠️ ВАЖНО: ты редактируешь только `chapters[].content` и `callouts[]`. Все остальные поля главы (`bio_data`, `timeline`, `facts_used`, `id`, `title`, `order`) ты обязан вернуть в выходе **без изменений** ровно так как они были на входе.

Включить negative example:
> v53b: GW сгенерировал `chapters[ch_01].timeline` с 6 этапами жизни. LE вернул главу без поля timeline. Это удалило хронологию из финальной книги. ❌

**2. Код-уровень — `pipeline_utils.preserve_chapter_structural_fields`.**

После Stage 3 LE, перед сохранением book_FINAL_stage3, программно копировать все non-content поля из book_before_le в book_after_le:

```python
def preserve_chapter_structural_fields(book_before_le, book_after_le):
    """
    Защита Stage 3: LE может изменять только content/callouts/historical_notes.
    Все остальные структурные поля главы (bio_data, timeline, facts_used) 
    копируются byte-identical из book_before_le.
    
    LE-mutable fields: content, paragraphs (derived), is_modified
    LE-immutable fields: id, title, order, bio_data, timeline, facts_used
    """
```

Интеграция в `scripts/test_stage3.py` после `run_literary_editor_async` и до save book_after_le.

**3. Тесты.**

`tests/test_le_structural_preservation.py`:
- Happy path: LE возвращает все поля → код просто проходит
- Регрессия v53b: LE возвращает chapter без timeline/bio_data → код восстанавливает из book_before
- Edge: глава у которой не было bio_data → пропускается
- Не мутирует входы

### Что не делать в этой задаче

- Не лечить bio_data.timeline=[] в Stage 2 GW (это task 027 / отдельная задача)
- Не пытаться спроектировать защиту от удаления контента LE — мы уже выяснили что это **не происходит** на полных прогонах (огурцы в v53b сохранились). Защита нужна только на структурных полях.
- Не лезть в LE стилистическую логику (callouts, repetition removal — это его работа)

### Бюджет

~0.5-1 день. Это маленькая прицельная защита, не масштабная волна.

---

## Verified-on-run

> Заполняется ОБЯЗАТЕЛЬНО перед закрытием.

**Ожидание:** v54 на TR1+TR2 → `chapters[ch_01].timeline` имеет 4-7 этапов в book_FINAL_stage3.

**Cursor — observation:** [после v54: открыть `book_FINAL_stage3_v54.json`, найти `chapters[0].timeline`, привести список этапов с период/title]

**Опус — independent observation:** [независимо открыть тот же файл, проверить что timeline preservation работает]

---

## Что не делаем сейчас

- Откат волны 1.4.0 (PR #14 закрывается с пометкой over-engineering — отдельный документ)
- Запуск v54 — ждёт реализацию task 034
- Layout / vёрстку — не обсуждаем по решению Никиты

---

## Комментарии

### 2026-05-08 — Опус (создание)

Задача появилась в ходе диагностики v53b после расширения продуктовой задачи Никитой. **Регрессия #7 (LE удаляет огурцы) — оказалась несуществующей** при прямой проверке артефакта (`book_FINAL_stage3_v53b.json` содержит огурцы в ch_02). Это привело к закрытию PR #14 (волна 1.4.0).

В процессе той же диагностики обнаружена **другая** реальная регрессия — удаление `chapters[ch_01].timeline`. Это объективная Stage 3 проблема (поле должно сохраняться по архитектуре пайплайна), хотя визуально она не объясняет восприятие Никитой v36 как «лучшего».

Дисциплинарное наблюдение: эта задача — пример того почему **artefact-direct verification** обязательна. Регрессия #7 (фантом) была обнаружена через Курсорский пересказ; настоящая регрессия (timeline) — только при прямом чтении JSON.

---

## История статусов

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-08 | `new` | Опус |
