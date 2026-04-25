-- ==============================================================================
-- Migración V2: Categorías, Comprobantes, División Proporcional y Múltiples Pagos
-- ==============================================================================

-- 1. Se agrega el coeficiente a los miembros para la división proporcional
ALTER TABLE group_members 
ADD COLUMN IF NOT EXISTS coefficient NUMERIC(5,4) DEFAULT 0.0000;

-- 2. Se enriquece la tabla de gastos (HU-08 y HU-13)
ALTER TABLE expenses 
ADD COLUMN IF NOT EXISTS category VARCHAR(50) DEFAULT 'Otros',
ADD COLUMN IF NOT EXISTS receipt_url TEXT,
ADD COLUMN IF NOT EXISTS expense_date DATE DEFAULT CURRENT_DATE,
ADD COLUMN IF NOT EXISTS division_type VARCHAR(20) DEFAULT 'EQUALLY';

-- OJO: Se permite que 'paid_by_user_id' sea NULL temporalmente 
-- para facilitar la transición hacia los pagos múltiples.
ALTER TABLE expenses ALTER COLUMN paid_by_user_id DROP NOT NULL;

-- 3. Se crea tabla para registrar MÚLTIPLES pagos (quiénes pusieron la plata)
CREATE TABLE IF NOT EXISTS expense_payments (
  id                 SERIAL PRIMARY KEY,
  expense_id         INTEGER NOT NULL REFERENCES expenses(id) ON DELETE CASCADE,
  user_id            INTEGER NOT NULL REFERENCES users(id),
  amount_paid        NUMERIC(12,2) NOT NULL CHECK (amount_paid > 0),
  UNIQUE(expense_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_expense_payments_expense_id ON expense_payments(expense_id);

-- 4. Se migran los datos viejos a la nueva tabla
-- Esto agarra todos los gastos que ya existen y mete a su 'paid_by_user_id' en la nueva tabla 'expense_payments'
INSERT INTO expense_payments (expense_id, user_id, amount_paid)
SELECT id, paid_by_user_id, amount
FROM expenses
WHERE paid_by_user_id IS NOT NULL
ON CONFLICT (expense_id, user_id) DO NOTHING;