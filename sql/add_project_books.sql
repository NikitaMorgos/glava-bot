-- =============================================
-- Кабинет: версии книг по проектам.
-- В отличие от book_versions (которая привязана к telegram_id и устарела),
-- эта таблица — основной носитель готовых PDF для нового web-кабинета.
-- =============================================

CREATE TABLE IF NOT EXISTS project_books (
    id              SERIAL PRIMARY KEY,
    project_id      INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    version         INTEGER NOT NULL,                  -- v1, v2, ...
    storage_key     TEXT NOT NULL,                     -- s3-ключ PDF
    size_bytes      BIGINT,                            -- размер PDF
    page_count      INTEGER,                           -- если знаем
    status          VARCHAR(20) NOT NULL DEFAULT 'ready', -- ready | revision_in_progress
    notes           TEXT,                              -- что нового в этой версии
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (project_id, version)
);
CREATE INDEX IF NOT EXISTS idx_project_books_project ON project_books(project_id);
CREATE INDEX IF NOT EXISTS idx_project_books_latest
    ON project_books(project_id, version DESC);
