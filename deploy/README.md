# Соглашения для деплоя

## Обновление кода

- **Основной способ:** `ssh glava "bash /opt/glava/ops.sh deploy"` — git pull + restart + health.
- **Альтернатива:** `rsync` с локального ПК (не `scp -r` — создаёт вложенную папку).
- **После обновления:** `systemctl restart glava` и `systemctl restart glava-admin` (делает `deploy`).
- **Сид промптов после обновления:** всегда запускать актуальные `_seed_prompts_vN.py` в `.venv`.

## Безопасность

- **Prod-токен — только на сервере.** Локально — отдельный бот через @BotFather.
- **Никогда не запускать `python main.py` локально с prod-токеном.** Два экземпляра с одним токеном → `telegram.error.Conflict`.

## Виртуальное окружение

- `.venv/` на сервере (`/opt/glava/.venv/`).
- В systemd: `ExecStart=/opt/glava/.venv/bin/python main.py`.

## Проверка после деплоя

```bash
ssh glava "bash /opt/glava/ops.sh health"
```

## Обновление workflow в n8n

1. `git push` с локального компа
2. `ssh root@72.56.121.94 "cd /opt/glava && git pull"`
3. `scp root@72.56.121.94:/opt/glava/n8n-workflows/phase-a.json ~/Downloads/phase-a.json`
4. В n8n UI: три точки → Import from file → выбрать скачанный файл → Save → Publish

## ops.sh — команды

Скрипт: `/opt/glava/ops.sh`. Задача: `tasks/server-ops-access/`.

| Команда | Что делает |
|---------|-----------|
| `health` | Статус бота, Flask, n8n |
| `logs-bot [N]` | Последние N строк лога бота |
| `logs-admin [N]` | Последние N строк лога Flask admin |
| `logs-n8n [N]` | Логи n8n docker |
| `status` | systemctl status сервисов |
| `deploy` | git stash + git pull + restart + health |
| `restart` | Перезапуск сервисов + health |
| `n8n-workflows` | Список воркфлоу |
| `n8n-executions [N]` | Последние N execution'ов |
| `n8n-execution <id>` | Детали execution'а |
| `db-check` | Кол-во промптов и версий книг в БД |
| `seed-prompts` | Обновить промпты в БД |

## SSH доступ

- **Config:** `~/.ssh/config` — алиас `glava` → `root@72.56.121.94`, ключ `~/.ssh/id_ed25519`
- **Проверка:** `ssh glava "echo ok"`

## Сервисы на VPS

| Сервис | Unit | Порт |
|--------|------|------|
| Telegram-бот | `glava` | — |
| Личный кабинет | `glava-cabinet` | 5000 |
| Admin-панель | `glava-admin` | 5001 |
| CCO-бот | `glava-cco` | — |
| n8n (Docker) | `glava-n8n` | 5678 |
