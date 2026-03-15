# Admin Panel + n8n Pipeline — статус

| Поле | Значение |
|------|---------|
| **Задача** | Admin Panel (Dev/Дasha/Лена) + n8n AI-пайплайн |
| **Создана** | 2026-03-14 |
| **Обновлена** | 2026-03-15 |
| **Статус** | 🟡 Инфраструктура и панели готовы, n8n workflows не построены |

## Этапы

| Этап | Статус |
|------|--------|
| 1. Инфраструктура (Docker, n8n, admin домен) | ✅ Готово |
| 2. БД: новые таблицы | ✅ Готово |
| 3. Дашборд разработчика | ✅ Готово |
| 4. Панель Даши | ✅ Готово (баг сохранения промпта исправлен 2026-03-15) |
| 5. Панель Лены | ✅ Готово |
| 6. n8n Phase A workflow | ⏳ Ожидает (инфраструктура есть, workflow не построен) |
| 7. n8n Phase B workflow | ⏳ Ожидает |

## Что сделано

### Инфраструктура
- Docker + Docker Compose на VPS, контейнер `glava-n8n` запущен (порт 5678)
- Swap 2GB создан (n8n требует памяти, OOM killer был проблемой)
- `/opt/glava/n8n-data/` с правами UID 1000 (пользователь `node` в контейнере)
- `deploy/glava-admin.service` — systemd для Flask admin-панели (порт 5001)
- `deploy/nginx-admin.conf` — Nginx + SSL (certbot, `admin.glava.family`)
- DNS A-запись `admin.glava.family` → IP сервера

### Код
- `admin/app.py` — Flask с авторизацией, 3 роли (dev/dasha/lena), bcrypt
- `admin/auth.py` — декораторы `login_required`, `role_required`
- `admin/db_admin.py` — функции для работы с новыми таблицами (RealDictCursor)
- `admin/blueprints/dev.py` — дашборд разработчика: статус сервисов, метрики БД/S3, логи, git, n8n, конфиг-чеклист, restart-кнопки
- `admin/blueprints/dasha.py` — управление промптами агентов, заказы, пайплайн, отчёты
- `admin/blueprints/lena.py` — пользователи по сегментам, рассылки, триггеры
- `admin/templates/` — Jinja2 + Tailwind CSS (base, login, dev, dasha, lena)
- `scripts/migrate_admin.py` — создание таблиц `prompts`, `pipeline_jobs`, `mailings`, `mailing_recipients`, `mailing_triggers`
- `docker/docker-compose.yml` — n8n с `network_mode: host`, persistent volume

### Известные исправления
- `RealDictCursor` возвращает dict, не tuple → `fetchone()[0]` → `fetchone()["key"]` (исправлено в `db_admin.py`)
- `network_mode: host` несовместим с `ports:` в docker-compose (исправлено)
- n8n Permission denied на `/data/n8n` → `chown -R 1000:1000 /opt/glava/n8n-data`

## Решения

| Вопрос | Решение |
|--------|---------|
| n8n | Docker-контейнер (`docker-compose` v1) |
| Поддомен | `admin.glava.family` (новый, SSL через certbot) |
| Пайплайн | Полная цепочка (12 агентов, Phase A + B) — запланировано |
| Шаблоны рассылок | Plain text |
| Авторизация | Отдельные логины (dev / dasha / lena), пароли в `.env` |
| Ролей | 3: Разработчик, Продакт, Маркетолог |

## Следующие шаги

1. Построить n8n workflow Phase A (12 нод) — открыть `admin.glava.family` → n8n
2. Построить n8n workflow Phase B (Triage Agent + 6 маршрутов)
3. Заполнить таблицу `prompts` промптами 12 агентов (через панель Даши)
4. Подключить webhook бота к n8n (`N8N_WEBHOOK_PHASE_A` в `.env`)
