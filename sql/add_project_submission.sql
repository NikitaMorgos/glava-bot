-- =============================================
-- Кабинет: клиент подтверждает «всё загружено» отдельным действием.
-- Когда materials_submitted_at NOT NULL — клиент явно «передал материалы нам».
-- Сбрасывается в NULL при публикации новой версии questions (новый раунд).
-- =============================================

ALTER TABLE projects ADD COLUMN IF NOT EXISTS materials_submitted_at TIMESTAMP WITH TIME ZONE;
