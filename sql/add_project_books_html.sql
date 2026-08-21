-- =============================================
-- Кабинет: HTML-источник книги (для inline-редактора и регенерации PDF)
-- =============================================

ALTER TABLE project_books ADD COLUMN IF NOT EXISTS html_storage_key TEXT;
ALTER TABLE project_books ADD COLUMN IF NOT EXISTS edited_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE project_books ADD COLUMN IF NOT EXISTS edited_by_user_id INTEGER REFERENCES users(id);
