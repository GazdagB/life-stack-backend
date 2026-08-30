BEGIN;

ALTER TABLE todos
    ADD COLUMN IF NOT EXISTS user_id INTEGER;

DO $$
DECLARE
    account_count INTEGER;
    only_user_id INTEGER;
BEGIN
    IF EXISTS (SELECT 1 FROM todos WHERE user_id IS NULL) THEN
        SELECT COUNT(*), MIN(id) INTO account_count, only_user_id FROM users;
        IF account_count <> 1 THEN
            RAISE EXCEPTION
                'Cannot assign legacy todos automatically: expected one user, found %',
                account_count;
        END IF;
        UPDATE todos SET user_id = only_user_id WHERE user_id IS NULL;
    END IF;
END $$;

ALTER TABLE todos
    ALTER COLUMN user_id SET NOT NULL;

ALTER TABLE todos
    DROP CONSTRAINT IF EXISTS todos_user_id_fkey,
    ADD CONSTRAINT todos_user_id_fkey
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

COMMIT;
