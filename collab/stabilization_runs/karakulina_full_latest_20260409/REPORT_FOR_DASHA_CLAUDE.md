# Full run report (Karakulina, 2026-04-09)

## Что сделано

1. Запущен полный цикл `Stage1 → Stage4` на актуальных промптах.
2. Подтверждена текстовая цель:
   - `epilogue` присутствует в финальном тексте.
   - `ch_03` используется как «Портрет человека» (вместо старого split-паттерна).
3. Дополнительно после полного прогона исправлен источник годов для обложки
   (убран хардкод `death_year=2005`, годы синхронизируются из fact_map).
4. Выполнен Stage4 rerun (`coverfix`) на тех же checkpoint-входах.

## Статус

- **Full run (ts `20260409_190332`)**:
  - Stage1 PASS
  - Stage2 PASS
  - Stage3 PASS (с fallback после невалидного JSON от proofreader)
  - Stage4: PDF собран, но финальный QA verdict = `FAIL`
- **Coverfix rerun (ts `20260409_192706`)**:
  - обложка в `final_cover_composition` содержит `years_line: "род. 1920"`
  - Stage4 QA всё ещё уходит в FAIL/эскалацию из-за текущего поведения QA-агента.

## Доказательства по ключевым требованиям

- `epilogue`:
  - `karakulina_full_latest_book_FINAL_stage3_20260409_185837.json` -> chapter id `epilogue`.
- объединённая логика `ch_03`:
  - тот же файл -> `ch_03` с заголовком «Портрет человека».
- «род. 1920» на обложке:
  - `coverfix_stage4/karakulina_full_latest_coverfix_20260409_stage4_cover_designer_call2_a1_20260409_192706.json`
  - `final_cover_composition.typography.years_line.text = "род. 1920"`.

## Где смотреть

- Индекс: `README.md`
- Лог full run: `logs/run_full_stage1_stage4_terminal.txt`
- Лог coverfix rerun: `coverfix_stage4/run_coverfix_stage4_terminal.txt`
