# Stage4 hardening attempt report (for Dasha + Claude)

Дата: 2026-04-09  
Контекст: Karakulina, Stage4-only rerun на зафиксированных входах.

## 1) Что было целью

Подтвердить, что после Stage4 hardening:
- `page_plan` и `page_map` сходятся по контракту;
- callout-ы не теряются и не «уезжают»;
- модель пагинации/TOC единообразна;
- прогон Stage4 проходит до `QA PASS`.

## 2) Что именно делали (без изменения Stage1-3)

- Использовали те же входы текста/фактов:
  - `karakulina_strict_control_20260408_185639e_proofreader_report_20260409_044411.json`
  - `test_fact_map_karakulina_v5.json`
- Использовали те же фото:
  - `exports/karakulina_photos`
- Обложка:
  - reused cover composition + portrait из предыдущего стабильного пакета.
- Прогоны:
  - r2: `karakulina_stage4_hardening_20260409_r2` (частично, обрыв на биллинге в середине iter2 QA)
  - r3: `karakulina_stage4_hardening_20260409_r3` (полный цикл до конца 3 итераций)

## 3) Артефакты в collab

### Основной пакет (полный)
- Папка: `collab/stabilization_runs/karakulina_stage4_hardening_20260409_r3/`
- Включает:
  - `stage4_page_plan`, `stage4_layout_iter1..3`, `stage4_pdf_iter1..3`
  - `stage4_pdf_preflight_iter1..3`
  - `stage4_structural_guard_iter1..3`
  - `stage4_structural_qa_iter1..3`
  - `stage4_visual_qa_iter1..3`
  - `stage4_qa_iter1..3`
  - `stage4_run_manifest`
  - `stage4_interview_questions`, `stage4_ai_questions`

### Промежуточный пакет
- Папка: `collab/stabilization_runs/karakulina_stage4_hardening_20260409_r2/`
- Полезен как промежуточный снимок перед пополнением баланса.

### Логи запусков
- `collab/stabilization_runs/karakulina_stage4_hardening_20260409_r3/logs/run_r1_terminal.txt`
- `collab/stabilization_runs/karakulina_stage4_hardening_20260409_r3/logs/run_r2_terminal.txt`
- `collab/stabilization_runs/karakulina_stage4_hardening_20260409_r3/logs/run_r3_terminal.txt`

## 4) Хронология попытки

## r2 (пере-запуск после renderer hotfix)

- Iter1:
  - PDF собирается.
  - Structural+Visual QA: `FAIL` (в основном callout vs page_plan).
- Iter2:
  - Прогон оборвался на `anthropic.BadRequestError` (низкий баланс) при запуске structural QA.
  - После пополнения перешли к r3.

## r3 (полный прогон до конца)

- Iter1:
  - PDF собран.
  - Structural QA: `FAIL` (callout mismatch).
  - Visual QA: `FAIL` (часть замечаний повторяет structural mismatch).
- Iter2:
  - Structural QA: `PASS`.
  - Visual QA: `PASS`.
  - Combined: `FAIL` из-за `structural_layout_guard не пройден`.
- Iter3:
  - `structural_layout_guard`: `PASS`.
  - Но Structural QA: `FAIL`.
  - Visual QA: `FAIL`.
  - Combined: `FAIL` (финальный verdict).
  - Run manifest сохранён.

## 5) Что именно сломало финал (по артефактам)

Опираясь на `stage4_qa_iter3`, `stage4_structural_qa_iter3`, `stage4_visual_qa_iter3`:

1. **Callout-consistency**
   - QA утверждает, что в `page_map` отсутствует `callout_03` (найдено 5 из 6).
   - Одновременно QA фиксирует, что `page_plan` не содержит callout-элементы, а `page_map` содержит.
   - Для QA это трактуется как нарушение контракта.

2. **Семантический drift между `page_plan` и `page_map`**
   - Отмечены расхождения по ожиданию текста на части страниц (пример со стр.16).
   - Отдельно ругается на разную номенклатуру типов (`text_with_photo` vs `chapter_body`, `photo_section` vs `photo_page`).

3. **Визуальный QA-report содержит шум**
   - В `visual_qa_iter3` есть жалоба "PDF недоступен", но файл PDF фактически существует и собирается.
   - Это похоже не на ошибку рендера, а на ограничение/шум канала visual QA в конкретном вызове.

## 6) Важное наблюдение

Финальная проблема выглядит не как "PDF сломан", а как **несогласованность контрактной логики в связке**:
- `expected_content.callout_ids`
- `page_plan` (частично без явных callout-элементов)
- `page_map` (callout-ы отражены иначе)
- интерпретация этих данных у QA.

То есть конфликт в основном **структурно-семантический**, а не рендеринговый.

## 7) Предложение по следующему шагу (для совместного решения)

Не фиксить «вслепую» в коде. Сначала согласовать единый контракт на уровне спецификации:

1. **Единый источник правды по callout-ам**
   - Либо callout-ы обязаны быть явно в `page_plan.elements` (рекомендуется),
   - либо разрешить, что они живут в `expected_content + technical_notes`, и тогда QA не должен требовать их в page_plan.

2. **Нормализация типов страниц**
   - Жёстко зафиксировать таблицу соответствий `page_plan.page_type -> page_map.content_type` и использовать её одинаково в guard и QA.

3. **Проверка полноты callout-идентификаторов**
   - Перед QA добавить deterministic precheck:
     - set(expected_content.callout_ids) == set(callouts_in_page_map)
     - явный fail с одним коротким техническим отчётом, если не сходится.

4. **Разделить structural и visual verdict-гейты**
   - Чтобы шум visual QA ("PDF недоступен") не маскировал структурный результат, если preflight уже PASS.

Если решите, могу по этому согласованному решению сделать минимальный patch и запустить `r4` на тех же входах.

