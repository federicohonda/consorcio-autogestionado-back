-- Configuración del Pozo y mes activo por grupo
CREATE TABLE IF NOT EXISTS group_settings (
    group_id             INTEGER PRIMARY KEY REFERENCES groups(id) ON DELETE CASCADE,
    active_month         INTEGER NOT NULL,   -- formato YYYYMM, ej: 202605
    monthly_contribution NUMERIC(12,2) NOT NULL DEFAULT 0,
    pozo_balance         NUMERIC(12,2) NOT NULL DEFAULT 0,
    updated_at           TIMESTAMPTZ DEFAULT NOW()
);

-- Historial de movimientos del Pozo
CREATE TABLE IF NOT EXISTS pozo_movements (
    id          SERIAL PRIMARY KEY,
    group_id    INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    type        VARCHAR(30) NOT NULL, -- PAYMENT_INCOME | EXPENSE_DEDUCTION | MONTH_DISTRIBUTION
    amount      NUMERIC(12,2) NOT NULL,
    description TEXT,
    user_id     INTEGER REFERENCES users(id),
    expense_id  INTEGER REFERENCES expenses(id),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pozo_movements_group ON pozo_movements(group_id, created_at DESC);

-- Distribuciones del Pozo a miembros al avanzar mes
CREATE TABLE IF NOT EXISTS pozo_distributions (
    id         SERIAL PRIMARY KEY,
    group_id   INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    user_id    INTEGER NOT NULL REFERENCES users(id),
    amount     NUMERIC(12,2) NOT NULL CHECK (amount > 0),
    month_year INTEGER NOT NULL, -- YYYYMM del mes que se cierra
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pozo_distributions_group_user ON pozo_distributions(group_id, user_id);

-- Marcar gastos pagados con el Pozo
ALTER TABLE expenses ADD COLUMN IF NOT EXISTS paid_by_pozo BOOLEAN NOT NULL DEFAULT FALSE;

-- Inicializar group_settings para grupos existentes
INSERT INTO group_settings (group_id, active_month, monthly_contribution, pozo_balance)
SELECT
    id,
    EXTRACT(YEAR FROM NOW())::int * 100 + EXTRACT(MONTH FROM NOW())::int,
    0,
    0
FROM groups
ON CONFLICT (group_id) DO NOTHING;

-- Trigger para inicializar group_settings en nuevos grupos
CREATE OR REPLACE FUNCTION init_group_settings() RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO group_settings (group_id, active_month, monthly_contribution, pozo_balance)
    VALUES (
        NEW.id,
        EXTRACT(YEAR FROM NOW())::int * 100 + EXTRACT(MONTH FROM NOW())::int,
        0,
        0
    )
    ON CONFLICT (group_id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_init_group_settings ON groups;
CREATE TRIGGER trg_init_group_settings
    AFTER INSERT ON groups
    FOR EACH ROW EXECUTE FUNCTION init_group_settings();
