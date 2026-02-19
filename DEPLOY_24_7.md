# GLAVA на VPS 24/7 — пошагово

Сайт и бот крутятся на сервере. **Сервер в США/Европе** — OpenAI будет работать без VPN.

**Кратко:** 1) Арендовать VPS (EU/US) → 2) Зайти по SSH → 3) Скопировать проект → 4) Создать .env → 5) Установить и запустить бот+кабинет → 6) Сайт + nginx + SSL → 7) CABINET_SECRET_KEY в .env.

---

## Шаг 1. Арендуй VPS

- **Регион обязательно США или Европа** (иначе OpenAI даст 403).
- Провайдеры: DigitalOcean, Hetzner, Timeweb (датацентр EU/US).
- Тариф: 1 vCPU, 1 GB RAM.
- ОС: **Ubuntu 22.04** или 24.04.

После создания запиши **IP сервера** и пароль root.

---

## Шаг 2. Зайди на сервер

На своём ПК открой PowerShell или cmd:

```bash
ssh root@IP_СЕРВЕРА
```

(подставь свой IP, пароль спросит)

---

## Шаг 3. Скопируй проект на сервер

**Не закрывая сервер**, открой второй терминал на своём ПК и выполни:

```powershell
scp -r "C:\Users\user\Dropbox\Public\Cursor\GLAVA" root@IP_СЕРВЕРА:/opt/glava
```

Папка `venv` и `.env` могут не скопироваться — нормально. На сервере нужен свой `.env`.

---

## Шаг 4. Создай .env на сервере

В терминале, где ты залогинен на сервер:

```bash
cd /opt/glava
nano .env
```

Скопируй содержимое своего локального `.env` (с ПК) и вставь в nano. Либо создай по образцу из `.env.example`. Обязательно заполни:

- `BOT_TOKEN`
- `DATABASE_URL`
- `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET_NAME`, `S3_ENDPOINT_URL`, `S3_REGION`
- `OPENAI_API_KEY`
- при необходимости: `YANDEX_API_KEY`, `CABINET_SECRET_KEY`

Сохрани: **Ctrl+O**, Enter, **Ctrl+X**.

---

## Шаг 5. Установи зависимости и запусти сервисы

Всё на сервере, по очереди:

```bash
apt update && apt install -y python3 python3-venv python3-pip ffmpeg
cd /opt/glava
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

Потом бот и кабинет как сервисы:

```bash
cp /opt/glava/deploy/glava.service /etc/systemd/system/
cp /opt/glava/deploy/glava-cabinet.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable glava glava-cabinet
systemctl start glava glava-cabinet
```

Проверка:

```bash
systemctl status glava
systemctl status glava-cabinet
```

Должно быть `active (running)`.

---

## Шаг 3. Установка

**На сервере выполни:**

```bash
apt update && apt install -y python3 python3-venv python3-pip git ffmpeg
cd /opt/glava
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

**Systemd-сервисы (бот + кабинет):**

```bash
cp /opt/glava/deploy/glava.service /etc/systemd/system/
cp /opt/glava/deploy/glava-cabinet.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable glava glava-cabinet
systemctl start glava glava-cabinet
```

Логи бота в реальном времени: `journalctl -u glava -f`.

---

## Шаг 6. Сайт glava.family и SSL

### 6.1 Лендинг

```bash
mkdir -p /var/www/glava.family
cp -r /opt/glava/landing/* /var/www/glava.family/
```

### 6.2 Nginx и certbot

```bash
apt install -y nginx certbot python3-certbot-nginx
```

### 6.3 Конфиги nginx

**Сайт glava.family:**
```bash
cp /opt/glava/deploy/nginx-glava.conf /etc/nginx/sites-available/glava
ln -sf /etc/nginx/sites-available/glava /etc/nginx/sites-enabled/
```

**Кабинет cabinet.glava.family:**
```bash
cp /opt/glava/deploy/nginx-cabinet.conf /etc/nginx/sites-available/cabinet
ln -sf /etc/nginx/sites-available/cabinet /etc/nginx/sites-enabled/
```

### 6.4 DNS

В панели домена создай A-записи:
- `glava.family` → IP сервера
- `www.glava.family` → IP сервера  
- `cabinet.glava.family` → IP сервера

### 6.5 SSL

```bash
nginx -t
systemctl reload nginx
certbot --nginx -d glava.family -d www.glava.family -d cabinet.glava.family --non-interactive
```

---

## Шаг 7. Кабинет (CABINET_SECRET_KEY)

```bash
nano /opt/glava/.env
```

Добавь (если ещё нет):
```
CABINET_SECRET_KEY=случайная_строка_32_символа
TRUST_PROXY=1
```

Перезапусти кабинет:
```bash
systemctl restart glava-cabinet
```

---

## Готово

| Компонент | URL / сервис |
|-----------|--------------|
| Лендинг | https://glava.family |
| Личный кабинет | https://cabinet.glava.family |
| Бот | работает 24/7 в фоне |

**Полезные команды:**
```bash
systemctl status glava          # статус бота
systemctl restart glava         # перезапуск бота
journalctl -u glava -f          # логи в реальном времени
```

**Обновление после изменений в коде:**
```bash
# Скопируй новые файлы на сервер (scp/rsync), затем:
systemctl restart glava
systemctl restart glava-cabinet
```
