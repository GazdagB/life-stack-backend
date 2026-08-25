BEGIN;

CREATE TABLE IF NOT EXISTS recurring_expenses (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category_id INTEGER REFERENCES expense_categories(id),
    title VARCHAR(120) NOT NULL,
    amount NUMERIC(10,2) NOT NULL CHECK (amount > 0),
    frequency occurrence NOT NULL CHECK (frequency <> 'NONE'),
    start_date DATE NOT NULL,
    end_date DATE,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (end_date IS NULL OR end_date >= start_date)
);

CREATE INDEX IF NOT EXISTS recurring_expenses_user_id_idx
    ON recurring_expenses(user_id);

COMMIT;
