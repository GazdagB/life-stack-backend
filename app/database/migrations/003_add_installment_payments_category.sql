BEGIN;

INSERT INTO expense_categories (name)
VALUES ('Installment Payments')
ON CONFLICT (name) DO NOTHING;

COMMIT;
