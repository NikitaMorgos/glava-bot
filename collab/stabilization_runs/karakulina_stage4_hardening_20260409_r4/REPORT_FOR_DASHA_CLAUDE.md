# Stage4 hardening report (r4)

Дата: 2026-04-09

## Контекст

`r4` — Stage4-only rerun Каракулиной на тех же зафиксированных входах, что и `r3`, после согласования 4 изменений контракта.

## Внедрённые изменения

1. **Callout source of truth**
   - Добавлено требование: callout-ы должны быть явно в `page_plan.elements`.
   - Усилено в runtime-инструкциях и в guard-валидации.

2. **Жёсткая таблица типов**
   - В runtime-инструкцию Layout Designer добавлена фиксированная таблица соответствий
     `page_plan.page_type -> page_map.content_type`.
   - Таблица также возвращается в отчёте `structural_layout_guard`.

3. **Deterministic callout precheck до QA**
   - Добавлен `callout_id_precheck`:
     - `expected_content.callout_ids` vs `page_plan` IDs
     - `expected_content.callout_ids` vs `page_map` IDs
     - отсутствие неожиданных callout ID в `page_map`
   - При FAIL: LLM-QA не запускается.

4. **Разделение structural/visual verdict**
   - `combined` теперь использует policy:
     - при `pdf_preflight PASS` visual-issues неблокирующие;
     - блокирующий источник — structural + deterministic guards.

## Итог r4

- Финальный verdict: **PASS** (на итерации 2).
- `callout_precheck`: PASS в iter1 и iter2.
- `structural_qa`: PASS в iter1 и iter2.
- `visual_qa`: снова шумно репортит "PDF недоступен", но теперь это не блокирует при preflight PASS.

## Артефакты

Папка: `collab/stabilization_runs/karakulina_stage4_hardening_20260409_r4/`

Ключевые файлы:
- `*_stage4_page_plan_*`
- `*_stage4_callout_precheck_iter1_*`, `*_stage4_callout_precheck_iter2_*`
- `*_stage4_structural_guard_iter1_*`, `*_stage4_structural_guard_iter2_*`
- `*_stage4_structural_qa_iter1_*`, `*_stage4_structural_qa_iter2_*`
- `*_stage4_visual_qa_iter1_*`, `*_stage4_visual_qa_iter2_*`
- `*_stage4_qa_iter1_*`, `*_stage4_qa_iter2_*`
- `*_stage4_run_manifest_*`
- `logs/run_r4_terminal.txt`

## Вывод

Согласованные 4 пункта применены и дают ожидаемое поведение: визуальный шум больше не блокирует выпуск при корректной структуре и успешном preflight, а callout-согласованность проверяется детерминированно до QA.
