BEGIN;

ALTER TABLE recurring_expenses
    ADD COLUMN IF NOT EXISTS cancellation_difficulty VARCHAR(20) NOT NULL DEFAULT 'EASY',
    ADD COLUMN IF NOT EXISTS cancellable_from DATE,
    ADD COLUMN IF NOT EXISTS cancellation_notes VARCHAR(280);

ALTER TABLE recurring_expenses
    DROP CONSTRAINT IF EXISTS recurring_expenses_cancellation_difficulty_check,
    DROP CONSTRAINT IF EXISTS recurring_expenses_cancellable_from_check;

ALTER TABLE recurring_expenses
    ADD CONSTRAINT recurring_expenses_cancellation_difficulty_check
        CHECK (cancellation_difficulty IN ('EASY', 'NOTICE_REQUIRED', 'CONTRACT_LOCKED', 'ESSENTIAL')),
    ADD CONSTRAINT recurring_expenses_cancellable_from_check
        CHECK (cancellable_from IS NULL OR cancellable_from >= start_date);

COMMIT;
