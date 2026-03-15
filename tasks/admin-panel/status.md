# Admin Panel + n8n Pipeline — статус

| Поле | Значение |
|------|---------|
| **Задача** | Admin Panel (Dev/Даша/Лена) + n8n AI-пайплайн |
| **Создана** | 2026-03-14 |
| **Обновлена** | 2026-03-15 |
| **Статус** | 🟢 Phase A workflow запущен и подключён к боту |

## Этапы

| Этап | Статус |
|------|--------|
| 1. Инфраструктура (Docker, n8n, admin домен) | ✅ Готово |
| 2. БД: новые таблицы | ✅ Готово |
| 3. Дашборд разработчика | ✅ Готово |
| 4. Панель Даши | ✅ Готово |
| 5. Панель Лены | ✅ Готово |
| 6. n8n Phase A workflow | ✅ Готово — импортирован, опубликован, подключён |
| 7. n8n Phase B workflow | ⏳ Следующий этап |

## Что сделано

### Инфраструктура
- Docker на VPS, контейнер `glava-n8n` запущен через `docker run` (не `docker-compose` — баг v1.29.2 с `ContainerConfig`)
- n8n доступен через Nginx: `https://admin.glava.family/n8n/` (проксирование `/n8n/` → `127.0.0.1:5678`)
- n8n аккаунт создан (owner), workflow опубликован
- Swap 2GB включён для стабильной работы
- `N8N_PATH=/n8n/`, `N8N_EDITOR_BASE_URL=https://admin.glava.family/n8n/` — заданы при `docker run`

### Код
- `admin/blueprints/api.py` — внутренний API для n8n:
  - `GET /api/prompts/<role>` — возвращает текущий промпт агента из БД
  - `POST /api/jobs/update` — обновляет статус пайплайн-джобы
  - `GET /api/health` — healthcheck
- `admin/db_admin.py` — добавлена `upsert_pipeline_job()`
- `admin/app.py` — зарегистрирован API blueprint
- `pipeline_n8n.py` — триггер n8n из Python после транскрипции
- `pipeline_transcribe_bio.py` — после транскрипции: если `N8N_WEBHOOK_PHASE_A` задан → вызывает n8n; иначе → прямой OpenAI (fallback)
- `n8n-workflows/phase-a.json` — импортируемый workflow для n8n (Phase A)
- `scripts/migrate_admin.py` — добавлены миграции: колонка `step` и UNIQUE constraint на `(telegram_id, phase)` в `pipeline_jobs`

### n8n Phase A workflow — цепочка агентов
```
Webhook (POST /webhook/glava/phase-a)
  → Get Prompt: Fact Extractor  → Fact Extractor (gpt-4o-mini)
  → Get Prompt: Ghostwriter     → Ghostwriter (gpt-4o)
  → Get Prompt: Fact Checker    → Fact Checker (gpt-4o-mini)
  → Get Prompt: Literary Editor → Literary Editor (gpt-4o)
  → Get Prompt: Proofreader     → Proofreader (gpt-4o-mini)
       ├─→ Send Bio to Telegram (готовая глава)     → Update Job Status
       └─→ Get Prompt: Interview Architect → Interview Architect → Send Questions to Telegram
```
- Промпты каждого агента берутся из БД через `GET http://127.0.0.1:5001/api/prompts/<role>`
- Если промпт не заполнен — используется встроенный fallback-промпт
- Результат (глава + уточняющие вопросы) отправляется в Telegram напрямую через Bot API
- Production URL: `https://admin.glava.family/n8n/webhook/glava/phase-a`

### Подключение к боту
- `N8N_WEBHOOK_PHASE_A=https://admin.glava.family/n8n/webhook/glava/phase-a` — прописан в `/opt/glava/.env`
- Бот перезапущен и подхватил переменную

### Известные исправления
- `RealDictCursor` → `fetchone()["key"]` вместо `fetchone()[0]` (db_admin.py)
- `docker-compose up --force-recreate` вызывал `KeyError: ContainerConfig` (баг v1.29.2) → используем `docker run` напрямую
- n8n за Nginx: нужен `N8N_PATH=/n8n/` иначе JS-ресурсы не грузятся
- URL промптов в workflow изначально динамические через `$json.body.admin_api_url` → не работают в тест-режиме → захардкожены как `http://127.0.0.1:5001/api/...`
- Webhook должен принимать POST (не GET по умолчанию)

## Управление для Даши

| Уровень | Где | Что делает |
|---------|-----|-----------|
| Промпты агентов | `admin.glava.family` → Скрипты агентов | Меняет текст промпта → изменения вступают в силу сразу (без деплоя) |
| Структура флоу | `admin.glava.family/n8n/` | Добавляет/убирает ноды, меняет порядок агентов |
| Заказы и статусы | `admin.glava.family` → Заказы | Видит какой клиент на каком этапе |

Доступ в n8n: Settings → Users → Invite user (роль Member — редактирование без удаления).

## Решения

| Вопрос | Решение |
|--------|---------|
| n8n запуск | `docker run` напрямую (docker-compose v1 несовместим с новым образом) |
| n8n доступ | Через Nginx `/n8n/` path (порт 5678 закрыт файрволлом Timeweb) |
| Промпты в workflow | Захардкожены `http://127.0.0.1:5001/api/prompts/<role>` |
| Поддомен | `admin.glava.family` (SSL через certbot) |
| Авторизация | Отдельные логины (dev / dasha / lena) |

## Следующие шаги

1. Заполнить промпты 12 агентов через панель Даши (`admin.glava.family/dasha/prompts`)
2. Протестировать полный прогон: голосовое → транскрипция → n8n → Telegram
3. Построить n8n Phase B workflow (Triage Agent + 6 маршрутов для правок)
