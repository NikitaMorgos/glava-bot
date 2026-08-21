-- =============================================
-- Редактор книги: сохраняем структуру book.json из pipeline glava в БД.
-- Это позволит открыть редактор без обращения к S3, и удобно править
-- (главы → блоки: paragraph, subsection_title, pull_quote, photo, callout, dates).
-- =============================================

ALTER TABLE project_books ADD COLUMN IF NOT EXISTS blocks_json JSONB;
