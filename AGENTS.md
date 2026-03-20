# GLAVA — контекст для AI-агентов

Файл задаёт контекст проекта для Cursor, Copilot, Codex и других агентов. Используй его при изменении кода, добавлении фич и отладке.

> **Правило:** при любом изменении этого файла сразу обновить `AGENTS.pdf`:
> `python scripts/export_agents_to_pdf.py` — и включить оба файла в один коммит.

---

## Обзор проекта

**GLAVA** — Telegram-бот и пайплайны для семейных историй: приём голосовых и фото, транскрипция, формирование биографического текста и уточняющих вопросов, личный кабинет, оплата (ЮKassa).

- **Бот:** `main.py` — сценарий v2 (spec Даши): двухинтервьюная модель, нарраторы, 3 круга правок, финализация, возврат. Команды: `/start`, `/versions`, `/list`, `/cabinet`. Пайплайн только после оплаты.
- **Личный кабинет:** `cabinet/app.py` (Flask) — вход по паролю, dashboard, вопросы.
- **Транскрипция:** SpeechKit (Яндекс), AssemblyAI, опционально Whisper; диаризация по спикерам — см. `docs/DIARIZATION.md`.
- **LLM:** OpenAI (ChatGPT) — биодокумент из транскрипта (`llm_bio.process_transcript_to_bio`), уточняющие вопросы (`generate_clarifying_questions`). Из РФ API часто недоступен — запуск на сервере за рубежом, см. `docs/OPENAI_ACCESS.md`.
- **Оплата:** ЮKassa; проверка `_user_has_paid` обязательна для запуска пайплайна и приёма голосовых/фото.
- **Онлайн-встречи:** команда `/online` — пользователь отправляет ссылку на встречу (Zoom, Google Meet, Teams) или получает ссылку из телемоста (`TELEMOST_MEETING_LINK`). Бот **Recall.ai** (приоритет) или MyMeet подключается по URL, записывает разговор; транскрипт (через AssemblyAI, русский язык) попадает в тот же пайплайн (bio + уточняющие вопросы). Выбор провайдера: `_online_meeting_api_key()` → recall → mymeet. Модули: `recall_client`, `pipeline_recall_bio`, `mymeet_client`, `pipeline_mymeet_bio`.

Подробнее: `README.md`, `ARCHITECTURE.md`.

---

## Правила проекта (Cursor rules / skills)

Правила лежат в **`.cursor/rules/`** (файлы `.mdc` с YAML frontmatter). При изменении кода учитывай их.

| Правило | Описание |
|--------|----------|
| **payment-required.mdc** | Пайплайн (голосовые/фото) запускается только после оплаты. Голосовые и фото принимаются только после оплаты. Не отключать проверку `_user_has_paid` в prod. Платёж — ЮKassa. |

При добавлении новых сценариев оплаты или обхода проверок — правило должно оставаться соблюдённым.

---

## Стек и окружение

- **Python:** 3.10+
- **Зависимости:** `requirements.txt`, для тестов — `pytest`, `pytest-asyncio`, `pytest-json-report` (см. `requirements-dev.txt`).
- **Конфиг:** `.env` (не коммитить), шаблон — `.env.example`. Ключи: `BOT_TOKEN`, БД (PostgreSQL), S3, `YANDEX_API_KEY`, `ASSEMBLYAI_API_KEY`, `OPENAI_API_KEY`, ЮKassa, `ADMIN_SECRET_KEY`, `ADMIN_PASSWORD_DEV`, `ADMIN_PASSWORD_DASHA`, `ADMIN_PASSWORD_LENA`, `N8N_BASIC_AUTH_USER`, `N8N_BASIC_AUTH_PASSWORD`, `N8N_WEBHOOK_PHASE_A`, `N8N_WEBHOOK_PHASE_B`, `REPLICATE_API_TOKEN`, `IMAGE_PROVIDER`.
- **Docker:** n8n запущен через `docker run` напрямую (не `docker-compose` — баг v1.29.2). Данные: `/opt/glava/n8n-data/` (владелец UID 1000). Swap 2GB включён.
- **Сервисы на VPS:** `glava` (бот), `glava-cabinet` (кабинет, порт 5000), `glava-admin` (панель, порт 5001), `glava-n8n` (Docker, порт 5678, доступен через Nginx `/n8n/`).

---

## Команды (build, test, run)

**Тесты (локально):**
```bash
pytest tests/ -v
# или с отчётом
python scripts/run_test_report.py
# v2 тесты с json-отчётом
pytest tests/test_bot_flows_v2.py -v --json-report --json-report-file=report.json
```
Тесты не требуют реальных ключей и БД (моки). Протокол и периодичность — `docs/TESTING.md`.

**Тесты через admin-панель (Даша):**
Раздел `/dasha/bot_tests` — кнопки «▶ Тесты v2» и «▶▶ Все тесты», таблица ✅/❌, history.

**Бот (локально):**
```bash
python main.py
```

**Скрипты OpenAI (лучше на сервере за рубежом):**
```bash
# Формирование биодокумента из транскрипта Assembly
python scripts/run_assembly_to_bio.py

# Уточняющие вопросы по готовому bio
python scripts/run_clarifying_questions.py
```
На сервере: виртуальное окружение `.venv` (`/opt/glava/.venv/`). Полная инструкция — `docs/OPENAI_ACCESS.md`.

**Сравнение транскриптов (диаризация):**
```bash
python scripts/run_diarized_compare.py
```
Результаты в `exports/client_<telegram_id>_<username>/`.

**Тест n8n пайплайна (с сервера или через SSH):**
```bash
# Быстрый запуск Phase A без голосового в боте
ssh root@72.56.121.94 "cd /opt/glava && python /tmp/test_pipeline.py"
```
Файл `/tmp/test_pipeline.py` — POST на webhook Phase A с тестовым транскриптом и `bot_token` из `.env`.

**Миграция БД и сид сообщений бота v2:**
```bash
cd /opt/glava && set -a && source .env && set +a && source .venv/bin/activate
python scripts/migrate_bot_v2.py          # новые поля: narrators, bot_state, revision_count, photo_type
python scripts/seed_bot_messages_v2.py    # 34 сообщения бота v2 в таблицу prompts
```

---

## Ключевые пути и модули

| Назначение | Путь |
|------------|------|
| Точка входа бота | `main.py` |
| Конфиг и .env | `config.py` |
| БД, черновики, оплата | `db.py`, `db_draft.py`, `payment_adapter.py` |
| Хранилище (S3) | `storage.py` |
| Транскрипция, диаризация | `transcribe.py`, `assemblyai_client.py` |
| LLM: биография и вопросы | `llm_bio.py`, `biographical_prompt.py`, `clarifying_questions_prompt.py` |
| Пайплайны (bio после транскрипта) | `pipeline_transcribe_bio.py`, `pipeline_assemblyai_bio.py`, `pipeline_plaud_bio.py`, `pipeline_mymeet_bio.py`, `pipeline_recall_bio.py` |
| **Триггеры n8n** | `pipeline_n8n.py` — `trigger_phase_a_background()`, `trigger_phase_b_background()` |
| **Оркестратор агентов** | `orchestrator.py` — циклы Fact Check, Literary Edit, Layout QA; Phase B revision |
| **Генератор PDF книги** | `pdf_book.py` — `generate_book_pdf(bio_text, character_name, cover_spec, cover_image_bytes)` → bytes, A5, reportlab. При `cover_image_bytes`: full-bleed AI-обложка с тёмным оверлеем, белый текст поверх. |
| **AI-обложка книги** | `replicate_client.py` — `generate_cover_image(visual_style, character_name)` → bytes. Provайдер: Replicate FLUX Schnell (`black-forest-labs/flux-schnell`). Токен: `REPLICATE_API_TOKEN`. При `GOOGLE_API_KEY` — переключить `IMAGE_PROVIDER=google_imagen` за 5 мин. |
| Клиенты онлайн-встреч | `recall_client.py` (Recall.ai, приоритет), `mymeet_client.py` (MyMeet, резерв) |
| **Лендинг glava.family** | `landing/` — `index.html`, `base.css`, `style.css`, `assets/`. Деплой: `bash deploy/deploy-landing.sh`. Nginx: `deploy/nginx-glava.conf`. |
| Telegram Mini App (кабинет) | `tma/index.html` (фронтенд), `cabinet/tma_api.py` (API Blueprint) |
| **Панель администратора** | `admin/app.py` (Flask, порт 5001), `admin/auth.py`, `admin/db_admin.py` |
| Блюпринты панели | `admin/blueprints/dev.py`, `admin/blueprints/dasha.py`, `admin/blueprints/lena.py`, `admin/blueprints/api.py` |
| **Внутренний API для n8n** | `admin/blueprints/api.py` — см. таблицу эндпоинтов ниже |
| Шаблоны панели | `admin/templates/` (Jinja2 + Tailwind CSS) |
| БД миграция (admin) | `scripts/migrate_admin.py` — таблицы `prompts`, `pipeline_jobs`, `book_versions`, `flow_suggestions` |
| **БД миграция bot v2** | `scripts/migrate_bot_v2.py` — поля `narrators`, `bot_state`, `revision_count`, `pending_revision`, `photo_type` |
| **Сид сообщений бота** | `scripts/seed_bot_messages_v2.py` — 34 сообщения всех экранов v2 → `prompts` (ключи `bot_*`) |
| n8n (AI-пайплайн) | Запуск: `docker run`, данные: `/opt/glava/n8n-data/`, доступ: `https://admin.glava.family/n8n/` |
| n8n workflow Phase A | `n8n-workflows/phase-a.json` — v12, все 14 агентов; узел **Send Bio PDF** передаёт `photo_layout` в `/api/send-book-pdf` |
| Патч промпта Ghostwriter (объём глав) | `scripts/patch_ghostwriter_prompt_volume.py` — добавляет в БД требования к длине текста (~6–9k символов суммарно); запускать на сервере после деплоя **один раз** |
| n8n workflow Phase B | `n8n-workflows/phase-b.json` — Triage B + revision + PDF v2 |
| Автотесты бота (pre-pay) | `tests/test_bot_flows.py` — TC-01…TC-27 |
| **Авто-тесты бота v2** | `tests/test_bot_flows_v2.py` — TC-28…TC-44 (нарраторы, интервью, правки, финализация) |
| Деплой, systemd | `deploy/deploy.sh`, `deploy/glava.service`, `deploy/glava-admin.service` |

### Внутренний API (`admin/blueprints/api.py`)

| Метод | Путь | Назначение |
|-------|------|-----------|
| GET | `/api/prompts/<role>` | Промпт агента из БД (без кеша) |
| POST | `/api/jobs/update` | Обновить статус джобы пайплайна |
| POST | `/api/send-book-pdf` | Генерация PDF + отправка `sendDocument` в Telegram; body: `bio_text`, `cover_spec?`, **`photo_layout?`** (подписи от Photo Editor); фото загружаются из S3 по `telegram_id` (все фото пользователя, подписи — по `photo_001`… или по порядку). Сохраняет версию в `book_versions` |
| GET | `/api/book-context/<telegram_id>` | Последняя версия книги для Phase B |
| POST | `/api/orchestrate/phase-b-revision` | Запуск Phase B revision через оркестратор |
| POST | `/api/agents/historian` | Вызов Историка через OpenAI (используется n8n-нодой) |
| POST | `/api/state/transition` | Переход состояния проекта (state machine) |
| GET | `/api/health` | Проверка живости сервиса |

### Маршруты /dasha/bot_tests

| Метод | Путь | Назначение |
|-------|------|-----------|
| GET | `/dasha/bot_tests` | Панель авто-тестов: история, кнопки запуска |
| POST | `/dasha/bot_tests/run` | Запустить pytest; body: `{only_v2: bool}`; возврат JSON |
| GET | `/dasha/bot_tests/run/<id>` | Детали конкретного запуска (JSON) |

---

## Документация (skills / гайды)

| Документ | Содержание |
|----------|------------|
| **docs/TESTING.md** | Система тестирования: тест-кейсы TC-01…TC-27 (pre-pay) + TC-28…TC-44 (v2 сценарий), протокол запуска, отчёты. |
| **docs/OPENAI_ACCESS.md** | Доступ к OpenAI из РФ, запуск на сервере, генерация bio и уточняющих вопросов. |
| **docs/DIARIZATION.md** | Разбивка интервью по спикерам: SpeechKit, AssemblyAI, Whisper. |
| **docs/USER_SCENARIOS.md** | Пользовательские сценарии и таблица тест-кейсов для бота. |
| **docs/N8N_DASHA_GUIDE.md** | Инструкция для Даши: как менять промпты, добавлять агентов, тестировать n8n. |
| **tasks/meeting-bot/** | Бот записи онлайн-созвонов (Playwright + Chromium). |
| **tasks/finance-admin/** | ✅ Выполнено (2026-03-17). Раздел «Финансы» в админке: расходы, P&L. |
| **tasks/bot-flow-admin/** | ✅ Выполнено (2026-03-17→18). Сообщения бота в админке, живая карта флоу, предложения по флоу. |
| **tasks/server-ops-access/** | ✅ Выполнено (2026-03-19). SSH без пароля, N8N API, ops.sh с 12 командами. |
| **tasks/bot-scenario-v2/** | ✅ Выполнено (2026-03-19). Бот v2 по постановке Даши: нарраторы, 2 интервью, 3 круга правок, возврат, /versions. |
| **tasks/bot-tests-panel/** | ✅ Выполнено (2026-03-19). Авто-тесты v2 (TC-28…TC-44) + панель `/dasha/bot_tests`; вывод через pytest-json-report, история в БД. |
| **ARCHITECTURE.md** | Схема сервисов, бот, кабинет, БД, S3, деплой. |
| **tasks/admin-panel/docs/ARCHITECTURE.md** | Схема admin-панели: роли, маршруты, таблицы БД, n8n интеграция. |
| **tasks/landing/status.md** | Лендинг v4.1 задеплоен (2026-03-17). |

---

## Управление задачами

Для каждой новой задачи создаётся отдельный каталог в проекте с полным набором документов.

**Структура каталога задачи:**

| Элемент | Назначение |
|--------|-------------|
| **tasks/** | Список подзадач и чек-листов |
| **jobs/** | Джобы, скрипты и команды по задаче |
| **breadcrumbs/** | Хлебные крошки, заметки, диагностика |
| **docs/** | Сопроводительные документы и ссылки |
| **status.md** | Текущий статус, версии, прогресс |
| **plan.md** | План работ |

**Правило:** любой агент, создающий новую задачу, обязан завести такой каталог и заполнить минимальный скелет `status.md` и `plan.md`.

---

## Tools, MCP и context7

**Context7 MCP** — актуальная документация по библиотекам. При работе с внешними API/библиотеками — сначала запрос через Context7, потом код.

**Локальные тулы:** `fs/git` — файлы и git; `shell/python` — скрипты из `jobs/` и `scripts/`.

---

## Автономный операционный доступ агента

> Задача: `tasks/server-ops-access/`. Реализовано: 2026-03-19.

Агент имеет прямой SSH-доступ к серверу и n8n API. При инциденте действует по схеме:

```
Ошибка/жалоба
  → 1. ssh glava "bash /opt/glava/ops.sh logs-bot"   # смотрим логи
  → 2. Локализуем поломку (бот / Flask / n8n / БД / внешний API)
  → 3. Правим код локально в Cursor
  → 4. ssh glava "bash /opt/glava/ops.sh deploy"     # git pull + restart + health
  → 5. Проверяем health и n8n-executions
  → 6. Эскалируем ТОЛЬКО если: внешний провайдер / нет доступа / риск данных
```

### SSH доступ

- **Config:** `~/.ssh/config` — алиас `glava` → `root@72.56.121.94`, ключ `~/.ssh/id_ed25519`
- **Без пароля:** ключ добавлен через Timeweb панель → SSH-ключи
- **Проверка:** `ssh glava "echo ok"`

### N8N API

- **Ключ:** `N8N_API_KEY` в `.env` (локально и на сервере)
- **База:** `N8N_BASE_URL=http://72.56.121.94:5678`
- **Проверка:** `ssh glava "bash /opt/glava/ops.sh n8n-workflows"`

### ops.sh — команды

Скрипт: `/opt/glava/ops.sh`. Источник: `tasks/server-ops-access/jobs/ops.sh`.

| Команда | Что делает |
|---------|-----------|
| `health` | Статус бота, Flask, n8n (все HTTP коды) |
| `logs-bot [N]` | Последние N строк лога бота |
| `logs-admin [N]` | Последние N строк лога Flask admin |
| `logs-n8n [N]` | Логи n8n docker |
| `status` | systemctl status обоих сервисов |
| `deploy` | git stash + git pull + restart + health |
| `restart` | Перезапуск сервисов + health |
| `n8n-workflows` | Список воркфлоу с ID и статусом |
| `n8n-executions [N]` | Последние N execution'ов |
| `n8n-execution <id>` | Детали конкретного execution'а |
| `db-check` | Кол-во промптов и версий книг в БД |
| `seed-prompts` | Обновить промпты v10+v11 в БД |

---

## Соглашения для деплоя

- **Обновление кода:** `git pull` на сервере через `ssh glava "bash /opt/glava/ops.sh deploy"`.
- **После обновления:** `systemctl restart glava` и `systemctl restart glava-admin` (делает `deploy`).
- **Сид промптов после обновления:** всегда запускать актуальные `_seed_prompts_vN.py` в `.venv`.
- **Prod-токен — только на сервере.** Локально — отдельный бот через @BotFather.
- **Виртуальное окружение:** `.venv/` на сервере (`/opt/glava/.venv/`).
- **Проверка после деплоя:**
  ```bash
  ssh glava "bash /opt/glava/ops.sh health"
  ```

### Обновление workflow в n8n

После изменения `n8n-workflows/phase-a.json` через patch-скрипт:
1. `git push` с локального компа
2. `ssh root@72.56.121.94 "cd /opt/glava && git pull"`
3. `scp root@72.56.121.94:/opt/glava/n8n-workflows/phase-a.json ~/Downloads/phase-a.json`
4. В n8n UI: три точки → Import from file → выбрать скачанный файл → Save → Publish

---

## n8n пайплайн — архитектура Phase A + Phase B

> Версия: **v12** (март 2026). Все 14 агентов из постановки Даши реализованы и протестированы end-to-end. Время выполнения Phase A: ~12–15 мин. Файлы: `n8n-workflows/phase-a.json`, `n8n-workflows/phase-b.json`.

### Роли и порядок выполнения

| # | Роль | Slug в БД | Реализация | Статус |
|---|------|-----------|-----------|--------|
| 01 | Транскрибатор | `transcriber` | Python (SpeechKit/AssemblyAI), вне n8n | ✅ |
| T | Триажер Phase A | `triage_agent` | Нода n8n (определяет вариант пайплайна) | ✅ |
| 02 | Фактолог | `fact_extractor` | Нода n8n | ✅ |
| 12 | Историк | `historian` | Flask API `/api/agents/historian` | ✅ |
| 03 | Писатель | `ghostwriter` | Нода n8n + итерации в оркестраторе | ✅ |
| 04 | Фактчекер | `fact_checker` | `orchestrator.py` (до 3 итераций) | ✅ |
| 05 | Литредактор | `literary_editor` | `orchestrator.py` (до 2 итераций) | ✅ |
| 06 | Корректор | `proofreader` | Нода n8n, вплетает `historical_backdrop` | ✅ |
| 07 | Фоторедактор | `photo_editor` | Нода n8n, параллельный трек | ✅ |
| 08 | Верстальщик | `layout_designer` | Нода n8n | ✅ |
| 09 | Контролёр вёрстки | `layout_qa` | `orchestrator.py` | ✅ |
| 10 | Продюсер | `producer` | Нода n8n, финальная сборка | ✅ |
| 11 | Интервьюер | `interview_architect` | Нода n8n, параллельная ветка | ✅ |
| 13 | Дизайнер обложки | `cover_designer` | Нода n8n, `cover_spec` для PDF | ✅ |
| TB | Триажер Phase B | `triage_b` | Нода n8n (классификация правки клиента) | ✅ |

### Граф Phase A v12

```
Webhook
  └→ Triage Agent (T)
       └→ Fact Extractor (02)
            ├→ Historian (12) [/api/agents/historian]
            │       └→ Extract Historian → historical_context
            │                                    ↓
            │                         Wrap for Ghostwriter
            │                                    ↓
            │                      Ghostwriter (03) [gpt-4o]
            │                                    ↓
            │                         Extract Book Draft
            │                                    ↓
            │           Call Orch: Fact Check (04) [orchestrator, ≤3 iter]
            │                                    ↓
            │           Call Orch: Literary Edit (05) [orchestrator, ≤2 iter]
            │                                    ↓
            │                   Proofreader (06) [historical_backdrop вплетён]
            │                                    ↓ bio_text (plain text)
            ├→ Photo Editor (07) ─────────────────────────→ photo_layout
            ├→ Interview Architect (11) ──────────────────→ questions_text
            ├→ Cover Designer (13) ───────────────────────→ cover_spec
            └→ Layout Designer (08) + Layout QA (09)
                                                     ↓
                                             Producer (10)
                                                   ↓
                                ┌─ Send Intro (велком в Telegram)
                                ├─ Send Bio PDF (pdf_book.py → sendDocument)
                                └─ Send Questions (уточняющие вопросы)
```

### Граф Phase B

```
Webhook (phase-b)
  └→ Get Book Context (/api/book-context/<telegram_id>)
       └→ Triage B (TB) → correction_type: factual/style/addition/audio/photo/structural
            └→ State: revising_phase_b
                 └→ Call Orch: Phase B (/api/orchestrate/phase-b-revision)
                      └→ Ghostwriter или Literary Editor (по типу правки)
                           └→ Proofreader
                                └→ /api/send-book-pdf → PDF v2 → Telegram
                                     └→ State: delivered_vN
```

### State Machine

| Состояние | Описание |
|-----------|---------|
| `created` | Проект создан, ожидает материал |
| `collecting` | Клиент присылает голосовые/фото |
| `assembling_phase_a` | Запущен конвейер Phase A |
| `delivered_v1` | PDF v1 + вопросы отправлены клиенту |
| `revising_phase_b` | Клиент прислал правку, запущен Phase B |
| `delivered_vN` | PDF v2+ отправлен, ожидает следующей правки |

Реализован в `admin/db_admin.py`. Переходы через `POST /api/state/transition`.

---

## Бот — сценарий v2 (spec Даши)

> Реализовано: 2026-03-19. Задача: `tasks/bot-scenario-v2/`. Спек: `glava-bot-spec.md`, схема: `glava-userflow-v2.html`.

### State Machine бота

```
no_project → draft → payment_pending → paid
→ narrators_setup → collecting_interview_1 → processing_interview_1
→ awaiting_interview_2 → collecting_interview_2 → assembling
→ book_ready → revision_N → revision_processing → book_updated → finalized
                                                 ↘ refund_requested
```

| Состояние | Описание | Экран |
|-----------|---------|-------|
| `no_project` | Новый пользователь | → 1.1 |
| `draft` | Заполняет данные (персонаж, email) | → 2.1–3.1 |
| `payment_pending` | Ожидает оплаты | → 4.2 |
| `paid` | Оплачено, настройка нарраторов | → 6.1 |
| `narrators_setup` | Добавляет рассказчиков | 6.1 |
| `collecting_interview_1` | Загружает первое интервью + фото | 8.1–8.4 |
| `processing_interview_1` | AI обрабатывает первое интервью | 8.5 |
| `awaiting_interview_2` | Показаны AI-вопросы, ждёт решения | 8.6 |
| `collecting_interview_2` | Загружает второе интервью | 9.1 |
| `assembling` | AI собирает книгу (Phase A) | 10.1 |
| `book_ready` | Книга v1 готова | 10.2 |
| `revision_1/2/3` | Пользователь пишет правку | 11.1 |
| `revision_processing` | AI вносит правки (Phase B) | 11.2 |
| `book_updated` | Обновлённая книга готова | 11.3 |
| `finalized` | Книга зафиксирована | 14.1 |
| `refund_requested` | Запрошен возврат средств | 15.2 |

### Ключевые правила

- **Нарраторы** (`narrators` JSONB в `draft_orders`) — люди, которые рассказывают историю персонажа. Отдельно от персонажа (hero).
- **Один персонаж** на заказ: `character_name` + `character_relation`.
- **Двухинтервьюная модель**: первое интервью → AI-вопросы (8.6) → опциональное второе → сборка.
- **3 круга правок**: `revision_count` ≤ 3. После 3-го кнопка «Ещё комментарий» скрыта.
- **Debounce 3 минуты**: несколько сообщений подряд собираются в `pending_revision` → отправляются одним блоком через `revision_deadline`.
- **Фото двух типов**: `photo_type = 'photo' | 'document'` — хранится в таблице `photos`.
- **bot_state** хранится в `draft_orders.bot_state` — первичный источник маршрутизации для `/start`.

### Новые функции `db_draft.py`

| Функция | Назначение |
|---------|-----------|
| `get_bot_state(telegram_id)` | Текущее состояние пользователя |
| `set_bot_state(draft_id, state)` | Установить состояние |
| `add_narrator(draft_id, name, relation)` | Добавить нарратора |
| `remove_narrator(draft_id, narrator_id)` | Удалить нарратора |
| `get_narrators(draft_id)` | Список нарраторов |
| `increment_revision_count(draft_id)` | +1 к счётчику правок |
| `set_pending_revision(draft_id, text, minutes=3)` | Сохранить правку с debounce |
| `get_pending_revision(draft_id)` | `(text, is_ready)` — готова ли к отправке |
| `clear_pending_revision(draft_id)` | Очистить после отправки |

### Управление текстами бота (для Даши)

Все тексты экранов хранятся в таблице `prompts` (ключ `bot_<screen_key>`).  
Редактирование: **admin.glava.family/dasha/bot_messages** — 56 ключей, сгруппированных по номерам экранов.
Живая карта флоу: **admin.glava.family/dasha/bot_flow** — все экраны 1.1…15.2 с текстами из БД и ссылками «↗ редактировать».

**Ограничение файлов (E.5 — `bot_file_too_large`):**
Telegram Bot API не позволяет скачивать файлы > 20 МБ. `handle_audio` и `handle_audio_document` проверяют `file_size` до загрузки. При превышении — бот отвечает сообщением `file_too_large` с советами (записать голосовое в Telegram, сжать до 64 кбит/с, разбить на части). Текст редактируется в панели Даши. Fallback: `prepay/messages.py → FILE_TOO_LARGE_MSG`.

### Команда `/versions`

Новая команда — список всех версий книги. Запрашивает `/api/book-context/<telegram_id>`, показывает inline-кнопки «📄 Открыть» и «↩️ Откатить» для каждой версии.


### Историк — особенности реализации

Нода `Historian` в n8n вызывает **Flask API** (`/api/agents/historian`), а не OpenAI напрямую. Причина: прямые OpenAI-ноды в n8n давали `invalid syntax` и `Bad request` из-за проблем с экранированием выражений `={{ }}`.

Цепочка передачи `historical_context`:
1. Historian → `{historical_context: {period_overview, key_historical_events, cultural_context, everyday_life_notes, historical_backdrop}}`
2. Extract Historian → Wrap for Ghostwriter (Ghostwriter пишет главы с историческим контекстом)
3. Wrap Orch: Fact Check и Literary Edit → получают `historical_context` в payload оркестратора
4. Wrap for Proofreader → передаёт `historical_backdrop` Корректору
5. Корректор вплетает исторические детали в финальный текст глав

### PDF генерация (`pdf_book.py`)

`generate_book_pdf(bio_text, character_name, cover_spec=None)` → bytes:
- Формат A5, шрифт DejaVuSerif (кириллица), библиотека reportlab
- Обложка: `title`/`subtitle`/`tagline` из `cover_spec` (Cover Designer) или `character_name`
- Контент: построчный рендер `bio_text`, автоопределение заголовков глав
- Колонтитул: `Глава — семейная биография · glava.family`
- Вызов из n8n: `POST /api/send-book-pdf` → bytes → Telegram `sendDocument`
- Версия сохраняется в таблицу `book_versions` (для Phase B и панели Даши)

### Маршрутизация Phase B в боте

После `delivered_v1` функция `_user_book_delivered()` в `main.py` определяет статус:
- Текст → `trigger_phase_b_background(input_type="text", content=text)`
- Голосовое → сохранить в S3 → `trigger_phase_b_background(input_type="voice", content=storage_key)`
- Фото с подписью → `trigger_phase_b_background(input_type="photo_caption", content=caption)`

### Сид промптов на сервере

```bash
cd /opt/glava && set -a && source .env && set +a && source .venv/bin/activate

# Обязательно после первого деплоя или обновления промптов:
python scripts/_seed_prompts_v7.py   # triage_agent, historian (базовые)
python scripts/_seed_prompts_v9.py   # triage_b
python scripts/_seed_prompts_v10.py  # ghostwriter (с historical_context), historian (обновлён)
python scripts/_seed_prompts_v11.py  # proofreader (вплетает historical_backdrop)
```

### Webhook и триггеры

| Пайплайн | Webhook URL | Python-функция |
|----------|-------------|----------------|
| Phase A | `https://admin.glava.family/n8n/webhook/glava/phase-a` | `pipeline_n8n.trigger_phase_a_background()` |
| Phase B | `https://admin.glava.family/n8n/webhook/glava/phase-b` | `pipeline_n8n.trigger_phase_b_background()` |

Payload Phase A: `{telegram_id, transcript, character_name, draft_id, username, bot_token}`
Payload Phase B: `{telegram_id, input_type, content, character_name, draft_id, username}`

### Как Даша управляет пайплайном

**Промпты** — через панель `https://admin.glava.family` (роль dasha). Применяются немедленно без перезапуска.

**Версии книги** — в панели `/dasha/projects`: история версий, статус агентов, прогресс по шагам.

**Добавление роли:**
1. Сохранить промпт в админке с новым slug
2. Добавить в n8n: `Wrap for X` (Code) → `Get Prompt: X` (HTTP GET `/api/prompts/<slug>`) → `X` (HTTP POST OpenAI)
3. Связать → Save → Publish

---

## Разделение работы между агентами

### Агент A — Бэкенд и пайплайн (этот чат)

| Область | Файлы |
|---------|-------|
| Telegram-бот | `main.py`, `prepay/`, `config.py` |
| Пайплайны обработки | `pipeline_*.py`, `pipeline_n8n.py`, `orchestrator.py` |
| n8n workflow | `n8n-workflows/`, `scripts/_patch_n8n_*.py` |
| Admin-панель (Flask) | `admin/` |
| Генерация PDF | `pdf_book.py` |
| БД и хранилище | `db.py`, `db_draft.py`, `storage.py` |
| Транскрипция и LLM | `transcribe.py`, `llm_bio.py`, `*_client.py` |
| Деплой и инфраструктура | `deploy/`, systemd, nginx, Docker |
| Тесты | `tests/` |

### Агент Б — Фронтенд и лендинг (отдельный чат)

| Область | Файлы |
|---------|-------|
| Лендинг сайта | `landing/` — `https://glava.family` |
| Telegram Mini App (TMA) | `tma/index.html`, `tma/` |
| Личный кабинет — UI | `cabinet/templates/` |
| Статика | `static/` |

**Правила для Агента Б:** не трогать `main.py`, `pipeline_*.py`, `admin/blueprints/`, `deploy/`. Flask-маршруты в `cabinet/app.py` — только согласовывать с Агентом А.

---

## Соглашения для кода

- Не отключать проверку оплаты (`_user_has_paid`) в production.
- Секреты только в `.env`, не хардкодить в коде.
- Логирование — через `logging`; в тестах — моки БД и внешних API.
- Новые скрипты с вызовом OpenAI — учитывать ограничение доступа из РФ.
- Patch-скрипты для n8n — хранить в `scripts/_patch_n8n_vN.py`, применять локально, коммитить результат `phase-a.json`.
