-- =============================================
-- GLAVA v3 — State Machine (CJM: инициатор, взрослый, ребёнок)
-- Миграция: проекты, герои, состояние пользователя
-- =============================================

-- web_password_hash для users (если ещё нет)
ALTER TABLE users ADD COLUMN IF NOT EXISTS web_password_hash TEXT;

-- Проекты (владелец = инициатор)
CREATE TABLE IF NOT EXISTS projects (
    id              SERIAL PRIMARY KEY,
    owner_user_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_type    VARCHAR(50) NOT NULL DEFAULT 'one_person',  -- one_person | family
    goal            VARCHAR(100),   -- для_семьи | для_детей | подарок_к_дате
    collection_strategy VARCHAR(50), -- self_interview | invite_relative | mixed
    scenario_type   VARCHAR(50) DEFAULT 'basic',  -- basic | extended | custom
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_projects_owner ON projects(owner_user_id);

-- Герои (персонажи книги: кто рассказывает)
CREATE TABLE IF NOT EXISTS heroes (
    id              SERIAL PRIMARY KEY,
    project_id      INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name            VARCHAR(255),
    relation        VARCHAR(100),   -- мама, папа, бабушка...
    years           VARCHAR(50),    -- годы жизни
    place           VARCHAR(255),
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_heroes_project ON heroes(project_id);

-- Состояние пользователя в боте (персистентное)
CREATE TABLE IF NOT EXISTS bot_user_state (
    telegram_id     BIGINT PRIMARY KEY,
    state           VARCHAR(80) NOT NULL DEFAULT 'START',
    project_id      INTEGER REFERENCES projects(id) ON DELETE SET NULL,
    hero_id         INTEGER REFERENCES heroes(id) ON DELETE SET NULL,
    invitation_id   INTEGER,
    question_index  INTEGER DEFAULT 0,
    payload         JSONB,          -- доп. контекст: {last_photo_id, invite_token, ...}
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Приглашения родственников
CREATE TABLE IF NOT EXISTS invitations (
    id              SERIAL PRIMARY KEY,
    project_id      INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    inviter_user_id INTEGER NOT NULL REFERENCES users(id),
    invite_token    VARCHAR(64) UNIQUE NOT NULL,
    telegram_id     BIGINT,         -- если родственник уже в боте
    status          VARCHAR(20) DEFAULT 'pending',  -- pending | accepted | declined
    hero_id         INTEGER REFERENCES heroes(id),
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_invitations_token ON invitations(invite_token);
CREATE INDEX IF NOT EXISTS idx_invitations_telegram ON invitations(telegram_id);

-- Связь voice_messages и photos с проектом/героем (для контекста)
ALTER TABLE voice_messages ADD COLUMN IF NOT EXISTS project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL;
ALTER TABLE voice_messages ADD COLUMN IF NOT EXISTS hero_id INTEGER REFERENCES heroes(id) ON DELETE SET NULL;
ALTER TABLE voice_messages ADD COLUMN IF NOT EXISTS question_index INTEGER;
ALTER TABLE photos ADD COLUMN IF NOT EXISTS project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL;
ALTER TABLE photos ADD COLUMN IF NOT EXISTS hero_id INTEGER REFERENCES heroes(id) ON DELETE SET NULL;
