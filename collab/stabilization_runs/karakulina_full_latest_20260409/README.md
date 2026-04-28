# Karakulina full run (Stage1→Stage4) — 2026-04-09

Дата: 2026-04-09  
Команда: `bash scripts/_run_karakulina_full_latest.sh`

## Итог

- Полный прогон Stage1→Stage4 выполнен.
- Stage2 подтверждает целевую текстовую структуру:
  - есть `epilogue`
  - `ch_03` = «Портрет человека» (объединённый блок по логике v2.6)
- Stage4 собрал PDF (iter1..3), но финальный QA verdict: `FAIL`
  (шум/эскалация от QA-агента по «PDF недоступен» и регрессионным замечаниям).

## Ключевой пакет этого полного прогона (ts `20260409_190332`)

- Stage2 final book: `karakulina_book_FINAL_20260409_184502.json` (на сервере)
- Stage3 final report: `karakulina_full_latest_proofreader_report_20260409_185837.json`
- Stage4 run manifest: `karakulina_full_latest_stage4_run_manifest_20260409_190332.json`
- Stage4 final PDF: `karakulina_full_latest_stage4_pdf_iter3_20260409_190332.pdf`
- Stage4 final QA: `karakulina_full_latest_stage4_qa_iter3_20260409_190332.json`
- Лог полного прогона: `logs/run_full_stage1_stage4_terminal.txt`

## Обложка: требование «род. 1920»

В исходном полном прогоне обложка вышла как `1920 — 2005`.
Причина: в `test_stage4_karakulina.py` был хардкод `death_year=2005`.

После этого сделан фикс и отдельный Stage4 rerun:
- папка: `coverfix_stage4/`
- ключевой файл: `coverfix_stage4/karakulina_full_latest_coverfix_20260409_stage4_cover_designer_call2_a1_20260409_192706.json`
- в нём `years_line.text = "род. 1920"` (требование выполнено).

## Примечание по артефактам

Wildcard-копирование из `exports` подтянуло также предыдущие файлы `karakulina_full_latest_*` от более ранних запусков.
Для текущего запуска ориентироваться по timestamp:
- полный прогон: `20260409_190332`
- coverfix Stage4: `20260409_192706`
