CREATE TABLE IF NOT EXISTS bank_connections (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR(30) NOT NULL DEFAULT 'ENABLE_BANKING',
    institution_name VARCHAR(200) NOT NULL,
    institution_country VARCHAR(2) NOT NULL CHECK (institution_country IN ('DE', 'HU')),
    psu_type VARCHAR(10) NOT NULL DEFAULT 'personal' CHECK (psu_type IN ('personal', 'business')),
    authorization_id VARCHAR(100),
    provider_session_id TEXT,
    state_hash VARCHAR(64) NOT NULL UNIQUE,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING', 'AUTHORIZED', 'EXPIRED', 'ERROR', 'DISCONNECTED')),
    consent_valid_until TIMESTAMPTZ,
    last_synced_at TIMESTAMPTZ,
    last_error VARCHAR(500),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS bank_connections_user_idx ON bank_connections(user_id, status);

CREATE TABLE IF NOT EXISTS bank_accounts (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    connection_id BIGINT NOT NULL REFERENCES bank_connections(id) ON DELETE CASCADE,
    provider_account_id UUID NOT NULL,
    identification_hash VARCHAR(500) NOT NULL,
    account_name VARCHAR(200),
    bank_name VARCHAR(200),
    iban_last4 VARCHAR(4),
    currency VARCHAR(3) NOT NULL,
    current_balance NUMERIC(16,2),
    balance_updated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, provider_account_id)
);

CREATE INDEX IF NOT EXISTS bank_accounts_connection_idx ON bank_accounts(user_id, connection_id);

CREATE TABLE IF NOT EXISTS bank_transactions (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    bank_account_id BIGINT NOT NULL REFERENCES bank_accounts(id) ON DELETE CASCADE,
    provider_fingerprint VARCHAR(64) NOT NULL,
    entry_reference VARCHAR(300),
    direction VARCHAR(10) NOT NULL CHECK (direction IN ('DEBIT', 'CREDIT')),
    booking_status VARCHAR(10) NOT NULL CHECK (booking_status IN ('BOOKED', 'PENDING')),
    amount NUMERIC(16,2) NOT NULL CHECK (amount >= 0),
    currency VARCHAR(3) NOT NULL,
    booking_date DATE NOT NULL,
    merchant_name VARCHAR(300),
    description VARCHAR(1000),
    merchant_category_code VARCHAR(10),
    suggested_category_id INTEGER REFERENCES expense_categories(id),
    import_status VARCHAR(10) NOT NULL DEFAULT 'PENDING'
        CHECK (import_status IN ('PENDING', 'IMPORTED', 'IGNORED')),
    expense_id INTEGER REFERENCES expenses(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, bank_account_id, provider_fingerprint)
);

CREATE INDEX IF NOT EXISTS bank_transactions_inbox_idx
    ON bank_transactions(user_id, import_status, direction, booking_date DESC);
