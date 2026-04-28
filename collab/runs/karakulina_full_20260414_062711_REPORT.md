# Отчёт: полный прогон Каракулиной (Stage1 → Phase B → Stage4) — 2026-04-14

**Тег прогона:** `karakulina_full_20260414_062711`  
**Старт:** 2026-04-14 06:27 UTC (сервер `glava`)  
**Скрипт-оркестратор:** `/opt/glava/scripts/_run_full_karakulina_s1_s4.sh`  
**Архитектура:** Вариант B — Stage1 только TR1 (assemblyai), TR2 (интервью Татьяны) в Phase B после Stage3.

---

## Итоговый статус

| Этап | Статус | Примечание |
|------|--------|------------|
| Stage 1 (Cleaner + Fact Extractor v3.3) | **PASS** | fact_map сохранён |
| Stage 2 (Ghostwriter + Fact Checker) | **FAIL (не запущен)** | на сервере не было флага `--variant-b` в `test_stage2_pipeline.py` |
| Stage 3 | не дошли | — |
| Phase B | не дошли | — |
| Stage 4 (вёрстка) | не дошли | — |

**Причина остановки:** после обновления локального `_run_full_karakulina_s1_s3.sh` на использование `--variant-b` вместо `--no-strict-gates` соответствующие версии `scripts/test_stage2_pipeline.py` и `scripts/test_stage3.py` **не были задеплоены на сервер** до запуска. Ошибка:

```text
test_stage2_pipeline.py: error: unrecognized arguments: --variant-b
```

**После отчёта:** на сервер задеплоены актуальные `test_stage2_pipeline.py` и `test_stage3.py` (флаг `--variant-b` подтверждён: `/opt/glava/.venv/bin/python .../test_stage2_pipeline.py -h`).

---

## Что использовалось (конфигурация)

### Входные данные

| Источник | Путь на сервере | Роль |
|----------|-----------------|------|
| TR1 | `/opt/glava/exports/transcripts/karakulina_valentina_interview_assemblyai.txt` | ~20 KB, AssemblyAI — единственный вход Stage1 (Вариант B) |
| TR2 | `/opt/glava/exports/karakulina_meeting_transcript_20260403.txt` | ~48 KB — планировалось для Phase B после Stage3 |

### Промпты и модели (из `run_manifest` Stage1)

Файл: `karakulina_stage1_full_run_manifest_20260414_062712.json`

- **config:** `/opt/glava/prompts/pipeline_config.json`  
  `config_sha256`: `5fb1265d573d146717c9c685f1d6df662f02ced6b48e4704255071b7991f28fd`
- **git_sha (сервер):** `d6ae6a4`
- **Cleaner:** `01_cleaner_v1.md`, Haiku 4.5, `max_tokens` 32000  
- **Fact Extractor:** `02_fact_extractor_v3.3.md`, Sonnet 4, `max_tokens` 32000  
- **Ghostwriter / FC / LE / Proofreader** и др. — перечислены в `active_prompts` манифеста (полный список — в JSON на сервере).

Усечённые хэши промптов в манифесте позволяют сверить, какие именно файлы участвовали в прогоне.

### Хэш входа (манифест)

В `inputs_sha256` для `transcript1`:

```json
"transcript1": "sha256:3555b3d0cb4da1ea"
```

(В `pipeline_utils.save_run_manifest` сохраняется префикс sha256 — 16 hex-символов для сравнения прогонов.)

---

## Как проходило (хронология по логам)

1. Запущен `_run_full_karakulina_s1_s4.sh` в фоне (`nohup`), PID зафиксирован в переписке.
2. **Cleaner:** ~59 с, 11528 → 11494 символов; сохранён очищенный текст.
3. **Fact Extractor:** ~249 с, выход ~55k символов JSON; токены in≈14268, out≈20079.
4. Статистика fact_map: timeline 35, persons 17, quotes 8, traits 28, metaphors 1, gaps 7.
5. Stage1 завершён успешно; при вызове Stage2 — падение из-за неизвестного аргумента CLI.

Логи на сервере:

| Файл | Назначение |
|------|------------|
| `/opt/glava/exports/karakulina_full_20260414_062711/run.log` | полный лог Stage1 + ошибка Stage2 |
| `/opt/glava/exports/karakulina_s1_s4_nohup.out` | оболочка s1_s4 (баннер + то же до обрыва) |
| `/opt/glava/exports/karakulina_full_s1_s4_20260414_062711.log` | создавался для блока «чекпоинты + Stage4» — **пуст/минимален**, т.к. до этого этапа не дошли |

Файл `karakulina_last_run_dir.txt` **не был записан** (скрипт пишет его в конце успешного `_run_full_karakulina_s1_s3.sh`).

---

## Артефакты (что реально есть на сервере)

**Каталог прогона:** `/opt/glava/exports/karakulina_full_20260414_062711/`

| Файл | Описание |
|------|----------|
| `karakulina_combined_cleaned_20260414_062712.txt` | выход Cleaner (~11.5k симв.) |
| `karakulina_fact_map_full_20260414_062712.json` | карта фактов Stage1 |
| `karakulina_stage1_full_run_manifest_20260414_062712.json` | run_manifest: промпты, git_sha, config_sha, inputs_sha256 |
| `run.log` | лог этапа |

**Чекпоинты (авто при Stage1):**  
`/opt/glava/checkpoints/karakulina/fact_map.json` обновлялся (v11 в логе).  
Также упоминался checkpoint cleaner для проекта с кириллическим именем в логе — при необходимости сверить отдельно.

**Collab:** каталог `/opt/glava/collab/runs/karakulina_full_20260414_062711/` **не создан** скриптом (копирование в collab — в конце успешного s1_s3).

---

## Что было сделано дополнительно (инфраструктура до/во время задачи)

1. **`_run_full_karakulina_s1_s3.sh`** — переключён на `--variant-b` вместо `--no-strict-gates` для Stage2/3; в конце пишутся `karakulina_last_run_dir.txt` и `run_meta.json` в RUN_DIR.
2. **`_run_full_karakulina_s1_s4.sh`** — новый оркестратор: после текста — save/approve `fact_map` и `proofreader` (из Phase B JSON), затем `test_stage4_karakulina.py` (с фото при наличии `exports/karakulina_photos/manifest.json`).
3. **`run_regression_suite.py`** — для approve `proofreader` чтение чекпоинта с `require_approved=False`, иначе первая регрессия перед approve невозможна.
4. После сбоя задеплоены на сервер **`test_stage2_pipeline.py`** и **`test_stage3.py`** с поддержкой `--variant-b`.

---

## Как продолжить с текущего fact_map (рекомендуемое возобновление)

Рабочий каталог и fact_map:

```bash
RUN=/opt/glava/exports/karakulina_full_20260414_062711
FM=$RUN/karakulina_fact_map_full_20260414_062712.json
```

На сервере (из `/opt/glava`, venv + `.env`):

```bash
source .venv/bin/activate
set -a; source .env; set +a

# Stage 2
python scripts/test_stage2_pipeline.py \
  --fact-map "$FM" \
  --output-dir "$RUN" \
  --skip-historian \
  --variant-b

BOOK_S2=$(ls -t "$RUN"/karakulina_book_FINAL_*.json | head -1)

# Stage 3
python scripts/test_stage3.py \
  --book-draft "$BOOK_S2" \
  --fact-map "$FM" \
  --variant-b

BOOK_S3=$(ls -t exports/karakulina_book_FINAL_stage3_*.json | head -1)

# Phase B
python scripts/test_stage2_phase_b.py \
  --current-book "$BOOK_S3" \
  --new-transcript exports/karakulina_meeting_transcript_20260403.txt \
  --fact-map "$FM" \
  --output-dir "$RUN"

# Затем чекпоинты + Stage4 — по сценарию _run_full_karakulina_s1_s4.sh (ручной блок)
```

Либо **повторить целиком** `bash scripts/_run_full_karakulina_s1_s4.sh` после деплоя — получится новый `RUN_TAG` и полный след в `collab/runs/`.

---

## Рекомендации

1. **Чеклист деплоя перед длинным прогоном:** после изменения CLI у скриптов — `scp` на сервер **всех** затронутых `test_stage*.py` и быстрая проверка:  
   `/opt/glava/.venv/bin/python scripts/test_stage2_pipeline.py -h | grep variant-b`
2. **Один источник правды:** закрепить в `deploy/README.md` или `ops.sh` шаг «синхронизация scripts перед прогоном».
3. **Писать `karakulina_last_run_dir.txt` при частичном успехе** (например, после Stage1) — упростит resume при сбое на Stage2+.
4. **Согласовать `fact_checker.max_tokens` на сервере** с репозиторием (в манифесте Stage1 для FC указано 8000 — если это не намеренно, проверить `pipeline_config.json` на VPS).
5. После успешного завершения — скопировать `collab/runs/<tag>/` на машину разработчика и приложить финальный PDF + regression отчёты к задаче.

---

## Связанные документы

- Задача архитектуры пайплайна: `collab/tasks/007-pipeline-architecture-improvements.md` (done)
- Отчёты по предыдущим прогонам: `karakulina_variantB_REPORT.md`, `karakulina_full_20260413_042555_REPORT.md`

---

*Отчёт сформирован автоматически по логам сервера и состоянию репозитория на 2026-04-14.*
