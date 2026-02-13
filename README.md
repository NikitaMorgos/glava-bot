# GLAVA — Telegram-бот для голосовых сообщений

Простой MVP-бот: принимает голосовые, сохраняет в облаке (S3-совместимое хранилище) и в PostgreSQL, позволяет просмотреть и скачать свои файлы.

---

## Структура проекта

```
GLAVA/
├── main.py           # Точка входа, логика бота
├── config.py         # Загрузка настроек из .env
├── db.py             # Работа с PostgreSQL
├── storage.py        # Работа с S3-облаком
├── requirements.txt  # Зависимости Python
├── .env.example      # Пример переменных окружения
├── .env              # Твои переменные (создать самому, не коммитить!)
├── sql/
│   └── init_db.sql   # Скрипт создания таблиц в БД
└── README.md         # Этот файл
```

---

## Шаг 1: Что установить

### 1. Python

- Нужен Python **3.10 или выше**
- Проверка: `python --version` или `python3 --version`

### 2. PostgreSQL

- Установи [PostgreSQL](https://www.postgresql.org/download/) (или используй облачный сервис)
- Запомни: пользователь, пароль, порт (обычно 5432)

### 3. S3-совместимое хранилище

Выбери один из вариантов:

| Сервис | Endpoint | Регион |
|--------|----------|--------|
| **MinIO** (локально) | `http://localhost:9000` | можно оставить пустым |
| **Yandex Object Storage** | `https://storage.yandexcloud.net` | `ru-central1` |
| **AWS S3** | `https://s3.amazonaws.com` | `us-east-1` или другой |

Создай бакет (контейнер для файлов) и получи Access Key + Secret Key.

---

## Шаг 2: Создание бота в Telegram

1. Открой [@BotFather](https://t.me/BotFather) в Telegram
2. Отправь `/newbot`
3. Введи имя бота (например: GLAVA Voice Bot)
4. Введи username (например: glava_voice_bot)
5. Скопируй **токен** — он понадобится для `BOT_TOKEN`

---

## Шаг 3: Создание базы данных

1. Создай базу:

   ```sql
   CREATE DATABASE glava_bot;
   ```

2. Выполни скрипт создания таблиц:

   ```bash
   psql -U postgres -d glava_bot -f sql/init_db.sql
   ```

   (замени `postgres` на своего пользователя, если другой)

---

## Шаг 4: Переменные окружения

1. Скопируй пример:

   ```bash
   copy .env.example .env
   ```

   (на Linux/Mac: `cp .env.example .env`)

2. Открой `.env` и заполни:

   | Переменная | Описание | Пример |
   |------------|----------|--------|
   | `BOT_TOKEN` | Токен от @BotFather | `7123456789:AAH...` |
   | `DATABASE_URL` | Строка подключения к Postgres | `postgresql://postgres:пароль@localhost:5432/glava_bot` |
   | `S3_ENDPOINT_URL` | URL хранилища | `https://storage.yandexcloud.net` |
   | `S3_ACCESS_KEY` | Access Key | из панели облака |
   | `S3_SECRET_KEY` | Secret Key | из панели облака |
   | `S3_BUCKET_NAME` | Имя бакета | `glava-voice-messages` |
   | `S3_REGION` | Регион (если нужен) | `ru-central1` или `us-east-1` |

   Опционально: `LIST_LIMIT=5` — сколько голосовых показывать в `/list` (по умолчанию 5).

---

## Шаг 5: Установка зависимостей и запуск

1. Создай виртуальное окружение (рекомендуется):

   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

   (на Linux/Mac: `source venv/bin/activate`)

2. Установи зависимости:

   ```bash
   pip install -r requirements.txt
   ```

3. Запусти бота:

   ```bash
   python main.py
   ```

   В консоли должно появиться: `Бот запущен. Нажми Ctrl+C для остановки.`

---

## Как проверить

1. Найди своего бота в Telegram по username
2. Отправь `/start` — бот ответит приветствием
3. Отправь голосовое сообщение — бот ответит «Голосовое сохранено»
4. Отправь `/list` — бот пришлёт список твоих голосовых со ссылками для скачивания
5. Перейди по ссылке — файл должен скачаться

То же самое может сделать Никита (или любой другой пользователь): у каждого свой список голосовых.

---

## Транскрибация голосовых

При экспорте клиента (`export_client.py TELEGRAM_ID`) голосовые автоматически транскрибируются в текст. Результат — `transcript.txt` в папке экспорта.

**Требования:**
- `pip install openai-whisper`
- [ffmpeg](https://ffmpeg.org/download.html) в PATH

Если Whisper не установлен, экспорт работает без транскрипции (transcript.txt не создаётся).

### Диаризация (разделение по спикерам)

Для интервью с несколькими участниками:

```
python export_client.py TELEGRAM_ID --diarize
```

Работает через Resemblyzer без регистрации. Подробнее: [DIARIZATION_SETUP.md](DIARIZATION_SETUP.md).

---

## Устранение типичных ошибок

- **«Не задана обязательная переменная»** — проверь `.env`, все ли переменные заполнены
- **«Connection refused» (Postgres)** — БД не запущена или неверный хост/порт
- **«No such bucket»** — бакет не создан в облаке, создай его вручную
- **«Access Denied» (S3)** — неверный Access Key или Secret Key

---

## Развёртывание на VPS (24/7)

См. **[VPS_DEPLOY.md](VPS_DEPLOY.md)** — пошаговая инструкция для Ubuntu/Debian.

---

## Лицензия

MIT
