-- =============================================
-- Кабинет: реальный прогресс обработки книги.
-- Каждая запись = одна стадия pipeline (для одного раунда обработки проекта).
-- Worker пишет статусы по мере выполнения; кабинет читает и показывает прогресс.
-- =============================================

CREATE TABLE IF NOT EXISTS project_job_stages (
    id            SERIAL PRIMARY KEY,
    project_id    INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    round_number  INTEGER NOT NULL DEFAULT 1,        -- номер раунда обработки (1, 2, ...)
    stage_key     VARCHAR(50) NOT NULL,              -- 'transcribe', 'extract', ...
    stage_label   VARCHAR(120),                      -- человекочитаемое название для UI
    status        VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending|running|done|failed
    ordering      INTEGER NOT NULL DEFAULT 0,        -- порядок отображения
    started_at    TIMESTAMP WITH TIME ZONE,
    finished_at   TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    created_at    TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (project_id, round_number, stage_key)
);
CREATE INDEX IF NOT EXISTS idx_project_job_stages_project ON project_job_stages(project_id);
CREATE INDEX IF NOT EXISTS idx_project_job_stages_round
    ON project_job_stages(project_id, round_number, ordering);
