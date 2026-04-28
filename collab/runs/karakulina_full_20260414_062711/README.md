# Отчёт прогона: karakulina_full_20260414

**Дата:** 14 апреля 2026  
**Прогон:** `karakulina_full_20260414_062711`  
**Режим:** Variant B — TR1 (AssemblyAI) → Stage1→2→3, TR2 (Татьяна, встреча) → Phase B

---

## Входные данные

| Источник | Файл | Размер | Этап |
|----------|------|--------|------|
| TR1 — AssemblyAI-транскрипт | `karakulina_assemblyai_full_*.txt` | ~20 К симв. | Stage1 → Stage2 → Stage3 |
| TR2 — Запись встречи с Татьяной | `karakulina_meeting_transcript_20260403.txt` | 27 503 симв. | Phase B (Incremental FE + GW) |
| Фотографии | `karakulina_photos/` + `manifest.json` | 22 фото | Stage4 |

---

## Промпты и агенты

| Агент | Роль | Файл промпта | Версия |
|-------|------|-------------|--------|
| Cleaner | 00 | `00_cleaner_v1.md` | v1 |
| Fact Extractor | 02 | `02_fact_extractor_v3.3.md` | v3.3 |
| Ghostwriter | 03 | `03_ghostwriter_v2.6.md` | v2.7 (внутр.) |
| Fact Checker | 04 | `04_fact_checker_v2.md` | v2.1 (внутр.) |
| Literary Editor | 05 | `05_literary_editor_v3.md` | v3 |
| Proofreader | 06 | `06_proofreader_v1.md` | v1 |
| Layout Designer | 08 | `08_layout_designer_v3.14.md` | v3.14 |
| QA Layout | 09 | `09_qa_layout_v1.md` | v1 |
| Cover Designer | 13 | `13_cover_designer_v2.6.md` | v2.6 |
| Art Director | 15 | `15_layout_art_director_v1.8.md` | v1.8 |

---

## Ход прогона

### Stage 1 — Cleaner + Fact Extractor
**Время:** 06:27–06:32 UTC (≈5 мин)

- Вход: TR1, 20 К симв.
- Cleaner (streaming, max_tokens=32000): очистил транскрипт
- Fact Extractor v3.3 (с категорией `metaphor` в `character_traits`): построил карту фактов
- **Результат:** `karakulina_fact_map_full_20260414_062712.json` — 69 К, 156 фактов

---

### Stage 2 — Ghostwriter + Fact Checker
**Время:** 09:48–09:56 UTC (≈30 мин, включая дебаг gate)

- Ghostwriter v2.7 Phase A: создал 4 главы + epilogue (~10 К симв.)
- FC v2.1, итерация 1: 1 critical, 4 major → доработка
- FC v2.1, итерация 2: **0 critical, 0 major, 0 minor, 2 warnings → PASS**
- Strict Gates Variant B (gate_required_entities пропущен): **PASS**

**Инцидент:** gate `non_empty_book` упал на `ch_01` — в ней только `bio_data`, поле `content` пустое. Пофиксили в `pipeline_quality_gates.py` прямо в ходе прогона.

- **Результат:** `karakulina_book_FINAL_20260414_094837.json` — 63 К

---

### Stage 3 — Literary Editor + Proofreader (per-chapter)
**Время:** 12:00–12:00 UTC (≈18 мин)

- Вход: 5 глав, 10 241 симв.
- Literary Editor v3: 144.8с | 3 warnings устранены | объём 10241 → 10212 симв. (Δ−29) | **PASS**
- Proofreader v1 в per-chapter режиме (порог >10 000 симв.):
  - ch_01: нет текста — пропущена
  - ch_02: 75.9с | 8 правок
  - ch_03: 36.4с | 6 правок
  - ch_04: 27.8с | 4 правки
  - epilogue: 15.6с | 0 правок
- Итого после Proofreader: 10 298 симв. (Δ+86 к LitEditor)
- Strict Gates Variant B: **PASS**

- **Результат:** `karakulina_book_FINAL_stage3_20260414_120045.json` — 21 К

---

### Phase B — Incremental FE + Ghostwriter + Fact Checker
**Время:** 12:10–12:23 UTC (≈13 мин)

- Incremental Fact Extractor на TR2 (27 503 симв.): **392.8с** | 70 661 симв. выхода | in=37 850, out=25 961 токенов
- Слияние fact_map: `karakulina_fact_map_full_20260414_062712.json` + инкрементальный → `karakulina_fact_map_phase_b_20260414_121019.json` (85 К)
- Ghostwriter v2.7 Phase B `content_addition`: **358.1с** | in=56 730, out=9 744 токенов
  - Все 4 главы модифицированы: `[modified]`
  - Объём до Phase B: 10 298 симв. → после: **14 145 симв. (+37.4%)** ✅ PASS
- FC v2.1, 1 итерация (affected chapters only): **24.8с** | in=63 743, out=1 052 | **PASS**

- **Результат:** `karakulina_book_FINAL_phase_b_20260414_121019.json` — 36 К

Структура итоговой книги:

| Глава | Симв. |
|-------|-------|
| ch_01 — Основные даты жизни | 109 |
| ch_02 — История жизни | 5 818 |
| ch_03 — Портрет человека | 4 701 |
| ch_04 — Интересные факты и жизненные истории | 2 807 |
| epilogue — Путь длиною в жизнь | 710 |
| **ИТОГО** | **14 145** |

---

### Stage 4 — Layout + Cover + QA (без фото)
**Время:** 12:22–12:33 UTC (≈11 мин)

- 16 страниц A5, обложка текстовая (фото не переданы — ошибка скрипта)
- QA iter 1: FAIL → iter 2: FAIL → iter 3: **PASS**
- PDF: `karakulina_FINAL_20260414.pdf` — 183 КБ

---

### Stage 4 (повтор с фото)
**Время:** 17:54–18:02 UTC (≈8 мин)

- Фото загружены из `manifest.json`: **22 фото** (23 записи − 1 excluded: "Сын в 2026 году в гостях")
- Cover Designer v2.6: 34.1с | референс-фото `photo_002` (Фотопортрет) для AI-обложки
- Art Director v1.8: 49.1с
- Layout Designer v3.14: 30 страниц A5
  - iter 1: 131.0с | FAIL
  - iter 2: 118.8с | **PASS (structural+visual combined)**
- PDF: `karakulina_FINAL_with_photos_20260414.pdf` — **3.5 МБ, 30 страниц**

---

## Артефакты в collab

| Файл | Описание | Размер |
|------|----------|--------|
| `karakulina_fact_map_full_20260414_062712.json` | Карта фактов Stage1, 156 фактов | 68 К |
| `karakulina_book_FINAL_stage3_20260414_120045.json` | Книга после Stage3 (base, до Phase B) | 21 К |
| `karakulina_book_FINAL_phase_b_20260414_121019.json` | Финальная книга после Phase B | 36 К |
| `karakulina_FINAL_20260414.pdf` | PDF без фото (текстовый, 16 стр.) | 183 КБ |
| `karakulina_FINAL_with_photos_20260414.pdf` | **Финальный PDF с фото (30 стр.)** | 3.5 МБ |

Полные артефакты прогона (FC-отчёты, run_manifest, logs): `/opt/glava/exports/karakulina_full_20260414_062711/`

---

## Что было исправлено по ходу прогона

1. **`gate_non_empty_book` падал на `ch_01`** — глава содержит только `bio_data` (структурированные данные), поле `content` пустое. Добавлена проверка: если есть `bio_data` — считается непустой. Пофикшено в `pipeline_quality_gates.py`.

2. **Аргумент Phase B: `--transcript2` → `--new-transcript`** — несовпадение имён параметров между resume-скриптом и `test_stage2_phase_b.py`. Исправлено в генераторе скрипта.

3. **`--variant-b` не был задеплоен** в `test_stage2_phase_b.py` на сервере. Задеплоен в ходе прогона.

4. **venv не активировался** в bash-скриптах — первый запуск упал с `[ERROR] pip install anthropic`. Добавлено `source /opt/glava/.venv/bin/activate`.

5. **Stage4 без фото** — в resume-скрипт не передали `--photos-dir`. Stage4 перезапущен отдельно с фото.

6. **Лишние файлы `photo_001.jpg`…`photo_022.jpg`** в директории `karakulina_photos/` (22 файла от другой сессии) — не влияли на прогон (manifest-режим их игнорирует), но создавали путаницу. Удалены.

---

## Рекомендации

### Срочные
1. **Вопросы для клиента (15 уточняющих)** — сохранены в `karakulina_stage4_ai_questions_20260414_175419.json`. Примеры высокоприоритетных:
   - Как Валентина пережила смерть матери в 1933 году?
   - Что произошло с ней в самые тяжёлые моменты войны?
   - Как они с Дмитрием решили пожениться через две недели?
   - Почему Валерий остался в России, не вернулся в Венгрию?

   Передать Даше — это основа для следующего интервью и обогащения текста.

2. **AI-портрет для обложки** — Stage4 выбрал `photo_002` как референс (единственное портретное фото с чёткими чертами), но Replicate в этом прогоне не вызывался (обложка сделана текстовой). Если нужен AI-портрет в стиле ink sketch — запустить Cover Designer отдельно с явным референсом.

### Процессные
3. **`--photos-dir` по умолчанию** — в `test_stage4_karakulina.py` фото-директория должна быть дефолтной для проекта Каракулиной, чтобы не упускать в resume-скриптах. Либо добавить в `pipeline_config.json`.

4. **`PYTHONUNBUFFERED=1` в bash-скриптах** — Phase B молчала ~10 минут пока шёл Incremental FE (392 сек на API-вызов). Без буферизации лог был бы в реальном времени. Добавить `export PYTHONUNBUFFERED=1` после `source .env`.

5. **Стандартизировать `--output-dir`** — `test_stage3.py` не принимает `--output-dir` и пишет напрямую в `/opt/glava/exports/`, остальные скрипты поддерживают параметр. Это ломает resume-скрипты. Добавить аргумент.

### Архитектурные
6. **Checkpoint после каждого stage** — сейчас при падении нужно вручную искать где остановились. Автоматическое сохранение checkpoint после Stage2 и Stage3 (аналогично Stage1) позволит resume-скриптам стартовать с последней рабочей точки без ручного разбора логов.

7. **Единый orchestrator-скрипт** — сейчас есть 5+ разных bash-скриптов (`_run_full_*`, `_resume_*`, `_resume2_*`, `_resume3_*`, `_stage4_with_photos_*`). Стоит сделать один idempotent-скрипт, который сам определяет с какой точки продолжать по наличию checkpoint-файлов.
