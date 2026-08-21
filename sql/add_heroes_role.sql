-- =============================================
-- Кабинет: разделение heroes на subject (о ком книга) и narrator (кто рассказывает)
-- =============================================

ALTER TABLE heroes ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'narrator' NOT NULL;

-- Первый созданный hero каждого проекта становится subject
-- (это исторически персонаж, создаваемый формой /projects/new).
UPDATE heroes h
SET role = 'subject'
WHERE id = (
    SELECT MIN(id) FROM heroes
    WHERE project_id = h.project_id
)
AND role <> 'subject';

CREATE INDEX IF NOT EXISTS idx_heroes_project_role ON heroes(project_id, role);
