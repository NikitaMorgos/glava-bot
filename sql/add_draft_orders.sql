-- DraftOrder: черновик заказа до оплаты (ТЗ Pre-pay flow)
-- Запуск: psql -d your_db -f sql/add_draft_orders.sql

CREATE TYPE draft_order_status AS ENUM (
    'draft',
    'payment_pending',
    'paid',
    'cancelled',
    'expired'
);

CREATE TABLE IF NOT EXISTS draft_orders (
    id                  SERIAL PRIMARY KEY,
    user_id             INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status              draft_order_status NOT NULL DEFAULT 'draft',
    email               VARCHAR(255),
    characters          JSONB NOT NULL DEFAULT '[]',
    total_price         INTEGER NOT NULL DEFAULT 0,
    currency            VARCHAR(10) NOT NULL DEFAULT 'RUB',
    payment_provider    VARCHAR(50),
    payment_id          VARCHAR(255),
    payment_url         TEXT,
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Только один активный draft на пользователя (draft или payment_pending)
CREATE UNIQUE INDEX IF NOT EXISTS idx_draft_orders_user_active
    ON draft_orders (user_id)
    WHERE status IN ('draft', 'payment_pending');

CREATE INDEX IF NOT EXISTS idx_draft_orders_user_id ON draft_orders(user_id);
CREATE INDEX IF NOT EXISTS idx_draft_orders_status ON draft_orders(status);
