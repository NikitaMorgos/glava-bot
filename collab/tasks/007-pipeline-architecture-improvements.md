# 007 — Архитектурные улучшения пайплайна: Proofreader, Phase B FC, Incremental FactExtractor

Статус: dasha-review
Приоритет: высокий
Автор: Даша
Дата: 2026-04-13
Реализовано: 2026-04-13 (Cursor)

## Контекст

По результатам прогонов Каракулиной (Вариант A и Вариант B, 12-13 апреля) выявлены три архитектурных улучшения, которые требуют изменения кода.

Отчёты: `collab/runs/karakulina_full_20260413_042555_REPORT.md` и `collab/runs/karakulina_variantB_REPORT.md`.

Подтверждено: Вариант B (Stage1 только TR1, Phase B с TR2 как новым материалом) — правильная архитектура для продакшна.

## Что нужно сделать

### 1. Proofreader — разбить на итерацию по главам

**Проблема:** Корректор системно падает при объёме >15K символов (пустой JSON). Работает стабильно при ≤10K. Сейчас при падении используется fallback на текст Литредактора → книга выходит без финальной вычитки.

**Решение:** Вызывать Корректор отдельно для каждой главы. Алгоритм:

1. Первый вызов (ch_01 или ch_02) — генерирует паспорт стиля
2. Последующие вызовы (ch_03, ch_04, epilogue) — получают паспорт стиля как вход для единообразия
3. Каждый вызов получает контекст стыков: последний абзац предыдущей главы + первый абзац следующей
4. Если один вызов упал — fallback только для этой главы, остальные вычитаны

**Где менять:**
- `scripts/test_stage3_pipeline.py` или аналог — цикл по главам вместо одного вызова
- Промпт `06_proofreader_v1.md` — возможно не менять, он уже умеет работать с одной главой (Phase B режим)

### 2. Phase B FC — ограничить до 1 итерации

**Проблема:** Вторая итерация FC Phase B контрпродуктивна. В Варианте A: 8→10 ошибок (ухудшение). В Варианте B: 11→4 (улучшение, но всё ещё FAIL). Писатель при правке вносит новые ошибки.

**Решение:**
- Ограничить FC Phase B до 1 итерации
- Добавить режим `affected_chapters_only` — FC проверяет только главы, изменённые в Phase B, а не всю книгу (главы из Stage2 уже прошли FC PASS)

**Где менять:**
- `scripts/test_stage2_phase_b.py` — ограничить цикл FC
- `04_fact_checker_v2.md` — добавить флаг `check_scope: "affected_only"` в Phase B

### 3. Incremental FactExtractor перед Phase B

**Проблема:** Phase B подаёт новый транскрипт (TR2) напрямую Писателю без нормализации через Фактолог. Из-за этого: новые персоны не в fact_map, топонимы не нормализованы, метафоры не извлечены. FC находит ошибки, которые были бы предотвращены.

**Решение:** Перед Phase B Ghostwriter добавить шаг:

```
TR2 → Фактолог v3.3 (existing_facts=текущий fact_map) → обновлённый fact_map → Писатель Phase B
```

Фактолог в Phase B уже умеет мержить — поле `is_new: true` для новых фактов. Нужно только добавить этот вызов в код.

**Где менять:**
- `scripts/test_stage2_phase_b.py` — добавить вызов Фактолога перед Писателем
- Возможно `pipeline_utils.py` — если мерж fact_map нужен как утилита

**Ожидаемый результат:** FC Phase B снизится с 4 ошибок до PASS (или ~1 minor).

### 4. Strict Gates — режим Variant B

**Проблема:** Strict Gates настроены на полный объём книги (~20K+) и блокируют Stage2/Stage3 при TR1-only основе (~10K).

**Решение:** Добавить флаг `--variant-b` — при нём проверять не абсолютный объём, а относительный рост Phase B (минимум +20%).

**Где менять:**
- `pipeline_quality_gates.py`

### 5. FC false positives по топонимам

**Проблема:** FC помечает как distortion написания, которые совпадают с fact_map (Кирсанов, Капошвара). Писатель «исправляет» правильное.

**Решение:** Добавить правило в FC: если написание совпадает с `fact_map.locations[].name` или `fact_map.persons[].name` — не считать ошибкой.

**Где менять:**
- Промпт `04_fact_checker_v2.md` — Даша/Claude
- Или код `pipeline_quality_gates.py` — детерминированная проверка до LLM-FC

## Приоритеты

1. 🔴 Incremental FactExtractor (#3) — устраняет корневую причину FC-ошибок Phase B
2. 🔴 Proofreader по главам (#1) — Корректор не работает на полном объёме
3. 🟡 Phase B FC 1 итерация (#2) — быстрый фикс
4. 🟡 Strict Gates variant-b (#4) — удобство тестирования
5. 🟢 FC false positives (#5) — промптовая правка

## Чеклист проверки

- Proofreader отрабатывает на полном объёме книги (14K+ символов) без падений
- Phase B FC: PASS (или 0 major) после Incremental FactExtractor
- Strict Gates не блокируют Вариант B при флаге
- FC не помечает корректные топонимы из fact_map как distortion

## Реализация (заполняет Cursor)

Статус изменён на **dasha-review**. Все 5 пунктов реализованы и задеплоены на сервер.

### Что изменено

**1. Proofreader по главам** (`pipeline_utils.py` + `scripts/test_stage3.py`)
- Добавлена функция `run_proofreader_per_chapter` в `pipeline_utils.py`
- Первая глава генерирует `style_passport`, остальные получают его как вход
- Каждый вызов получает контекст стыков (последний абзац пред. + первый след.)
- Fallback только для упавшей главы, остальные вычитаны
- В `test_stage3.py`: автоматический выбор режима — если книга > 10 000 симв. → per_chapter

**2. Phase B FC — 1 итерация** (`scripts/test_stage2_phase_b.py`)
- `--max-fc-iterations` default: 2 → **1**
- FC теперь запускается с `phase="B"` и `affected_chapters=["ch_02","ch_03","ch_04"]`
- FC проверяет только затронутые главы (не всю книгу)

**3. Incremental FactExtractor** (`pipeline_utils.py` + `scripts/test_stage2_phase_b.py`)
- Добавлена функция `merge_fact_maps` в `pipeline_utils.py` — мерж с дедупликацией по id/name, новые элементы получают `is_new: true`
- В `run_fact_extractor` добавлен параметр `existing_facts`
- В `test_stage2_phase_b.py`: перед Phase B Ghostwriter → вызов FE на TR2 с `existing_facts=fact_map` → мерж → обновлённый fact_map идёт в Ghostwriter
- Флаг `--no-incremental-fe` для отключения (по умолчанию включён)

**4. Strict Gates — режим Variant B** (`pipeline_quality_gates.py` + скрипты)
- Добавлены функции `run_stage2_text_gates_variant_b` и `run_stage3_text_gates_variant_b` — без `gate_required_entities`
- Добавлена функция `gate_phase_b_volume_growth` — проверяет рост ≥20% после Phase B
- Флаг `--variant-b` добавлен в `test_stage2_pipeline.py`, `test_stage3.py`, `test_stage2_phase_b.py`

**5. FC false positives по топонимам** (`prompts/04_fact_checker_v2.md`)
- Добавлен блок правила: если написание в тексте ТОЧНО совпадает с `fact_map.locations[].name` или `fact_map.persons[].name` — НЕ флагать как distortion
- Пример в промпте: `fact_map → «Кирсанов», текст → «Кирсанов» → не ошибка`

### Как запустить Вариант B с новыми флагами

```bash
# Stage 1 (только TR1)
python scripts/test_stage1_karakulina_full.py --transcript1 $TR1 --output-dir $RUN_DIR

# Stage 2 (с --variant-b вместо --no-strict-gates)
python scripts/test_stage2_pipeline.py --fact-map $FACT_MAP --output-dir $RUN_DIR --skip-historian --variant-b

# Stage 3 (с --variant-b)
python scripts/test_stage3.py --book-draft $BOOK_DRAFT --variant-b

# Phase B (incremental FE включён по умолчанию, 1 итерация FC, volume check)
python scripts/test_stage2_phase_b.py --current-book $STAGE3_BOOK --new-transcript $TR2 --variant-b
```
