# Karakulina Stage4 hardening rerun (r3)

Дата: 2026-04-09  
Префикс: `karakulina_stage4_hardening_20260409_r3`

## Входы (зафиксированные)

- `proofreader_report`: `karakulina_strict_control_20260408_185639e_proofreader_report_20260409_044411.json`
- `fact_map`: `test_fact_map_karakulina_v5.json`
- `photos_dir`: `exports/karakulina_photos`
- `cover_composition`: `karakulina_strict_control_20260409_0449_stage4_cover_designer_call2_a1_20260409_044838.json`
- `portrait`: `karakulina_strict_control_20260409_0449_stage4_cover_portrait_20260409_044838.webp`
- `page_plan`: пересобран Арт-директором в этом прогоне

## Результат

- Прогон завершён полностью (3 итерации Stage4 + Interview Architect).
- Финальный `run_manifest` сохранён:
  - `karakulina_stage4_hardening_20260409_r3_stage4_run_manifest_20260409_081836.json`
- Финальный `QA verdict`: **FAIL**.

## Ключевая динамика по итерациям

- **Iter1**
  - PDF собран.
  - Structural/Visual QA: FAIL (основной конфликт по callout-ам vs page_plan/page_map).
- **Iter2**
  - Structural QA: PASS.
  - Visual QA: PASS.
  - Combined QA: FAIL из-за `structural_layout_guard` (пагинационная модель / TOC visible numbering mismatch).
- **Iter3**
  - `structural_layout_guard`: PASS.
  - Но Structural/Visual QA снова FAIL:
    - расхождение callout-ов (`callout_03` отсутствует в `page_map` по мнению QA),
    - несоответствия между `page_plan` и `page_map` по части элементов страниц.

## Что положено в папку

- Все `layout_iter1..3`, `iter*_layout_pages`, `pdf_iter1..3`,
  `pdf_preflight_iter1..3`, `structural_guard_iter1..3`,
  `structural_qa_iter1..3`, `visual_qa_iter1..3`, `qa_iter1..3`,
  `page_plan`, `run_manifest`, `interview_questions`, `ai_questions`.
- Отдельный подробный отчёт для Даши и Claude:
  - `REPORT_FOR_DASHA_CLAUDE.md`
- Логи прогонов:
  - `logs/run_r1_terminal.txt`
  - `logs/run_r2_terminal.txt`
  - `logs/run_r3_terminal.txt`

