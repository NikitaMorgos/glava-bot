# Задача: Волна 1.4.0 — LE fact preservation guard (промпт + code validator)

**Статус:** `dasha-review` (реализовано, ждёт verified-on-run на v54)
**Номер:** 033
**Автор:** Опус
**Дата создания:** 2026-05-08
**Тип:** `промпт` + `cco-скрипт` (defense in depth)
**Связано:** task 031 (v52/v53 прогон, сценарий C), архитектурный аудит (PR #13), волны 1.2.2 / 1.3.3 как паттерн

---

## Контекст

v53b показал новый класс мутации: **регрессия #7 — Stage 3 LE silent deletion**.

Конкретный кейс: TR2 (Каракулина, 2-й транскрипт). Stage 2 защиты (FC v2.13 + GW v2.16 + scope merge + evidence-check) пропустили эпизод об огурцах в Молдавии в `book_FINAL_stage2 ch_02` ✅. Stage 3 LE v3 удалил эпизод — посчитал дублем с другим эпизодом «конфликт с зятем». Прогон формально завершился (gate2c PDF 27 стр.), но в финальной книге огурцов нет.

**Корень — два уровня:**

1. **Промпт LE v3** — в направлениях работы прямо сказано «3. ПОВТОРЫ — устранение дублей (одна история рассказана дважды)». Промпт **не различает**: «стилистический повтор фразы внутри эпизода» (можно убрать) vs «разные сюжетные эпизоды одной темы» (нельзя удалять).
2. **Архитектурно** — на Stage 2→3 transition нет post-validator. `validate_revision_volume` (волна 1.2.2) работает между revision-итерациями GW, не на LE проходе. `validate_layout_fidelity` — на Stage 4. Stage 3 был слепым пятном.

Это **сценарий C** из task 031 — точно тот риск который описан в [архитектурном аудите](../context/architecture-audit-2026-05.md) как HIGH (волна 1.4.0).

---

## Что сделано

### 1. Код-уровень (главное) — `validate_le_fact_preservation`

Новая функция в `pipeline_utils.py`. После Stage 3 LE и **до** Proofreader проверяет:

- Для каждого `event` в `fact_map.timeline`:
  - Извлечь 2-4 предметных маркера (`_extract_event_markers`) из source_quotes / description / title
  - Проверить что событие было в `book_before_le` (≥2 маркеров stem-substring match в content/callouts/historical_notes)
  - Если было — проверить что осталось в `book_after_le`
  - Если было до и не осталось после → `event_lost_in_le`

Stem-based matching через `_marker_stem` (первые 5 символов): «огурц» → находит огурцы/огурцов/огурцами. Это компромисс для русской морфологии без дорогой лемматизации.

Поддерживает edge cases: пустой timeline (no-op), event без id (использует title), event с <2 маркеров (insufficient_markers, пропускается), event которого не было в book_before_le (not_in_book, не наша зона ответственности — это пропуск GW), preservation в callout/historical_note (засчитывается).

Интегрировано в `scripts/test_stage3.py:559-595`. Сохраняет `karakulina_le_fact_preservation_*.json` для аудита. Аварийный обход: `--allow-le-fact-loss` (по аналогии с `--allow-deletion-drop` 1.2.2).

### 2. Промпт-уровень — LE v3 → v3.1

`prompts/05_literary_editor_v3.1.md`:
- **Новый АБСОЛЮТНЫЙ ЗАПРЕТ 0** «НЕ УДАЛЯЙ СОБЫТИЯ ИЗ TIMELINE» в самом начале промпта (приоритет 0).
- Различение «стилистический повтор» (можно убрать) vs «сюжетный эпизод» (нельзя):
  - Стилистический: повтор фразы/эпитета/оценочного слова в смежных предложениях
  - Сюжетный: конкретное событие с уникальными деталями (объект + место + год + действие), привязка к event_id
- **Обязательная процедура «PRESERVE EPISODE MARKERS»**: перед сокращением назвать 2-4 маркера, проверить что ≥2 остаются.
- Конкретный negative example v53b (огурцы Молдавия 1990 vs счётчик 1977 — РАЗНЫЕ эпизоды).
- Связь с code-уровнем: «прогон ОСТАНОВИТСЯ если удалишь эпизод — экономь токены».
- Старое правило «3. ПОВТОРЫ» обновлено с ссылкой на ЗАПРЕТ 0.

`prompts/pipeline_config.json`: literary_editor prompt_file → v3.1.

### 3. Тесты — `tests/test_le_fact_preservation.py`

**19 unit-тестов**, покрывают:
- Happy path (все события preserved)
- **v53b регрессия** (огурцы удалены LE → blocked)
- v53b — другое событие preserved параллельно
- Edge cases: пустой timeline, event не в book_before_le, insufficient markers
- Legitimate LE rephrasing (маркеры остаются — preserved)
- Preservation в callout / historical_note
- Partial marker loss (4→1) → blocked (нужно ≥2)
- fact_map с `events` вместо `timeline`
- Helpers: `_extract_event_markers`, `_event_present_in_book`, `LE_EVENT_MIN_MARKERS=2`
- No input mutation

**Все 117 тестов суммарно** PASS (98 предыдущих + 19 новых).

---

## Архитектурный принцип

**Defense in depth — три уровня (тот же паттерн что волна 1.3.3):**
1. **Промпт (LE v3.1):** обучает модель не удалять эпизоды. Первая линия, ловит большинство.
2. **Code validator:** программно блокирует прогон если событие утеряно. Гарантия корректности.
3. **`validate_revision_volume` (1.2.2):** secondary защита (если LE подаёт в FC через revision).

Этот паттерн закрывает **архитектурное слепое пятно Stage 2→3**: до волны 1.4.0 на этой transition не было post-validator. Аудит (PR #13) идентифицировал это как HIGH risk.

---

## Verified-on-run

> Заполняется ОБЯЗАТЕЛЬНО перед закрытием задачи.

**Статус:** ожидает прогона **v54** (повторный полный Каракулины TR2 с защитой 1.4.0 активной).

**Cursor — предложение наблюдения:**

[После v54: открыть `karakulina_le_fact_preservation_*.json`. Если `events_lost_in_le=0` и `events_preserved>0` — LE v3.1 промпт держит. Если `verdict=blocked_events_lost_in_le` — code validator сработал, прогон остановлен на Stage 3, нужно смотреть какие именно эпизоды LE пытался удалить.]

**Опус — независимое наблюдение:**

[Открываю `book_FINAL_stage3_v54.json`. Grep на «огурц» / «молдави» / «чемодан» в ch_02 — должны быть найдены. Сравнение `book_FINAL_stage2_v54` ↔ `book_FINAL_stage3_v54`: chars_drop, key markers preserved.]

---

## Артефакты

**Изменены/созданы:**
- `pipeline_utils.py`: `+_extract_event_markers` + `_marker_stem` + `_event_present_in_book` (refactored) + `LE_EVENT_MIN_MARKERS=2` + `validate_le_fact_preservation` (~180 строк)
- `scripts/test_stage3.py`: import + интеграция validator после LE + `--allow-le-fact-loss` arg
- `prompts/05_literary_editor_v3.1.md`: новый файл (копия v3 + АБСОЛЮТНЫЙ ЗАПРЕТ 0 + апдейт правила «3. ПОВТОРЫ»)
- `prompts/pipeline_config.json`: literary_editor prompt_file → v3.1
- `tests/test_le_fact_preservation.py`: новый, 19 тестов

**Запуск тестов:**
```bash
pytest tests/test_revision_volume.py tests/test_validate_layout_fidelity.py \
       tests/test_pdf_renderer_refs.py tests/test_quality_gates.py \
       tests/test_fact_checker_historical_context.py tests/test_merge_revision_scope.py \
       tests/test_le_fact_preservation.py -q
# 117 passed
```

---

## Что не трогать

- Существующие защиты волн 1.1-1.3.3 (validate_layout_fidelity, validate_revision_volume, FC v2.13, GW v2.16 + scope merge, evidence-check)
- Stage 1/2 fact extraction logic (источник timeline events)
- Default LE поведение «работа с формой не содержанием» — оно правильно, ЗАПРЕТ 0 только усиливает

---

## Принципиальное решение по дефолту

При создании волны 1.4.0 был дефолт от Никиты (без явного ответа Даши): **«эпизод из fact_map.timeline НИКОГДА не удаляется на Stage 3»**. Это безопасный дефолт: строго → потом ослабим если нужно.

**Если Даша скажет «допустимо при cross-chapter дублях»** — в волне 1.4.0a добавим escape hatch (mechanism как у FC `legitimate_deletion`): LE может пометить event как `legitimate_le_removal=true` с evidence в writing_notes, validator проверит evidence наличие в другой главе. Аналог волны 1.2.3.

---

## Комментарии

### 2026-05-08 — Опус (создание)

Реализовано после v53b сценария C. Промпт + код + тесты в одном PR — defense in depth применён. Дефолт «никогда не удалять» подтверждён Никитой.

**Следующий шаг:** Курсор запускает v54 (повтор v53b на TR2 с волной 1.4.0). Если v54 = сценарий A для огурцов — волна 1.4.0 verified-on-run, переходим к 1.4.1 (err_004 — historical_note duplication, если Даша утвердит).

---

## История статусов

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-08 | `new` | Опус |
| 2026-05-08 | `in-progress` | Опус |
| 2026-05-08 | `dasha-review` (реализовано, ждёт verified-on-run на v54) | Опус |
