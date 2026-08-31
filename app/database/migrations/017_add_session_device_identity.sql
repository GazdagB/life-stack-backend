BEGIN;

ALTER TABLE refresh_sessions
    ADD COLUMN IF NOT EXISTS device_hash VARCHAR(64);

CREATE UNIQUE INDEX IF NOT EXISTS refresh_sessions_active_device_idx
    ON refresh_sessions(user_id, device_hash)
    WHERE revoked_at IS NULL AND device_hash IS NOT NULL;

COMMIT;
