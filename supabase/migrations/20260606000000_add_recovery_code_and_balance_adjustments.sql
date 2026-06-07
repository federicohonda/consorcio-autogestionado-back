ALTER TABLE users ADD COLUMN IF NOT EXISTS recovery_code VARCHAR(6);

CREATE TABLE IF NOT EXISTS balance_adjustments (
    id          SERIAL PRIMARY KEY,
    group_id    INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    amount      NUMERIC(12,2) NOT NULL,
    description TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_balance_adjustments_group_user
    ON balance_adjustments(group_id, user_id);
