# GLAVA — контекст для AI-агентов

Файл задаёт контекст проекта для Cursor, Copilot, Codex и других агентов. Используй его при изменении кода, добавлении фич и отладке.

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
- **Конфиг:** `.env` (не коммитить), шаблон — `.env.example`. Ключи: `BOT_TOKEN`, БД (PostgreSQL), S3, `YANDEX_API_KEY`, `ASSEMBLYAI_API_KEY`, `OPENAI_API_KEY`, ЮKassa.

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
| Telegram Mini App (кабинет) | `tma/index.html` (фронтенд), `cabinet/tma_api.py` (API Blueprint), `deploy/nginx-tma.conf` |
| Автотесты бота | `tests/test_bot_flows.py` |
| Деплой, systemd | `deploy/deploy.sh` (основной скрипт), `deploy/glava.service`, `DEPLOY_24_7.md`, `DEPLOY_TIMEWEB.md`, `deploy/DEPLOY_GLAVA_FAMILY.md` |

---

## Документация (skills / гайды)

| Документ | Содержание |
|----------|------------|
| **docs/TESTING.md** | Система тестирования: тест-кейсы TC-01…TC-27, протокол запуска, отчёты, реагирование на падения. |
| **docs/OPENAI_ACCESS.md** | Доступ к OpenAI из РФ, запуск на сервере, копирование файлов, генерация bio и уточняющих вопросов. |
| **docs/DIARIZATION.md** | Разбивка интервью по спикерам: SpeechKit, AssemblyAI, Whisper; рекомендации по длинным файлам. |
| **docs/USER_SCENARIOS.md** | Пользовательские сценарии и таблица тест-кейсов для бота. |
| **ARCHITECTURE.md** | Схема сервисов, бот, кабинет, БД, S3, деплой. |

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

- **Виртуальное окружение:** `venv/` (не `.venv/`). Путь на сервере: `/opt/glava/venv/`.  
  В systemd: `ExecStart=/opt/glava/venv/bin/python main.py`.

- **Проверка после деплоя:**
  ```bash
  systemctl status glava            # active (running), время старта — свежее
  journalctl -u glava -n 20         # нет ошибок импорта
  ```

---

## Соглашения для кода

- Не отключать проверку оплаты (`_user_has_paid`) в production.
- Секреты только в `.env`, не хардкодить в коде.
- Логирование — через `logging`; в тестах — моки БД и внешних API.
- Новые скрипты с вызовом OpenAI — учитывать ограничение доступа из РФ и документировать в `docs/OPENAI_ACCESS.md` при необходимости.
