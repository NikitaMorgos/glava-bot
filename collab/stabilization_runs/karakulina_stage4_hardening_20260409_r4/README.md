# Karakulina Stage4 hardening rerun (r4)

Дата: 2026-04-09  
Префикс: `karakulina_stage4_hardening_20260409_r4`

## Входы (те же, что в r3)

- `proofreader_report`: `karakulina_strict_control_20260408_185639e_proofreader_report_20260409_044411.json`
- `fact_map`: `test_fact_map_karakulina_v5.json`
- `photos_dir`: `exports/karakulina_photos`
- `cover_composition`: `karakulina_strict_control_20260409_0449_stage4_cover_designer_call2_a1_20260409_044838.json`
- `portrait`: `karakulina_strict_control_20260409_0449_stage4_cover_portrait_20260409_044838.webp`

## Что изменено перед r4

Реализованы согласованные 4 пункта:

1. Callout-ы обязаны быть явно в `page_plan.elements` (source of truth).
2. Жёсткая таблица соответствий `page_plan.page_type -> page_map.content_type`.
3. Детерминированный precheck callout IDs до запуска LLM-QA.
4. Разделение verdict: visual не блокирует при `pdf_preflight` PASS.

## Результат

- Прогон завершён полностью.
- Финальный `QA verdict`: **PASS** (итерация 2).
- Финальный `run_manifest`:
  - `karakulina_stage4_hardening_20260409_r4_stage4_run_manifest_20260409_173533.json`

## Динамика итераций

- **Iter1**
  - `callout_precheck`: PASS
  - `structural_qa`: PASS
  - `visual_qa`: FAIL (ложный шум "PDF недоступен")
  - `combined`: FAIL из-за `structural_layout_guard` (блокирующий guard)
- **Iter2**
  - `callout_precheck`: PASS
  - `structural_qa`: PASS
  - `visual_qa`: FAIL (тот же шум)
  - `combined`: PASS (visual non-blocking policy применена)

## Что лежит в папке

- `stage4_page_plan`, `stage4_layout_iter1..2`, `iter*_layout_pages`
- `stage4_pdf_iter1..2`
- `stage4_pdf_preflight_iter1..2`
- `stage4_callout_precheck_iter1..2`
- `stage4_structural_guard_iter1..2`
- `stage4_structural_qa_iter1..2`
- `stage4_visual_qa_iter1..2`
- `stage4_qa_iter1..2`
- `stage4_interview_questions`, `stage4_ai_questions`
- `stage4_run_manifest`
- `logs/run_r4_terminal.txt`
