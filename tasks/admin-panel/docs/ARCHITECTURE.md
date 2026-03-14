# Admin Panel + n8n — архитектура

## Сервисы и порты

| Сервис | Порт | Домен | Запуск |
|--------|------|-------|--------|
| Telegram Bot | — | — | systemd: glava.service |
| User Cabinet (Flask) | 5000 | cabinet.glava.family | systemd: glava-cabinet.service |
| **Admin Panel (Flask)** | **5001** | **admin.glava.family** | **systemd: glava-admin.service** |
| **n8n** | **5678** | внутренний | **Docker** |
| TMA static | — | app.glava.family | Nginx static |
| Landing | — | glava.family | Nginx static |

## Роли и доступы

| Роль | Логин | Доступ |
|------|-------|--------|
| Разработчик | dev | /dev/ — полный технический доступ |
| Продакт (Даша) | dasha | /dasha/ — промпты, заказы, пайплайн |
| Маркетолог (Лена) | lena | /lena/ — рассылки, пользователи |

## Структура файлов

```
admin/
├── app.py              — Flask-приложение (порт 5001)
├── auth.py             — авторизация + декоратор role_required
├── blueprints/
│   ├── dev.py          — /dev/ дашборд разработчика
│   ├── dasha.py        — /dasha/ панель продакта
│   └── lena.py         — /lena/ панель маркетолога
├── templates/
│   ├── base.html       — общий layout (sidebar с ролями)
│   ├── login.html
│   ├── dev/
│   │   └── dashboard.html
│   ├── dasha/
│   │   ├── prompts.html
│   │   ├── prompt_edit.html
│   │   ├── orders.html
│   │   └── order_detail.html
│   └── lena/
│       ├── users.html
│       ├── mailing_new.html
│       └── mailings.html
└── db_admin.py         — функции для admin-специфичных запросов к БД

deploy/
└── glava-admin.service — systemd unit

docker/
└── docker-compose.yml  — n8n контейнер
```

## Новые таблицы PostgreSQL

```sql
-- Промпты агентов (12 ролей)
CREATE TABLE prompts (
    id SERIAL PRIMARY KEY,
    role VARCHAR(50) NOT NULL,        -- 'transcriber', 'fact_extractor', etc.
    version INT NOT NULL DEFAULT 1,
    prompt_text TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    updated_at TIMESTAMP DEFAULT NOW(),
    updated_by VARCHAR(50)            -- 'dasha', 'dev'
);

-- Статусы пайплайна по каждому клиенту
CREATE TABLE pipeline_jobs (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL,
    phase VARCHAR(10) NOT NULL,       -- 'A', 'B'
    current_step VARCHAR(50),         -- 'transcriber', 'ghostwriter', etc.
    status VARCHAR(20) DEFAULT 'pending', -- pending/running/done/error/paused
    n8n_execution_id VARCHAR(100),    -- ID выполнения в n8n
    started_at TIMESTAMP DEFAULT NOW(),
    finished_at TIMESTAMP,
    error TEXT
);

-- Рассылки
CREATE TABLE mailings (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200),
    template_text TEXT NOT NULL,
    segment VARCHAR(50) NOT NULL,     -- 'all', 'paid', 'book_ready', 'inactive'
    scheduled_at TIMESTAMP,
    sent_at TIMESTAMP,
    sent_count INT DEFAULT 0,
    created_by VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Получатели рассылок
CREATE TABLE mailing_recipients (
    id SERIAL PRIMARY KEY,
    mailing_id INT REFERENCES mailings(id),
    telegram_id BIGINT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending', -- pending/sent/error
    sent_at TIMESTAMP,
    error TEXT
);
```

## n8n — конфигурация Docker

```yaml
# docker/docker-compose.yml
version: '3.8'
services:
  n8n:
    image: n8nio/n8n
    container_name: glava-n8n
    restart: always
    ports:
      - "127.0.0.1:5678:5678"  # только localhost, Nginx проксирует
    environment:
      - N8N_HOST=localhost
      - N8N_PORT=5678
      - N8N_PROTOCOL=http
      - WEBHOOK_URL=https://n8n.internal/  # внутренний, бот вызывает напрямую
      - DB_TYPE=postgresdb
      - DB_POSTGRESDB_HOST=localhost
      - DB_POSTGRESDB_DATABASE=glava_n8n   # отдельная БД для n8n
      - DB_POSTGRESDB_USER=...
      - DB_POSTGRESDB_PASSWORD=...
    volumes:
      - n8n_data:/home/node/.n8n
    network_mode: host  # чтобы n8n видел localhost PostgreSQL

volumes:
  n8n_data:
```

## Агентные роли (промпты)

| ID | Роль | Фаза |
|----|------|------|
| transcriber | Транскрибатор | A, B④ |
| fact_extractor | Фактолог | A, B③④ |
| ghostwriter | Писатель | A, B①③④⑥ |
| fact_checker | Фактчекер | A, B③④⑥ |
| literary_editor | Литредактор | A, B②③④⑥ |
| proofreader | Корректор | A, B все |
| photo_editor | Фоторедактор | A, B④⑤ |
| layout_designer | Верстальщик | A, B все |
| layout_qa | Контролёр вёрстки | A, B все |
| producer | Продюсер | A, B (эскалация) |
| interview_architect | Интервьюер | A только |
| triage | Триажер | B только |

## Дашборд разработчика — источники данных

| Виджет | Источник |
|--------|---------|
| Статус сервисов | `systemctl is-active glava glava-cabinet glava-admin` |
| Метрики БД | `SELECT COUNT(*) FROM users/drafts/voices/photos` |
| S3 метрики | `storage.list_objects()` |
| Ошибки | `journalctl -u glava -u glava-cabinet -p err -n 20` |
| Git коммит | `git -C /opt/glava log -1 --format="%h %s %ci"` |
| n8n статус | `GET http://localhost:5678/healthz` |
| Конфиг-чеклист | `os.environ.get(KEY) is not None` для каждого ключа |
