-- Datos bancarios del consorcio (alias, CBU, titular) para mostrar en pantalla de pago
ALTER TABLE groups
    ADD COLUMN IF NOT EXISTS bank_alias        VARCHAR(100),
    ADD COLUMN IF NOT EXISTS bank_cbu          VARCHAR(22),
    ADD COLUMN IF NOT EXISTS bank_account_name VARCHAR(100);

-- Pagos que los propietarios realizan al consorcio
CREATE TABLE IF NOT EXISTS owner_payments (
    id           SERIAL PRIMARY KEY,
    group_id     INTEGER NOT NULL REFERENCES groups(id)  ON DELETE CASCADE,
    user_id      INTEGER NOT NULL REFERENCES users(id)   ON DELETE CASCADE,
    amount       DECIMAL(10, 2) NOT NULL CHECK (amount > 0),
    payment_date DATE NOT NULL DEFAULT CURRENT_DATE,
    receipt_url  VARCHAR(255) NOT NULL,
    notes        TEXT,
    created_at   TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_owner_payments_group_user
    ON owner_payments (group_id, user_id);
