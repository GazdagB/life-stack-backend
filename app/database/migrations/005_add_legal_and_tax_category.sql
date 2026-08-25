BEGIN;

INSERT INTO expense_categories (name)
VALUES ('Legal & Tax')
ON CONFLICT (name) DO NOTHING;

COMMIT;
