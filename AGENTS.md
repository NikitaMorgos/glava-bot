# GLAVA — контекст для AI-агентов

Файл задаёт контекст проекта для Cursor, Copilot, Codex и других агентов. Используй его при изменении кода, добавлении фич и отладке.

> **Правило:** при любом изменении этого файла сразу обновить `AGENTS.pdf`:
> `python scripts/export_agents_to_pdf.py` — и включить оба файла в один коммит.

---

## Обзор проекта

**GLAVA** — Telegram-бот и пайплайны для семейных историй: приём голосовых и фото, транскрипция, формирование биографического текста и уточняющих вопросов, личный кабинет, оплата (ЮKassa).

- **Бот:** `main.py` — голосовые/фото, команды `/start`, `/list`, `/cabinet`; пайплайн только после оплаты.
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
- **Зависимости:** `requirements.txt`, для тестов — `pytest`, `pytest-asyncio` (см. `requirements-dev.txt`).
- **Конфиг:** `.env` (не коммитить), шаблон — `.env.example`. Ключи: `BOT_TOKEN`, БД (PostgreSQL), S3, `YANDEX_API_KEY`, `ASSEMBLYAI_API_KEY`, `OPENAI_API_KEY`, ЮKassa, `ADMIN_SECRET_KEY`, `ADMIN_PASSWORD_DEV`, `ADMIN_PASSWORD_DASHA`, `ADMIN_PASSWORD_LENA`, `N8N_BASIC_AUTH_USER`, `N8N_BASIC_AUTH_PASSWORD`, `N8N_WEBHOOK_PHASE_A`, `N8N_WEBHOOK_PHASE_B`.
- **Docker:** n8n запущен через `docker run` напрямую (не `docker-compose` — баг v1.29.2). Данные: `/opt/glava/n8n-data/` (владелец UID 1000). Swap 2GB включён.
- **Сервисы на VPS:** `glava` (бот), `glava-cabinet` (кабинет, порт 5000), `glava-admin` (панель, порт 5001), `glava-n8n` (Docker, порт 5678, доступен через Nginx `/n8n/`).

---

## Команды (build, test, run)

**Тесты (локально):**
```bash
pytest tests/ -v
# или с отчётом
python scripts/run_test_report.py
```
Тесты не требуют реальных ключей и БД (моки). Протокол и периодичность — `docs/TESTING.md`.

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
На сервере: виртуальное окружение `venv` (`/opt/glava/venv/`), `pip install openai`. Полная инструкция — `docs/OPENAI_ACCESS.md`.

**Сравнение транскриптов (диаризация):**
```bash
python scripts/run_diarized_compare.py
```
Результаты в `exports/client_<telegram_id>_<username>/`.

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
| Клиенты онлайн-встреч | `recall_client.py` (Recall.ai, приоритет), `mymeet_client.py` (MyMeet, резерв) |
| **Лендинг glava.family** | `landing/index.html` (HTML/CSS/JS, единый файл), `deploy/nginx-glava.conf` (создать) |
| Telegram Mini App (кабинет) | `tma/index.html` (фронтенд), `cabinet/tma_api.py` (API Blueprint), `deploy/nginx-tma.conf` |
| **Панель администратора** | `admin/app.py` (Flask, порт 5001), `admin/auth.py`, `admin/db_admin.py` |
| Блюпринты панели | `admin/blueprints/dev.py` (разработчик), `admin/blueprints/dasha.py` (продакт), `admin/blueprints/lena.py` (маркетолог), `admin/blueprints/api.py` (внутренний API для n8n) |
| Шаблоны панели | `admin/templates/` (Jinja2 + Tailwind CSS) |
| БД миграция (admin) | `scripts/migrate_admin.py` — таблицы `prompts`, `pipeline_jobs`, `mailings`, `mailing_recipients`, `mailing_triggers` |
| n8n (AI-пайплайн) | Запуск: `docker run` (см. команду в `tasks/admin-panel/status.md`), данные: `/opt/glava/n8n-data/`, доступ: `https://admin.glava.family/n8n/` |
| n8n workflow Phase A | `n8n-workflows/phase-a.json` — workflow v4, протестирован end-to-end. Архитектура: Webhook → Fact Extractor → Ghostwriter → [Fact Checker → Literary Editor → Proofreader] + [Interview Architect параллельно] → Merge → Producer → 3 сообщения в Telegram. Время выполнения ~1.5–2 мин. |
| n8n триггер из Python | `pipeline_n8n.py` — `trigger_phase_a_background()` вызывается из `pipeline_transcribe_bio.py` после транскрипции |
| Внутренний API для n8n | `GET /api/prompts/<role>` — промпт из БД без кеша (читается при каждом запуске пайплайна, Даша может менять промпты в реальном времени); `POST /api/jobs/update` — статус джобы |
| Деплой admin-панели | `deploy/glava-admin.service` (systemd), `deploy/nginx-admin.conf` (включает `/n8n/` proxy) |
| Автотесты бота | `tests/test_bot_flows.py` |
| Деплой, systemd | `deploy/deploy.sh` (основной скрипт), `deploy/glava.service`, `DEPLOY_24_7.md`, `DEPLOY_TIMEWEB.md`, `deploy/DEPLOY_GLAVA_FAMILY.md` |

---

## Документация (skills / гайды)

| Документ | Содержание |
|----------|------------|
| **docs/TESTING.md** | Система тестирования: тест-кейсы TC-01…TC-27, протокол запуска, отчёты, реагирование на падениях. |
| **docs/OPENAI_ACCESS.md** | Доступ к OpenAI из РФ, запуск на сервере, копирование файлов, генерация bio и уточняющих вопросов. |
| **docs/DIARIZATION.md** | Разбивка интервью по спикерам: SpeechKit, AssemblyAI, Whisper; рекомендации по длинным файлам. |
| **docs/USER_SCENARIOS.md** | Пользовательские сценарии и таблица тест-кейсов для бота. |
| **ARCHITECTURE.md** | Схема сервисов, бот, кабинет, БД, S3, деплой. |
| **tasks/admin-panel/docs/ARCHITECTURE.md** | Схема admin-панели: роли, маршруты, таблицы БД, n8n интеграция. |
| **tasks/admin-panel/plan.md** | Детальный план задачи Admin Panel + n8n. |
| **tasks/landing/plan.md** | План задачи лендинга glava.family: фазы, блоки, дизайн-система, Nginx-конфиг. |
| **tasks/landing/status.md** | Текущий статус лендинга: v3.0 MVP готов, ожидаем ассеты и деплой. |
| **tasks/landing/docs/DESIGN_BRIEF.md** | Дизайн-бриф: палитра, шрифты, описание всех блоков, что нужно от клиента. |

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

Полный набор каталогов и файлов формируется сразу при создании задачи, чтобы сохранять контекст при переключении между задачами в рамках проекта.

**Правило:** любой агент, создающий новую задачу, обязан завести такой каталог и заполнить минимальный скелет `status.md` и `plan.md`.

---

## Tools, MCP и context7

В проекте используются внешние инструменты и MCP-серверы. Обязательные:

**Context7 MCP**

- **Назначение:** актуальная документация по библиотекам, фреймворкам, SDK и внешним сервисам.
- **Правило:** при работе с внешними библиотеками, API и инфраструктурой агент сначала должен запросить справку через Context7, а уже потом писать или править код.
- В настройках MCP/Tools редактора (Cursor и др.) Context7 должен быть включён всегда.

**Локальные тулы**

- **fs/git** — чтение и запись файлов, работа с git.
- **shell/python** — запуск скриптов из каталогов `jobs/` и `scripts/`.

Все агенты работают в рамках context7: проектный контекст задаётся AGENTS.md, ARCHITECTURE.md, one-pager'ами и активной задачей (`status.md` / `plan.md`).

---

## Соглашения для деплоя

Правила защищают от ситуации «деплой прошёл, а пользователь видит старый текст».

- **Для обновления кода используй `rsync` или `git pull`, никогда не `scp -r DIR`.**  
  `scp -r GLAVA root@host:/opt/glava` при существующем `/opt/glava` создаёт
  `/opt/glava/GLAVA/main.py` — systemd читает `/opt/glava/main.py` и бот запускается со
  старым кодом.

  Правильно для обновления:
  ```bash
  # вариант A — git на сервере
  cd /opt/glava && git pull

  # вариант B — rsync с локального ПК
  rsync -avz --exclude=venv --exclude=__pycache__ --exclude=.git \
    ./GLAVA/ root@SERVER:/opt/glava/
  ```

- **После любого обновления кода — обязательно `systemctl restart glava`.**  
  Python не перечитывает модули автоматически; бот в памяти работает со снимком кода
  на момент последнего старта.

- **`deploy/deploy.sh` — эталонный скрипт для установки и обновления.**  
  Использует `systemctl restart` (не `start`). Всегда копирует `glava.service` из репо,
  чтобы на сервере не было самодельного юнита с неправильными путями.

- **Никогда не запускать `python main.py` локально с prod-токеном.**  
  Бот использует long polling. Если одновременно работают два экземпляра с одним токеном —  
  возникает `telegram.error.Conflict`, оба бота перестают отвечать на сообщения.  
  Для локальной разработки и тестирования — создай отдельного бота через @BotFather  
  и пропиши его токен в локальном `.env`. Prod-токен — только на сервере.

- **Виртуальное окружение:** `venv/` (не `.venv/`). Путь на сервере: `/opt/glava/venv/`.  
  В systemd: `ExecStart=/opt/glava/venv/bin/python main.py`.

- **Проверка после деплоя:**
  ```bash
  systemctl status glava            # active (running), время старта — свежее
  journalctl -u glava -n 20         # нет ошибок импорта
  ```

---

## n8n пайплайн — архитектура Phase A

### Роли и порядок выполнения

Пайплайн соответствует постановке Даши (продакт-менеджер). Все 12 ролей:

| # | Роль | Slug в БД | В Phase A workflow | Статус |
|---|------|-----------|-------------------|--------|
| 01 | Транскрибатор | `transcriber` | Python (SpeechKit/AssemblyAI) до n8n | ✅ вне n8n |
| 02 | Фактолог | `fact_extractor` | Нода n8n | ✅ |
| 03 | Писатель | `ghostwriter` | Нода n8n | ✅ |
| 04 | Фактчекер | `fact_checker` | Нода n8n (1 проход, без итераций) | ✅ |
| 05 | Литредактор | `literary_editor` | Нода n8n (1 проход, без итераций) | ✅ |
| 06 | Корректор | `proofreader` | Нода n8n | ✅ |
| 07 | Фоторедактор | `photo_editor` | Не реализован (Phase B, отдельный трек) | 🔲 |
| 08 | Верстальщик | `layout_designer` | Не реализован (PDF-трек) | 🔲 |
| 09 | Контролёр вёрстки | `layout_qa` | Не реализован (PDF-трек) | 🔲 |
| 10 | Продюсер | `producer` | Нода n8n, финальный оркестратор | ✅ |
| 11 | Интервьюер | `interview_architect` | Нода n8n, параллельная ветка | ✅ |
| Т | Триажер | `triage_agent` | Phase B (не реализован) | 🔲 |

### Граф Phase A (реализован)

```
Webhook
  └→ Fact Extractor (02)
       └→ Ghostwriter (03)
            ├→ Fact Checker (04) → Literary Editor (05) → Proofreader (06) → Extract Bio
            └→ Interview Architect (11) ──────────────────────────────────→ Extract Questions
                                                                                    ↓
                                                                          Merge (ждёт оба)
                                                                                    ↓
                                                                       Producer (10)
                                                                                    ↓
                                                         ┌─ Send Intro (тёплое вступление)
                                                         ├─ Send Bio (текст книги)
                                                         └─ Send Questions (уточняющие вопросы)
```

### Формат данных между агентами (JSON-first)

Каждый агент получает строго структурированный JSON и возвращает JSON:
- **Fact Extractor** → выдаёт `fact_map` (persons, timeline, gaps, conflicts, locations…)
- **Ghostwriter** → получает `fact_map` + `transcripts`; выдаёт `book_draft` (chapters, callouts)
- **Fact Checker** → получает `book_draft` + `fact_map` + `transcripts`; выдаёт `verdict` + `warnings`
- **Literary Editor** → получает `book_draft` + `fact_checker_warnings`; выдаёт отредактированные `chapters`
- **Proofreader** → получает `book_text` (chapters); выдаёт исправленные `chapters`
- **Interview Architect** → получает `gaps/timeline/persons` из fact_map + `book_chapters_summary`; выдаёт `questions` + `question_groups`
- **Producer** → получает анонс о готовности + excerpt; выдаёт plain text для Telegram

Между агентами стоят **Code-ноды** (`Wrap for X`, `Extract from X`) — они парсят JSON из LLM-ответа и упаковывают вход для следующего агента.

### Как Даша управляет пайплайном

**Промпты агентов (без перезапуска):**
- Даша меняет текст в своей админке (`https://admin.glava.family`, роль dasha)
- n8n при каждом запуске делает `GET http://127.0.0.1:5001/api/prompts/<slug>` — читает актуальный промпт из PostgreSQL
- Изменение вступает в силу **немедленно** для следующего запуска

**Логика флоу (через n8n editor):**
- Даша заходит в `https://admin.glava.family/n8n/`
- Добавляет/удаляет ноды, меняет связи
- Нажимает **Publish** — изменения применяются для всех последующих запросов

**Добавление новой роли:**
1. Даша сохраняет промпт в админке с новым slug (например, `style_checker`)
2. Разработчик добавляет 3 ноды в n8n: `Wrap for X` (Code) → `Get Prompt: X` (HTTP GET) → `X` (HTTP POST OpenAI)
3. Связывает в нужное место флоу → Publish

### Webhook и триггер

- **URL (prod):** `https://admin.glava.family/n8n/webhook/glava/phase-a`
- **Метод:** POST
- **Payload:** `{telegram_id, transcript, character_name, draft_id, username, bot_token}`
- **Триггер из Python:** `pipeline_n8n.trigger_phase_a_background()` в фоновом потоке после транскрипции
- **Ответ n8n:** `{"message": "Workflow was started"}` — пайплайн работает асинхронно

### Phase B (не реализован — следующая задача)

Phase B включает Триажера (Triage Agent) и 6 маршрутов обработки правок клиента:
- ① Фактическая поправка: Писатель → Корректор → Верстальщик → QA
- ② Стилевой комментарий: Литредактор → Корректор → Верстальщик → QA
- ③ Дополнение текстом: Фактолог → Писатель → Фактчекер → Литредактор → Корректор → Верстальщик → QA
- ④ Новое интервью/аудио: Транскрибатор → полный цикл
- ⑤ Новые фотографии: Фоторедактор → Верстальщик → QA
- ⑥ Структурная правка: Писатель → Фактчекер → Литредактор → Корректор → Верстальщик → QA

---

## Разделение работы между агентами

В проекте одновременно работают два AI-агента. Каждый отвечает за свою область.

### Агент A — Бэкенд и пайплайн (этот чат)

Отвечает за всё серверное и инфраструктурное:

| Область | Файлы |
|---------|-------|
| Telegram-бот | `main.py`, `prepay/`, `config.py` |
| Пайплайны обработки | `pipeline_*.py`, `pipeline_n8n.py` |
| n8n workflow | `n8n-workflows/`, `docker/` |
| Admin-панель (Flask) | `admin/` |
| Личный кабинет — backend | `cabinet/app.py`, `cabinet/tma_api.py` |
| БД и хранилище | `db.py`, `db_draft.py`, `storage.py` |
| Транскрипция и LLM | `transcribe.py`, `llm_bio.py`, `*_client.py` |
| Деплой и инфраструктура | `deploy/`, systemd, nginx, Docker |
| Тесты | `tests/` |

### Агент Б — Фронтенд и лендинг (отдельный чат, Sonnet)

Отвечает за визуальную часть и публичные страницы:

| Область | Файлы |
|---------|-------|
| Лендинг сайта | `landing/` (новая папка) |
| Telegram Mini App (TMA) | `tma/index.html`, `tma/` |
| Личный кабинет — UI | `cabinet/templates/` |
| Статика | `static/` |

**Правила для Агента Б:**
- Не трогать Python-файлы, `main.py`, `pipeline_*.py`, `admin/blueprints/`
- Не менять `deploy/` и systemd конфиги
- Flask-маршруты в `cabinet/app.py` — только согласовывать с Агентом А
- Лендинг размещать в папке `landing/` (отдельно от кабинета)
- Домен лендинга: `glava.family` (основной), Nginx конфиг: `deploy/nginx-glava.conf`
- Домен кабинета: `cabinet.glava.family`, TMA: открывается внутри Telegram

**Текущий стек фронтенда:**
- TMA: чистый HTML/CSS/JS (файл `tma/index.html`)
- Кабинет: Jinja2 шаблоны (Flask)
- Лендинг: на усмотрение Агента Б (статический HTML или простой Flask blueprint)

---

## Соглашения для кода

- Не отключать проверку оплаты (`_user_has_paid`) в production.
- Секреты только в `.env`, не хардкодить в коде.
- Логирование — через `logging`; в тестах — моки БД и внешних API.
- Новые скрипты с вызовом OpenAI — учитывать ограничение доступа из РФ и документировать в `docs/OPENAI_ACCESS.md` при необходимости.
