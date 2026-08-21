-- =============================================
-- Кабинет: доп. вопросы по проекту (questions.md → веб)
-- =============================================

CREATE TABLE IF NOT EXISTS project_questions (
    id            SERIAL PRIMARY KEY,
    project_id    INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    version       INTEGER NOT NULL,        -- v1, v2 — после каждой итерации материалов
    blocks_json   JSONB NOT NULL,          -- [{title, questions: [...]}, ...]
    blitz_json    JSONB,                   -- ["Любимое блюдо?", ...]  (optional)
    notes         TEXT,
    created_at    TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (project_id, version)
);
CREATE INDEX IF NOT EXISTS idx_project_questions_project ON project_questions(project_id);
