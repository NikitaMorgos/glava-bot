# Архитектура GLAVA

Проект GLAVA — семейные истории: голосовые сообщения и фото, сбор материалов для книги.  
Лендинг: glava.family. Бот: @glava_voice_bot. Личный кабинет: cabinet.glava.family.

---

## Общая схема

```
                    ┌─────────────────────────────────────────────────────────┐
                    │                      Интернет                            │
                    └─────────────────────────────────────────────────────────┘
                                           │
         ┌─────────────────────────────────┼─────────────────────────────────┐
         │                                 │                                 │
         ▼                                 ▼                                 ▼
   glava.family                    cabinet.glava.family              api.telegram.org
   (лендинг)                       (личный кабинет)                   (бот)
         │                                 │                                 │
         └─────────────────────────────────┼─────────────────────────────────┘
                                           │
                    ┌──────────────────────┴──────────────────────┐
                    │              VPS (85.239.60.90)             │
                    │                    nginx                    │
                    │  glava.family      → /var/www/glava.family  │
                    │  cabinet.glava.family → proxy 127.0.0.1:5000│
                    └──────────────────────┬──────────────────────┘
                                           │
                    ┌──────────────────────┴──────────────────────┐
                    │  glava-cabinet (gunicorn :5000)             │
                    │  Flask-приложение, авторизация, dashboard   │
                    └──────────────────────┬──────────────────────┘
                                           │
         ┌─────────────────────────────────┼─────────────────────────────────┐
         │                                 │                                 │
         ▼                                 ▼                                 ▼
   PostgreSQL                          S3 (Yandex/AWS)              glava (бот)
   (Neon / внешняя)                    (голосовые, фото)             python main.py
```

---

## Сервисы

### 1. Telegram-бот (`main.py`)

**Назначение:** Приём голосовых и фото, сохранение в облако, показ списка, настройка пароля для кабинета.

**Команды:**
- `/start` — приветствие и подсказки
- `/list` — последние голосовые и фото со ссылками на скачивание
- `/cabinet` — установка пароля для входа в личный кабинет

**Обработка сообщений:**
- Голосовые (VOICE), аудио (AUDIO), документы (DOCUMENT с .ogg/.mp3 и т.п.) → сохранение в S3, запись в БД
- Фото → сохранение в S3, ожидание подписи следующим текстовым сообщением
- Текст (не команда) → подпись к последнему фото или пароль для `/cabinet`

**Запуск:** `python main.py` (polling)  
**На VPS:** systemd `glava.service` → `/opt/glava/venv/bin/python main.py`

---

### 2. Личный кабинет (`cabinet/app.py`)

**Назначение:** Веб-интерфейс для пользователей. Вход по логину (@username или telegram_id) и паролю.

**Страницы:**
- `/` — редирект на /login или /dashboard
- `/login` — форма входа
- `/dashboard` — голосовые и фото (как /list), ссылки на скачивание, материалы
- `/questions` — вопросы для интервью
- `/logout` — выход

**Запуск:** `gunicorn -w 1 -b 127.0.0.1:5000 cabinet.app:app`  
**На VPS:** systemd `glava-cabinet.service` → gunicorn

---

### 3. Лендинг (glava.family)

**Файлы:** `landing/index.html` (статический HTML)  
**На VPS:** nginx отдаёт из `/var/www/glava.family/`  
**Конфиг:** `deploy/nginx-glava.conf`

---

## Порядок работы (потоки данных)

### Голосовое сообщение

1. Пользователь отправляет голосовое в боте
2. Бот скачивает файл через Telegram API
3. `storage.upload_file()` загружает в S3 по ключу `users/{user_id}/{uuid}.ogg`
4. `db.save_voice_message()` сохраняет запись в `voice_messages` (storage_key, duration)
5. Ответ: «Аудио сохранено.»

### Фото с подписью

1. Пользователь отправляет фото
2. Бот загружает в S3, сохраняет в `photos` с `caption = NULL`
3. Ответ: «Напиши подпись»
4. Пользователь отправляет текст
5. `db.get_pending_photo()` находит последнее фото без подписи
6. `db.update_photo_caption()` обновляет подпись
7. Ответ: «Подпись сохранена»

### Личный кабинет

1. Пользователь: `/cabinet` → вводит пароль
2. `db.set_web_password()` сохраняет bcrypt-хэш в `users.web_password_hash`
3. На cabinet.glava.family: логин (username или telegram_id) + пароль
4. `get_user_by_login()` находит пользователя, `verify_password()` проверяет
5. Сессия: `session["telegram_id"]`
6. Dashboard: `db.get_user_all_data()` + `storage.get_presigned_download_url()` для каждого файла

### /list

1. `db.get_user_voice_messages()` и `db.get_user_photos()`
2. Для каждого файла: `storage.get_presigned_download_url(storage_key)` — временная ссылка (1 ч)
3. Отправка списка в Telegram с HTML-ссылками

---

## База данных (PostgreSQL)

### Таблицы

| Таблица           | Назначение                                         |
|-------------------|----------------------------------------------------|
| `users`           | Пользователи: telegram_id, username, web_password_hash |
| `voice_messages`  | Голосовые: user_id, storage_key, duration, transcript |
| `photos`          | Фото: user_id, storage_key, caption                |

### Миграции

- `sql/init_db.sql` — users, voice_messages
- `sql/add_photos.sql` — photos
- `sql/add_web_password.sql` — web_password_hash в users

---

## Хранилище (S3)

- **Ключи:** `users/{user_id}/{uuid}.{ext}` — для голосовых и фото
- **Доступ:** presigned URL (1 час) для скачивания
- **Совместимо с:** AWS S3, Yandex Object Storage, MinIO

---

## Конфигурация (.env)

| Переменная        | Назначение                              |
|-------------------|-----------------------------------------|
| BOT_TOKEN         | Токен Telegram-бота                     |
| DATABASE_URL      | PostgreSQL connection string            |
| S3_*              | endpoint, access key, secret, bucket    |
| CABINET_SECRET_KEY| Секрет для Flask-сессий                 |
| TRUST_PROXY       | 1 — для работы за nginx (HTTPS)         |
| LIST_LIMIT        | Сколько голосовых в /list (по умолчанию 5) |

---

## Развёртывание на VPS

### Сервисы systemd

| Сервис          | Команда запуска                              |
|-----------------|----------------------------------------------|
| glava           | `python main.py`                             |
| glava-cabinet   | `gunicorn -b 127.0.0.1:5000 cabinet.app:app` |

### Nginx

| Домен              | Конфиг                  | Назначение                    |
|--------------------|-------------------------|-------------------------------|
| glava.family       | nginx-glava.conf        | Статика из /var/www/glava.family |
| cabinet.glava.family | nginx-cabinet.conf    | Прокси на 127.0.0.1:5000      |

### SSL

Certbot после настройки DNS:
```bash
certbot --nginx -d glava.family -d www.glava.family -d cabinet.glava.family --non-interactive
```

---

## Структура проекта

```
GLAVA/
├── main.py              # Бот
├── config.py            # Конфигурация из .env
├── db.py                # Работа с PostgreSQL
├── storage.py           # S3: загрузка, presigned URL
├── cabinet/
│   ├── app.py           # Flask-приложение
│   ├── templates/       # HTML-шаблоны
│   └── static/pdfs/     # PDF-документы
├── landing/
│   └── index.html       # Лендинг glava.family
├── deploy/
│   ├── glava.service
│   ├── glava-cabinet.service
│   ├── nginx-glava.conf
│   ├── nginx-cabinet.conf
│   └── deploy.sh
├── sql/
│   ├── init_db.sql
│   ├── add_photos.sql
│   └── add_web_password.sql
├── scripts/             # Утилиты (PDF, экспорт и т.д.)
└── .env                 # Секреты (не в git)
```

---

## DNS (nic.ru)

Для работы сайтов нужны A-записи:

| Запись               | IP             |
|----------------------|----------------|
| glava.family         | 85.239.60.90   |
| www.glava.family     | 85.239.60.90   |
| cabinet.glava.family | 85.239.60.90   |
