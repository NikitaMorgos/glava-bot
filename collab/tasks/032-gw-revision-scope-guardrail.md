# Задача: Волна 1.3.3 — GW revision scope guardrail (промпт + code merge)

**Статус:** `dasha-review` (реализовано, ждёт verified-on-run на v53)
**Номер:** 032
**Автор:** Опус
**Дата создания:** 2026-05-08
**Тип:** `промпт` + `cco-скрипт` (defense in depth)
**Связано:** task 031 (v52 прогон), волна 1.2.2 (GW v2.15 anti-deletion), волны 1.3 / 1.3.1 / 1.3.2 (FC defenses регрессии #3)

---

## Контекст

v52 показал новый класс мутации: **GW out-of-scope modification при revision**.

Конкретный кейс: FC v2.13 нашёл 8 ошибок в ch_01/ch_02 (`legitimate_deletion=False` — требуется fact_correction). GW v2.15 при revision вернул книгу с пустыми ch_03/ch_04/epilogue (52.8% drop, 15911→7510 chars). `validate_revision_volume` (волна 1.2.2) поймал на `blocked_unauthorized_deletion`, прогон остановился с откатом всей revision-итерации.

**Корень:**
- Код корректно передавал `revision_scope.affected_chapters = ["ch_01", "ch_02"]` (`test_stage2_pipeline.py:256`)
- GW v2.15 промпт корректно содержал SCOPE LOCK правило (стр. 1383): «Работай ТОЛЬКО с главами, указанными в revision_scope.affected_chapters»
- **Модель проигнорировала промпт-правило** — типичный паттерн при размытии правил в длинном промпте

Это **другой класс**, не регрессия #3 (та была про FC false positives). Существующая защита `validate_revision_volume` была спроектирована достаточно общо чтобы поймать новый класс — но мутацию ловит только постфактум, после того как GW уже потратил токены на удаление.

---

## Что сделано

### 1. Код-уровень (главное) — `pipeline_utils.merge_revision_out_of_scope_chapters`

Новая функция в `pipeline_utils.py`. После GW revision и **до** `validate_revision_volume` — детерминированный merge:

- Главы из `affected_chapters`: берутся из `book_after` (результат GW)
- Главы вне scope: восстанавливаются byte-identical из `book_before` snapshot
- callouts/historical_notes с `chapter_id` вне scope: восстанавливаются из snapshot
- callouts/historical_notes без chapter_id (глобальные): pass-through из after
- Top-level fields (title, bio_data): pass-through из after
- Edge cases: empty/None affected_chapters → no-op (no_scope_provided), in-scope глава пропала в after → восстанавливается, новая out-of-scope глава в after → отбрасывается

Интегрировано в `scripts/test_stage2_pipeline.py:285-313` — между GW revision и validate_revision_volume.

### 2. Промпт-уровень — GW v2.15 → v2.16

`prompts/03_ghostwriter_v2.16.md`:
- Новый АБСОЛЮТНЫЙ ЗАПРЕТ 0 «REVISION SCOPE LOCK» в самом начале промпта (перед запретами 1-N), приоритет 0
- Конкретный negative example v52: cur_book → out_book диаграмма что было неправильно и что правильно
- Связь с code-level enforcement: «Любые out-of-scope правки будут отброшены кодом — не трать токены»
- Новая семантика для writing_notes: `scope_violation_needed: <описание>` — если GW считает что нужна правка вне scope, не делает её сам, а флагает для куратора

`prompts/pipeline_config.json` обновлён на v2.16.

### 3. Тесты — `tests/test_merge_revision_scope.py`

**19 unit-тестов**, покрывают:
- Happy path (in-scope from after, out-of-scope from before)
- **v52 регрессия** (FC errors в ch_01/ch_02, GW обнулил ch_03/ch_04/epilogue → восстанавливаются)
- Edge cases: empty/None affected_chapters, in-scope chapter missing in after, новая глава in/out of scope, порядок глав сохраняется
- callouts/historical_notes: out-of-scope восстанавливаются, in-scope pass-through, глобальные без chapter_id pass-through
- Top-level fields preserved, details/diagnostics корректны, no input mutation

**Все 98 тестов суммарно** (79 предыдущих + 19 новых) — PASS.

---

## Архитектурный принцип

**Defense in depth — три уровня:**
1. **Промпт (GW v2.16):** обучает модель не нарушать scope. Первая линия обороны, ловит большинство.
2. **Code merge:** программно восстанавливает out-of-scope. Гарантия корректности, ловит остаток.
3. **`validate_revision_volume`:** secondary защита (если merge сам сломается, или есть in-scope deletion). Остаётся как fallback.

Этот же паттерн «промпт + код + тест» применили к регрессии #3 в волнах 1.3.x. Подтвердил работу в v51 (сценарий A).

---

## Verified-on-run

> Заполняется ОБЯЗАТЕЛЬНО перед закрытием задачи (Cursor + Опус независимо).

**Статус:** ожидает прогона v53 (повторный полный Каракулины с защитой 1.3.3 активной).

**Cursor — предложение наблюдения:**

[После v53 прогона: открыть scope_merge JSON-логи каждой revision-итерации. Если есть `chapters_restored != []` — GW всё ещё пытается out-of-scope, защита держит. Если пусто — GW v2.16 промпт-правило сработало с первой попытки.]

**Опус — независимое наблюдение:**

[Открываю book_FINAL_stage3_v53.json. Проверяю что 5 глав на месте, ch_03/ch_04/epilogue не пустые. Проверяю scope_merge_iter*.json — какие именно главы восстанавливал merge.]

---

## Артефакты

**Изменены/созданы:**
- `pipeline_utils.py`: `+merge_revision_out_of_scope_chapters` (~150 строк) + `_restore_chapter_scoped_items` helper
- `scripts/test_stage2_pipeline.py`: import + интеграция merge между GW revision и validate_revision_volume
- `prompts/03_ghostwriter_v2.16.md`: новый файл (копия v2.15 + АБСОЛЮТНЫЙ ЗАПРЕТ 0 + апдейт SCOPE LOCK секции)
- `prompts/pipeline_config.json`: ghostwriter prompt_file → v2.16
- `tests/test_merge_revision_scope.py`: новый, 19 тестов

**Запуск тестов:**
```bash
pytest tests/test_revision_volume.py tests/test_validate_layout_fidelity.py \
       tests/test_pdf_renderer_refs.py tests/test_quality_gates.py \
       tests/test_fact_checker_historical_context.py tests/test_merge_revision_scope.py -q
# 98 passed
```

---

## Что не трогать

- Существующие защиты волн 1.1-1.3.2 (validate_layout_fidelity, validate_revision_volume, FC v2.13 обработка historical_context, evidence-check)
- Логика формирования `revision_scope.affected_chapters` в `test_stage2_pipeline.py:256` (она правильная — собирает unique chapter_ids из FC errors)

---

## Комментарии

### 2026-05-08 — Опус (закрытие)

Реализовано после диагностики ответа Курсора по v52 (B+D гибрид: защита сработала, но новый класс мутации). Промпт + код + тесты в одном PR — defense in depth применён.

**Следующий шаг:** task 031 (v52 прогон) повторяется как v53 на новом коде. Если v53 = сценарий A — волна 1.3.3 verified-on-run. Если защита снова сработала на чём-то новом — следующая итерация.

---

## История статусов

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-05-08 | `new` | Опус |
| 2026-05-08 | `in-progress` | Опус |
| 2026-05-08 | `dasha-review` (реализовано, ждёт verified-on-run на v53) | Опус |
