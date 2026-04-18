CREATE TABLE IF NOT EXISTS expenses (
  id                 SERIAL PRIMARY KEY,
  group_id           INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
  description        VARCHAR(200) NOT NULL,
  amount             NUMERIC(12,2) NOT NULL CHECK (amount > 0),
  paid_by_user_id    INTEGER NOT NULL REFERENCES users(id),
  created_by_user_id INTEGER NOT NULL REFERENCES users(id),
  created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS expense_splits (
  id         SERIAL PRIMARY KEY,
  expense_id INTEGER NOT NULL REFERENCES expenses(id) ON DELETE CASCADE,
  user_id    INTEGER NOT NULL REFERENCES users(id),
  amount     NUMERIC(12,2) NOT NULL,
  UNIQUE(expense_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_expenses_group_id ON expenses(group_id);
