# GLAVA — контекст для AI-агентов

Контекст проекта для Cursor, Copilot, Codex и других агентов.

---

## Обзор

**GLAVA** — Telegram-бот и AI-пайплайн для создания семейных книг-биографий: приём голосовых и фото, транскрипция, формирование биографии через цепочку AI-агентов (n8n), доставка PDF в Telegram. Оплата через ЮKassa. Пайплайн только после оплаты.

Подробнее: `ARCHITECTURE.md`, `README.md`.

---

## Стек

- **Python 3.10+**, Flask, PostgreSQL, S3-совместимое хранилище
- **Telegram Bot API** (`python-telegram-bot[job-queue]`)
- **LLM:** OpenAI (GPT-4o) — биография, вопросы, поддержка, CCO-агент
- **Транскрипция:** Яндекс SpeechKit, AssemblyAI (диаризация по спикерам)
- **Запись онлайн-звонков:** `meeting_bot.py` — Playwright + Chromium + Xvfb + PulseAudio (Telemost, Zoom, Jitsi)
- **AI-пайплайн:** n8n (Docker) — 14 агентов (Phase A + Phase B)
- **Зависимости:** `requirements.txt`, тесты: `requirements-dev.txt`
- **Конфиг:** `.env` (шаблон `.env.example`)

---

## Сервисы

| Сервис | Unit / способ запуска | Порт |
|--------|----------------------|------|
| Telegram-бот | `glava` (systemd) | — |
| Личный кабинет | `glava-cabinet` | 5000 |
| Admin-панель | `glava-admin` | 5001 |
| CCO-бот | `glava-cco` | — |
| n8n (Docker) | `glava-n8n` | 5678 |

Деплой, SSH, ops.sh → `deploy/README.md`.

---

## Команды

```bash
# Тесты
pytest tests/ -v
python scripts/run_test_report.py

# Бот (локально, с отдельным BOT_TOKEN)
python main.py

# Деплой на сервер
ssh glava "bash /opt/glava/ops.sh deploy"
```

---

## Правила (`.cursor/rules/`)

| Правило | Срабатывает | Описание |
|---------|-------------|----------|
| `payment-required.mdc` | `main.py`, `pipeline_*`, `prepay/` | Пайплайн и приём файлов только после оплаты |
| `task-completion.mdc` | `tasks/**` | Обязательное обновление документации после задачи |
| `agent-separation.mdc` | `landing/`, `tma/`, `static/`, `cabinet/templates/` | Разделение зон Агента А и Б |

---

## Управление задачами

Для каждой задачи — каталог `tasks/<task>/` со структурой:

| Файл | Назначение |
|------|-----------|
| `status.md` | Текущий статус и версия |
| `plan.md` | План работ |
| `tasks/` | Чек-листы |
| `docs/` | Документы |
| `breadcrumbs/` | Заметки и диагностика |

Любой агент, создающий задачу, обязан завести каталог и заполнить `status.md` + `plan.md`.

---

## Документация

| Документ | Содержание |
|----------|------------|
| `ARCHITECTURE.md` | Схема сервисов, БД, S3, деплой |
| `deploy/README.md` | Деплой, ops.sh, SSH, сервисы на VPS |
| `docs/TESTING.md` | Тесты TC-01…TC-44, протокол запуска |
| `docs/OPENAI_ACCESS.md` | Доступ к OpenAI из РФ |
| `docs/DIARIZATION.md` | Диаризация: SpeechKit, AssemblyAI, Whisper |
| `docs/N8N_DASHA_GUIDE.md` | Управление промптами и агентами для Даши |

### Задачи

| Задача | Статус |
|--------|--------|
| `tasks/admin-panel/` | ✅ Phase A+B запущены |
| `tasks/bot-scenario-v2/` | ✅ Бот v2 по спеку Даши |
| `tasks/bot-tests-panel/` | ✅ Авто-тесты + панель |
| `tasks/task-promo-codes/` | ✅ Промо-коды + планировщик |
| `tasks/support-bot/` | ✅ AI-поддержка (GPT-4o) |
| `tasks/file-upload/` | ✅ Веб-загрузка > 20 МБ |
| `tasks/landing/` | ✅ Лендинг v4.1 |
| `tasks/email-glava-family/` | ✅ Корп. почта |
| `tasks/server-ops-access/` | ✅ SSH + ops.sh |
| `tasks/security-audit/` | ⚠️ Аудит завершён, фиксы не начаты |
| `tasks/reliability-audit/` | ⚠️ Аудит завершён, фиксы не начаты |
| `tasks/tma-cabinet/` | 🟡 Пауза |
| `tasks/recall-ai/` | 🟡 Ожидает API-ключа |
| `tasks/meeting-bot/` | ✅ Запись онлайн-звонков работает (Telemost протестировано) |
| `tasks/cco-agent/` | 🟢 В работе |

---

## Соглашения для кода

- Проверка оплаты (`_user_has_paid`) — не отключать в production
- Секреты только в `.env`, не хардкодить
- Логирование через `logging`; в тестах — моки
- OpenAI-скрипты — учитывать ограничение доступа из РФ
- Patch-скрипты для n8n — `scripts/_patch_n8n_vN.py`
- `meeting_bot.py` — запись звонков только через Xvfb + non-headless Chrome; провайдер выбирается в `_online_meeting_provider()` (приоритет: meeting_bot → mymeet → recall)

---

## Tools и MCP

**Context7** — актуальная документация по библиотекам. При работе с внешними API — сначала Context7, потом код.
