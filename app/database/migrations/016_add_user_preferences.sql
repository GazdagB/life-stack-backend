BEGIN;

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS preferred_language VARCHAR(2) NOT NULL DEFAULT 'en';

ALTER TABLE users
    DROP CONSTRAINT IF EXISTS users_preferred_language_check,
    ADD CONSTRAINT users_preferred_language_check
        CHECK (preferred_language IN ('en', 'de', 'hu'));

COMMIT;
