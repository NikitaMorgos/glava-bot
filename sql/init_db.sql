-- =============================================
-- Схема базы данных для бота GLAVA
-- Запусти этот скрипт один раз при первом развёртывании
-- =============================================

-- Таблица пользователей Telegram
-- telegram_id — уникальный ID пользователя в Telegram (используем для привязки)
-- username — имя пользователя (@username), может быть пустым
CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    telegram_id     BIGINT UNIQUE NOT NULL,
    username        VARCHAR(255),
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Индекс для быстрого поиска пользователя по telegram_id
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);

-- Таблица голосовых сообщений
-- user_id — ссылка на пользователя из таблицы users
-- telegram_file_id — ID файла в Telegram (на случай, если нужен доступ к оригиналу)
-- storage_key — ключ/путь файла в облачном хранилище (S3)
-- duration — длительность голосового в секундах (если Telegram передал)
CREATE TABLE IF NOT EXISTS voice_messages (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    telegram_file_id VARCHAR(255) NOT NULL,
    storage_key     VARCHAR(512) NOT NULL,
    duration        INTEGER,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Индекс для быстрого получения голосовых конкретного пользователя
CREATE INDEX IF NOT EXISTS idx_voice_messages_user_id ON voice_messages(user_id);
-- Сортировка по дате — для команды /list (последние N)
CREATE INDEX IF NOT EXISTS idx_voice_messages_created_at ON voice_messages(created_at DESC);
