BEGIN;

CREATE TABLE IF NOT EXISTS auth_rate_limits (
    scope VARCHAR(20) NOT NULL,
    key_hash VARCHAR(64) NOT NULL,
    attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    window_started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (scope, key_hash)
);

CREATE INDEX IF NOT EXISTS auth_rate_limits_window_idx
    ON auth_rate_limits(window_started_at);

COMMIT;
