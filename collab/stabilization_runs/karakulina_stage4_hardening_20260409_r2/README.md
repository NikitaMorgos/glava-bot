# Karakulina Stage4 hardening rerun (fixed inputs)

Дата: 2026-04-09
Префикс: `karakulina_stage4_hardening_20260409_r2`

## Режим запуска

- Stage4-only на зафиксированных входах:
  - proofreader: `karakulina_strict_control_20260408_185639e_proofreader_report_20260409_044411.json`
  - fact_map: `test_fact_map_karakulina_v5.json`
  - page_plan: `karakulina_strict_control_20260409_0449_stage4_page_plan_20260409_044838.json`
  - cover/portrait: reused из `karakulina_strict_control_20260409_0449`
  - photos: `exports/karakulina_photos`

## Что удалось получить

- Iteration 1:
  - layout + pages JSON
  - PDF
  - structural_guard
  - pdf_preflight
  - structural_qa / visual_qa / combined qa
- Iteration 2:
  - layout + pages JSON
  - PDF
  - structural_guard
  - pdf_preflight

## Блокер

На шаге `structural_qa` для iteration 2 прогон остановился из-за ошибки Anthropic billing:
`Your credit balance is too low to access the Anthropic API`.

Из-за этого:
- нет `stage4_structural_qa_iter2_*`
- нет `stage4_visual_qa_iter2_*`
- нет `stage4_qa_iter2_*`
- нет run_manifest для этого прогона

## Файлы в папке

- `karakulina_stage4_hardening_20260409_r2_stage4_layout_iter1_20260409_074107.json`
- `karakulina_stage4_hardening_20260409_r2_iter1_layout_pages_20260409_074107.json`
- `karakulina_stage4_hardening_20260409_r2_stage4_pdf_iter1_20260409_074107.pdf`
- `karakulina_stage4_hardening_20260409_r2_stage4_pdf_preflight_iter1_20260409_074107.json`
- `karakulina_stage4_hardening_20260409_r2_stage4_structural_guard_iter1_20260409_074107.json`
- `karakulina_stage4_hardening_20260409_r2_stage4_structural_qa_iter1_20260409_074107.json`
- `karakulina_stage4_hardening_20260409_r2_stage4_visual_qa_iter1_20260409_074107.json`
- `karakulina_stage4_hardening_20260409_r2_stage4_qa_iter1_20260409_074107.json`
- `karakulina_stage4_hardening_20260409_r2_stage4_layout_iter2_20260409_074107.json`
- `karakulina_stage4_hardening_20260409_r2_iter2_layout_pages_20260409_074107.json`
- `karakulina_stage4_hardening_20260409_r2_stage4_pdf_iter2_20260409_074107.pdf`
- `karakulina_stage4_hardening_20260409_r2_stage4_pdf_preflight_iter2_20260409_074107.json`
- `karakulina_stage4_hardening_20260409_r2_stage4_structural_guard_iter2_20260409_074107.json`
