BEGIN;

ALTER TABLE recurring_expenses
    DROP CONSTRAINT IF EXISTS recurring_expenses_cancellation_difficulty_check,
    DROP CONSTRAINT IF EXISTS recurring_expenses_cancellation_date_relevance_check;

ALTER TABLE recurring_expenses
    ADD CONSTRAINT recurring_expenses_cancellation_difficulty_check
        CHECK (cancellation_difficulty IN ('EASY', 'NOTICE_REQUIRED', 'CONTRACT_LOCKED', 'NON_CANCELLABLE', 'ESSENTIAL')),
    ADD CONSTRAINT recurring_expenses_cancellation_date_relevance_check
        CHECK (
            cancellable_from IS NULL
            OR cancellation_difficulty IN ('NOTICE_REQUIRED', 'CONTRACT_LOCKED')
        );

COMMIT;
