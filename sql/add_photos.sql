-- Таблица фото с подписями (для книги)
-- Фото сохраняется при отправке, подпись — следующим текстовым сообщением
CREATE TABLE IF NOT EXISTS photos (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    telegram_file_id VARCHAR(255) NOT NULL,
    storage_key     VARCHAR(512) NOT NULL,
    caption         TEXT,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_photos_user_id ON photos(user_id);
CREATE INDEX IF NOT EXISTS idx_photos_created_at ON photos(created_at DESC);
