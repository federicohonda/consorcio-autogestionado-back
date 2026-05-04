-- Deudas de aporte mensual por miembro (no son "gastos", no aparecen en la lista de gastos)
CREATE TABLE IF NOT EXISTS contribution_debts (
    id          SERIAL PRIMARY KEY,
    group_id    INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    amount      NUMERIC(12,2) NOT NULL CHECK (amount > 0),
    month_year  INTEGER NOT NULL, -- YYYYMM del mes al que corresponde
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(group_id, user_id, month_year)
);

CREATE INDEX IF NOT EXISTS idx_contribution_debts_group_user
    ON contribution_debts(group_id, user_id);
