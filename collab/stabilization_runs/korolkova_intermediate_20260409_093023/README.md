# Korolkova Intermediate Run Report

Папка собрана для совместного разбора с Дашей и Claude.

## Коротко

Это тестовый прогон по Корольковой, собранный по той же логике, что и недавний прогон по Каракулиной, но на данных:

- 2 интервью: `transcript_comparison_diarized.txt`, `транскрипт2.txt`
- 3 фото: `photo_2026-02-24_16-09-29.jpg`, `photo_2026-02-24_16-12-05.jpg`, `photo_2026-02-24_16-19-14.jpg`

Итог состояния:

- Stage 1: прошёл
- Stage 2: по сути прошёл, но legacy-скрипт упал на побочной выгрузке `.txt`
- Stage 3: прошёл с fallback, потому что `proofreader` вернул невалидный JSON
- Stage 4: дошёл до `QA PASS` на итерации 2, но итоговый PDF для принятой итерации не собрался

Главный вывод:

- это полезный промежуточный диагностический пакет
- это не финальный стабильный артефакт для клиента
- реальный собранный PDF есть только для `iter1`, а он по QA был `FAIL`
- принятая `iter2` версия существует как layout/QA JSON, но не как готовый PDF

## Контекст запуска

- Дата прогона: `2026-04-09`
- Git SHA: `65b7b83`
- Конфиг пайплайна: `prompts/pipeline_config.json`
- SHA конфига: `64cef56d6fbdc3135491fa7ff5eda07a62b28995f05dfbf48aa938acf632c424`
- Режим Stage 4: `legacy`
- Входы Stage 4 были поданы вручную через:
  - `korolkova_proofreader_report_20260409_092627.json`
  - `korolkova_fact_map_v2.json`
  - `exports/korolkova` как `photos_dir`
  - `korolkova_subject_profile.json`

## Какие скрипты использовались

### Stage 1

- `scripts/_run_korolkova.py`
- Вход: объединённый файл `korolkova_combined_transcript_latest.txt`

Примечание:

- это старый корольковский запускатор под Stage 1
- он читает актуальный `pipeline_config.json`, то есть промпты были последние

### Stage 2

- `scripts/test_stage2_korolkova.py`

Примечание:

- это отдельный legacy-скрипт под Королькову
- он не пишет `run_manifest`
- он не встроен в strict checkpoint flow
- он не умеет аккуратно завершаться при `None` в `chapter.content`

### Stage 3

- `scripts/test_stage3.py --prefix korolkova`

### Stage 4

- `scripts/test_stage4_karakulina.py`
- запущен как универсальный Stage 4 runner с параметрами Корольковой:
  - `--allow-legacy-input`
  - `--prefix korolkova`
  - `--proofreader-report exports/korolkova_proofreader_report_20260409_092627.json`
  - `--fact-map exports/korolkova_fact_map_v2.json`
  - `--photos-dir exports/korolkova`
  - `--subject-profile exports/korolkova/korolkova_subject_profile.json`

Примечание:

- сам runner называется `test_stage4_karakulina.py`, но фактически отработал на профиле Корольковой
- это нормально для теста, но создаёт когнитивный шум и риск путаницы

## Какие промпты и модели реально были в прогоне

По `stage3_run_manifest` и `stage4_run_manifest`:

- `01_cleaner_v1.md` → `claude-haiku-4-5-20251001`
- `02_fact_extractor_v3.3.md` → `claude-sonnet-4-20250514`
- `03_ghostwriter_v2.6.md` → `claude-sonnet-4-20250514`
- `04_fact_checker_v2.md` → `claude-sonnet-4-20250514`
- `05_literary_editor_v3.md` → `claude-sonnet-4-20250514`
- `06_proofreader_v1.md` → `claude-sonnet-4-20250514`
- `08_layout_designer_v3.14.md` → `claude-sonnet-4-20250514`
- `09_qa_layout_v1.md` → `claude-sonnet-4-20250514`
- `11_interview_architect_v4.1.md` → `claude-sonnet-4-20250514`
- `13_cover_designer_v2.6.md` → `claude-sonnet-4-20250514`
- `15_layout_art_director_v1.8.md` → `claude-sonnet-4-20250514`

## Что произошло по этапам

### Stage 1

Что сделали:

- взяли 2 интервью
- собрали их в `korolkova_combined_transcript_latest.txt`
- прогнали через `Cleaner` и `Fact Extractor`

Что получили:

- `korolkova_cleaned_transcript.txt`
- `korolkova_fact_map_v2.json`

Состояние:

- этап прошёл
- критических блокеров на Stage 1 не было

### Stage 2

Что сделали:

- прогнали `Historian`
- сделали `Ghostwriter` initial
- сделали `Ghostwriter` revision после историка
- прогнали `Fact Checker`

Что получилось:

- `Fact Checker` на итерации 1 дал `FAIL`
- после ревизии `Fact Checker` на итерации 2 дал `PASS`
- итоговый основной JSON книги сохранился: `korolkova_book_FINAL_20260409_091439.json`

Где зависли:

- после успешного `PASS` legacy-скрипт упал на записи `.txt`
- причина: в одной из глав `chapter.content == null`, а код ожидал строку

Технический сбой:

- `TypeError: unsupported operand type(s) for +: 'NoneType' and 'str'`

Вывод:

- содержательно Stage 2 можно считать завершённым
- инфраструктурно runner требует фикса

### Stage 3

Что сделали:

- подали Stage 2 final book
- использовали `liteditor` + `proofreader`

Что получилось:

- `liteditor` прошёл успешно
- `proofreader` вернул невалидный JSON
- скрипт ушёл в fallback и использовал текст после `liteditor`
- затем пропатчил пустую `ch_01` минимальным биоблоком из `fact_map`

Артефакты:

- `korolkova_liteditor_report_20260409_092627.json`
- `korolkova_proofreader_raw_20260409_092627.json`
- `korolkova_proofreader_report_20260409_092627.json`
- `korolkova_book_FINAL_stage3_20260409_092627.json`
- `korolkova_FINAL_stage3_20260409_092627.txt`
- `korolkova_stage3_text_gates_20260409_092627.json`
- `korolkova_stage3_run_manifest_20260409_092627.json`

Что важно:

- `stage3_text_gates` прошли
- но `ready_for_layout` в manifest стоит `false`
- это значит, что мы перешли в Stage 4 не из чистого proofreader success, а через fallback-маршрут

Где зависли:

- не в самом прохождении этапа
- а в том, что `proofreader` не вернул валидную JSON-структуру

Вывод:

- Stage 3 диагностически полезен
- но не является чистым эталонным текстовым финишем

### Stage 4

Что сделали:

- запустили обложку, арт-директора, верстальщика, QA и интервьюера
- подали 3 фото
- подали subject profile Корольковой

#### Cover Designer

Что произошло:

- `cover_designer` выбрал `photo_002`
- референсная генерация через `nano-banana-2` трижды упала из-за внешней перегрузки сервиса
- затем сработал fallback на `FLUX Schnell`
- портрет был сгенерирован
- второй вызов `cover_designer` портрет одобрил

Артефакты:

- `korolkova_stage4_cover_designer_call1_20260409_093023.json`
- `korolkova_stage4_cover_designer_call2_a1_20260409_093023.json`
- `korolkova_stage4_cover_portrait_20260409_093023.webp`

Вывод:

- трек обложки сработал хорошо
- внешний риск только в нестабильности Replicate reference-модели

#### Art Director

Что получилось:

- page plan на 22 страницы

Артефакт:

- `korolkova_stage4_page_plan_20260409_093023.json`

#### Layout + QA, итерация 1

Что произошло:

- `layout_designer` отдал `pages[]`
- `pdf_renderer.py` собрал PDF
- PDF `iter1` реально существует
- затем `structural_qa` и `visual_qa` дали `FAIL`

Основные проблемы iter1:

- страница 13 отмечена как `blank`, хотя по `page_plan` там должен быть текст
- отсутствовал `callout_05`
- были множественные расхождения между `page_plan` и `page_map` по callouts
- `technical_notes` расходились с фактической пагинацией

Артефакты:

- `korolkova_stage4_layout_iter1_20260409_093023.json`
- `korolkova_iter1_layout_pages_20260409_093023.json`
- `korolkova_stage4_pdf_iter1_20260409_093023.pdf`
- `korolkova_stage4_structural_guard_iter1_20260409_093023.json`
- `korolkova_stage4_pdf_preflight_iter1_20260409_093023.json`
- `korolkova_stage4_structural_qa_iter1_20260409_093023.json`
- `korolkova_stage4_visual_qa_iter1_20260409_093023.json`
- `korolkova_stage4_qa_iter1_20260409_093023.json`

Вывод:

- iter1 полезен как реально собранный PDF
- но он не принят по QA

#### Layout + QA, итерация 2

Что произошло:

- `layout_designer` исправил структурные проблемы iter1
- `structural_qa` дал `PASS`
- combined `qa` в итоге тоже дал `PASS`

Но:

- на сборке PDF `iter2` `pdf_renderer.py` упал
- причина: `bio_data_block.content` пришёл как `dict`, а рендерер ждал `str`

Точный блокер:

- `AttributeError: 'dict' object has no attribute 'split'`
- место: `_render_bio_data_block()` в `scripts/pdf_renderer.py`

Следствие:

- `pdf_preflight_iter2` = `passed: false`
- итогового PDF для принятой iter2 нет
- `visual_qa` для iter2 по сути был skipped/fallback, потому что PDF был недоступен

Артефакты:

- `korolkova_stage4_layout_iter2_20260409_093023.json`
- `korolkova_iter2_layout_pages_20260409_093023.json`
- `korolkova_stage4_structural_guard_iter2_20260409_093023.json`
- `korolkova_stage4_pdf_preflight_iter2_20260409_093023.json`
- `korolkova_stage4_structural_qa_iter2_20260409_093023.json`
- `korolkova_stage4_qa_iter2_20260409_093023.json`

Что это означает по-честному:

- у нас есть хороший `layout JSON` iter2
- у нас есть `QA PASS` по combined report
- но у нас нет финального рендеренного PDF для этой принятой итерации
- значит продуктово это ещё не "финальная собранная книга", а промежуточный accepted-layout без материального PDF

#### Interview Architect

Что получилось:

- 15 уточняющих вопросов
- 6 групп
- акцент на детство, внутренний мир и поздние годы

Артефакты:

- `korolkova_stage4_interview_questions_20260409_093023.json`
- `korolkova_stage4_ai_questions_20260409_093023.json`

## Где именно мы зависли

Главная точка зависания сейчас не в LLM, а на стыке `layout JSON -> pdf_renderer`.

Конкретно:

1. Stage 2 runner старый и падает на `None` при записи `.txt`
2. Stage 3 `proofreader` нестабилен по формату ответа и сломал чистый proofreader path
3. Stage 4 iter2 структурно исправлен, но не собран в PDF из-за несовместимости `layout_designer` и `pdf_renderer`
4. Combined QA сейчас способен вернуть `PASS`, даже если итоговый PDF iter2 физически не построен

То есть основной настоящий блокер:

- accepted layout есть
- accepted final PDF нет

## Что предлагаю делать дальше

### Вариант A. Практический, быстрый

Сделать минимальный инженерный фикс и перегнать только Stage 4.

Шаги:

1. Починить `scripts/pdf_renderer.py`, чтобы `_render_bio_data_block()` принимал и `str`, и `dict`
2. Перезапустить Stage 4 на тех же входах Корольковой
3. Добиться, чтобы для принятой итерации появился реальный PDF
4. Повторно прогнать `preflight` и `visual_qa`

Почему это лучший ближайший ход:

- Stage 1–3 уже дали достаточно полезный промежуточный материал
- главный блокер сейчас локальный и технический
- это самый короткий путь до реального финального PDF

### Вариант B. Чистый, но дольше

Привести весь корольковский маршрут к тому же стандарту, что у Каракулиной.

Шаги:

1. Сделать нормальный multi-transcript runner для Корольковой вместо `scripts/_run_korolkova.py`
2. Перевести Stage 2 Корольковой на общий pipeline runner с `run_manifest`
3. Исправить/усилить `proofreader` JSON contract
4. Только после этого повторить прогон целиком от Stage 1 до Stage 4

Когда это имеет смысл:

- если цель не просто получить один PDF
- а стабилизировать весь корольковский pipeline как повторяемый сценарий

## Что стоит проверить Даше и Claude

### По промптам

- `06_proofreader_v1.md`
  - почему модель иногда возвращает невалидный JSON
  - надо ли сильнее форсировать "JSON only"

- `08_layout_designer_v3.14.md`
  - почему `bio_data_block.content` приходит как `dict`
  - надо ли жёстче нормировать схему output
  - надо ли отдельно требовать строгую согласованность `page_plan`, `page_map`, `technical_notes`

- `09_qa_layout_v1.md`
  - стоит ли блокировать `combined PASS`, если `pdf_preflight` не пройден и финальный PDF отсутствует

### По коду

- `scripts/pdf_renderer.py`
  - сделать рендер tolerant к двум форматам `bio_data_block`

- `scripts/test_stage2_korolkova.py`
  - защитить запись `.txt` от `None`

- `scripts/test_stage4_karakulina.py`
  - не считать итерацию по-настоящему принятой, если accepted layout не собрался в реальный PDF

## Рекомендуемое следующее действие

Рекомендую идти по Варианту A:

- фикс `pdf_renderer.py`
- повторный Stage 4 на этих же артефактах
- получить реальный финальный PDF

После этого, отдельной задачей:

- стабилизировать корольковские Stage 1–2 раннеры
- убрать legacy-маршрут и привести Королькову к strict flow

## Что лежит в этой папке

### Входы

- `transcript_comparison_diarized.txt`
- `транскрипт2.txt`
- `korolkova_combined_transcript_latest.txt`
- `photo_2026-02-24_16-09-29.jpg`
- `photo_2026-02-24_16-12-05.jpg`
- `photo_2026-02-24_16-19-14.jpg`
- `korolkova_subject_profile.json`

### Stage 1

- `korolkova_cleaned_transcript.txt`
- `korolkova_fact_map_v2.json`

### Stage 2

- `korolkova_historian_20260409_091439.json`
- `korolkova_book_draft_v1_20260409_091439.json`
- `korolkova_book_draft_v2_20260409_091439.json`
- `korolkova_book_draft_v3_20260409_091439.json`
- `korolkova_fc_report_iter1_20260409_091439.json`
- `korolkova_fc_report_iter2_20260409_091439.json`
- `korolkova_book_FINAL_20260409_091439.json`
- `korolkova_book_FINAL_20260409_091439.txt`

### Stage 3

- `korolkova_liteditor_report_20260409_092627.json`
- `korolkova_book_stage3_liteditor_20260409_092627.json`
- `korolkova_proofreader_raw_20260409_092627.json`
- `korolkova_proofreader_report_20260409_092627.json`
- `korolkova_book_FINAL_stage3_20260409_092627.json`
- `korolkova_FINAL_stage3_20260409_092627.txt`
- `korolkova_stage3_text_gates_20260409_092627.json`
- `korolkova_stage3_run_manifest_20260409_092627.json`

### Stage 4

- `korolkova_stage4_cover_designer_call1_20260409_093023.json`
- `korolkova_stage4_cover_designer_call2_a1_20260409_093023.json`
- `korolkova_stage4_cover_portrait_20260409_093023.webp`
- `korolkova_stage4_page_plan_20260409_093023.json`
- `korolkova_stage4_layout_iter1_20260409_093023.json`
- `korolkova_iter1_layout_pages_20260409_093023.json`
- `korolkova_stage4_pdf_iter1_20260409_093023.pdf`
- `korolkova_stage4_structural_guard_iter1_20260409_093023.json`
- `korolkova_stage4_pdf_preflight_iter1_20260409_093023.json`
- `korolkova_stage4_structural_qa_iter1_20260409_093023.json`
- `korolkova_stage4_visual_qa_iter1_20260409_093023.json`
- `korolkova_stage4_qa_iter1_20260409_093023.json`
- `korolkova_stage4_layout_iter2_20260409_093023.json`
- `korolkova_iter2_layout_pages_20260409_093023.json`
- `korolkova_stage4_structural_guard_iter2_20260409_093023.json`
- `korolkova_stage4_pdf_preflight_iter2_20260409_093023.json`
- `korolkova_stage4_structural_qa_iter2_20260409_093023.json`
- `korolkova_stage4_qa_iter2_20260409_093023.json`
- `korolkova_stage4_interview_questions_20260409_093023.json`
- `korolkova_stage4_ai_questions_20260409_093023.json`
- `korolkova_stage4_run_manifest_20260409_093023.json`

### Полный бандл одним файлом

- `full_artifacts/korolkova_intermediate_20260409_093023_artifacts.tgz`
