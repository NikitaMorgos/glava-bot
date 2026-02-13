# Развёртывание GLAVA на VPS (24/7)

Инструкция по запуску бота на виртуальном сервере (Ubuntu/Debian).

---

## 1. Аренда VPS

Подойдёт любой провайдер: **DigitalOcean**, **Hetzner**, **Timeweb**, **Selectel** и т.д.

- **Минимум:** 1 vCPU, 512 MB RAM
- **ОС:** Ubuntu 22.04 или 24.04

---

## 2. Подключение к серверу

```bash
ssh root@IP_АДРЕС_СЕРВЕРА
```

(или используй ключ: `ssh -i ~/.ssh/id_rsa root@IP`)

---

## 3. Ручная установка

### 3.1 Системные пакеты

```bash
apt update
apt install -y python3 python3-venv python3-pip git ffmpeg
```

### 3.2 Папка проекта

Скопируй проект на сервер одним из способов:

**Вариант A — через SCP (с локального ПК):**

```bash
scp -r "C:\Users\user\Dropbox\Public\Cursor\GLAVA" root@IP_СЕРВЕРА:/opt/glava
```

**Вариант B — через Git (если проект на GitHub):**

```bash
mkdir -p /opt/glava
cd /opt/glava
git clone https://github.com/ТВОЙ_USER/GLAVA.git .
```

**Вариант C — rsync (исключая лишнее):**

```bash
rsync -avz --exclude '.env' --exclude 'venv' --exclude '__pycache__' \
  /путь/к/GLAVA/ root@IP:/opt/glava/
```

### 3.3 Виртуальное окружение

```bash
cd /opt/glava
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3.4 Переменные окружения

```bash
cp .env.example .env
nano .env
```

Заполни:

- `BOT_TOKEN` — токен от @BotFather
- `DATABASE_URL` — строка подключения к PostgreSQL (Neon, Supabase, локальный Postgres)
- `S3_*` — ключи Yandex Object Storage (или другого S3)
- `YANDEX_API_KEY` — для SpeechKit (если нужна транскрипция при экспорте)

### 3.5 Сброс webhook (важно)

Если бот раньше работал через webhook, перед первым polling-запуском на VPS выполни:

```bash
source venv/bin/activate
python fix_webhook.py
```

### 3.6 Systemd — автозапуск 24/7

```bash
# Копируем unit-файл
cp deploy/glava.service /etc/systemd/system/

# Если проект в другой папке — отредактируй пути
nano /etc/systemd/system/glava.service
```

Пример `glava.service`:

```ini
[Unit]
Description=GLAVA Telegram Bot
After=network.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/opt/glava
ExecStart=/opt/glava/venv/bin/python main.py
Restart=always
RestartSec=10
EnvironmentFile=/opt/glava/.env

[Install]
WantedBy=multi-user.target
```

Дальше:

```bash
systemctl daemon-reload
systemctl enable glava
systemctl start glava
systemctl status glava
```

---

## 4. Полезные команды

| Действие              | Команда                    |
|-----------------------|----------------------------|
| Статус бота           | `systemctl status glava`   |
| Логи в реальном времени | `journalctl -u glava -f` |
| Перезапуск            | `systemctl restart glava`  |
| Остановка             | `systemctl stop glava`     |

---

## 5. Обновление бота

```bash
cd /opt/glava
git pull   # если через Git
# или scp/rsync новых файлов
systemctl restart glava
```

---

## 6. Важно

- **PostgreSQL** и **S3** уже используются у тебя (Neon, Yandex Cloud) — их не нужно ставить на VPS
- **Транскрибация** (export_client.py) запускается локально, на VPS крутится только бот
- Не коммить `.env` — там секреты
