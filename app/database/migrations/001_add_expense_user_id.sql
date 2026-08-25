BEGIN;

ALTER TABLE expenses
    ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id);

-- The legacy rows come from seed.sql, where they belong to the initial user.
UPDATE expenses
SET user_id = 1
WHERE user_id IS NULL;

ALTER TABLE expenses
    ALTER COLUMN user_id SET NOT NULL;

CREATE INDEX IF NOT EXISTS expenses_user_id_idx ON expenses(user_id);

COMMIT;
