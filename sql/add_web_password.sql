-- Пароль для входа в личный кабинет (веб)
ALTER TABLE users ADD COLUMN IF NOT EXISTS web_password_hash TEXT;
