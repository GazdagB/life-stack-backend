BEGIN;

INSERT INTO expense_categories (name)
VALUES ('Insurance')
ON CONFLICT (name) DO NOTHING;

COMMIT;
