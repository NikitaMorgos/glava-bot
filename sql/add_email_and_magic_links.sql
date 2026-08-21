-- =============================================
-- Кабинет: email + magic-link авторизация
-- Параллельно с существующим username+bcrypt логином.
-- =============================================

-- Email пользователя — опционален. Уникален среди не-NULL значений.
ALTER TABLE users ADD COLUMN IF NOT EXISTS email TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified_at TIMESTAMP WITH TIME ZONE;

-- partial unique: NULL email не считается «дублем»
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_unique
    ON users (LOWER(email))
    WHERE email IS NOT NULL;

-- telegram_id становится опциональным: web-only пользователи без бота
ALTER TABLE users ALTER COLUMN telegram_id DROP NOT NULL;
-- (если на колонке был NOT NULL — снимаем; если уже NULL-able, no-op)

-- Magic-link токены. Один токен — одна попытка входа.
-- purpose: 'login' (вход), 'signup' (первый вход), reserved: 'reset' и т.п.
CREATE TABLE IF NOT EXISTS magic_link_tokens (
    token         VARCHAR(64) PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    purpose       VARCHAR(20) NOT NULL DEFAULT 'login',
    expires_at    TIMESTAMP WITH TIME ZONE NOT NULL,
    used_at       TIMESTAMP WITH TIME ZONE,
    requested_ip  INET,
    created_at    TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_magic_link_tokens_user
    ON magic_link_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_magic_link_tokens_expires
    ON magic_link_tokens(expires_at)
    WHERE used_at IS NULL;
