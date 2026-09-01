-- Canonical schema for a brand-new database.
-- This file is intentionally non-destructive and is applied by Alembic's
-- baseline migration. Existing databases must be stamped, never recreated.
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(20) NOT NULL UNIQUE,
    email VARCHAR(50) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    display_name VARCHAR(80),
    bio VARCHAR(280),
    avatar_data BYTEA,
    avatar_content_type VARCHAR(50),
    preferred_language VARCHAR(2) NOT NULL DEFAULT 'en'
        CHECK (preferred_language IN ('en', 'de', 'hu')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE refresh_sessions (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    family_id UUID NOT NULL,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    last_used_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMPTZ,
    user_agent VARCHAR(500),
    device_hash VARCHAR(64)
);

CREATE INDEX refresh_sessions_user_id_idx ON refresh_sessions(user_id);
CREATE INDEX refresh_sessions_family_id_idx ON refresh_sessions(family_id);
CREATE UNIQUE INDEX refresh_sessions_active_device_idx
    ON refresh_sessions(user_id, device_hash)
    WHERE revoked_at IS NULL AND device_hash IS NOT NULL;

CREATE TABLE auth_rate_limits (
    scope VARCHAR(20) NOT NULL,
    key_hash VARCHAR(64) NOT NULL,
    attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    window_started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (scope, key_hash)
);

CREATE INDEX auth_rate_limits_window_idx ON auth_rate_limits(window_started_at);


CREATE TYPE occurrence AS ENUM (
    'NONE',
    'DAILY',
    'WEEKLY',
    'MONTHLY',
    'YEARLY'
);

CREATE TABLE expense_categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
);

INSERT INTO expense_categories (name)
VALUES ('Housing'),
       ('Utilities'),
       ('Groceries'),
       ('Dining Out'),
       ('Transportation'),
       ('Healthcare'),
       ('Subscriptions'),
       ('Entertainment'),
       ('Shopping'),
       ('Other'),
       ('Installment Payments'),
       ('Insurance'),
       ('Legal & Tax')
ON CONFLICT (name) DO NOTHING;

CREATE TABLE expenses (
    id SERIAL PRIMARY KEY,
    category_id INTEGER REFERENCES expense_categories(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    title VARCHAR(30) NOT NULL,
    amount NUMERIC(10,2) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expense_date DATE NOT NULL,
    recurrence occurrence NOT NULL DEFAULT 'NONE'
);

CREATE TABLE bank_connections (
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

CREATE INDEX bank_connections_user_idx ON bank_connections(user_id, status);

CREATE TABLE bank_accounts (
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

CREATE INDEX bank_accounts_connection_idx ON bank_accounts(user_id, connection_id);

CREATE TABLE bank_transactions (
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

CREATE INDEX bank_transactions_inbox_idx
    ON bank_transactions(user_id, import_status, direction, booking_date DESC);

CREATE TABLE recurring_expenses (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category_id INTEGER REFERENCES expense_categories(id),
    title VARCHAR(120) NOT NULL,
    amount NUMERIC(10,2) NOT NULL CHECK (amount > 0),
    frequency occurrence NOT NULL CHECK (frequency <> 'NONE'),
    start_date DATE NOT NULL,
    end_date DATE,
    cancellation_difficulty VARCHAR(20) NOT NULL DEFAULT 'EASY'
        CHECK (cancellation_difficulty IN ('EASY', 'NOTICE_REQUIRED', 'CONTRACT_LOCKED', 'NON_CANCELLABLE', 'ESSENTIAL')),
    cancellable_from DATE,
    cancellation_notes VARCHAR(280),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (end_date IS NULL OR end_date >= start_date),
    CHECK (cancellable_from IS NULL OR cancellable_from >= start_date),
    CHECK (cancellable_from IS NULL OR cancellation_difficulty IN ('NOTICE_REQUIRED', 'CONTRACT_LOCKED'))
);

CREATE TABLE todos (
    id SERIAL PRIMARY KEY,
    title VARCHAR(120) NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    description TEXT,
    priority VARCHAR(2) NOT NULL DEFAULT 'P3',
    status VARCHAR(20) NOT NULL default 'not_started',
    due_date DATE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    sort_order INTEGER DEFAULT 0,
    source VARCHAR(50) DEFAULT 'manual'
);

CREATE TABLE user_movies (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    imdb_id VARCHAR(20) NOT NULL,
    title VARCHAR(300) NOT NULL,
    year VARCHAR(20),
    poster_url TEXT,
    plot TEXT,
    director TEXT,
    actors TEXT,
    genre TEXT,
    runtime VARCHAR(40),
    content_rating VARCHAR(30),
    released VARCHAR(40),
    awards TEXT,
    country TEXT,
    language TEXT,
    box_office VARCHAR(80),
    external_ratings JSONB NOT NULL DEFAULT '[]'::jsonb,
    list_status VARCHAR(20) NOT NULL DEFAULT 'WANT_TO_WATCH'
        CHECK (list_status IN ('WANT_TO_WATCH', 'WATCHED')),
    personal_rating NUMERIC(3,1)
        CHECK (personal_rating IS NULL OR (personal_rating >= 1 AND personal_rating <= 10)),
    critique VARCHAR(2000),
    watched_at DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, imdb_id),
    CHECK (list_status = 'WATCHED' OR (personal_rating IS NULL AND watched_at IS NULL))
);

CREATE INDEX user_movies_user_status_idx ON user_movies(user_id, list_status);

CREATE TABLE businesses (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    legal_name VARCHAR(200) NOT NULL,
    jurisdiction VARCHAR(2) NOT NULL CHECK (jurisdiction IN ('DE', 'HU')),
    tax_number VARCHAR(60),
    vat_id VARCHAR(40),
    registration_number VARCHAR(80),
    address_line1 VARCHAR(200),
    address_line2 VARCHAR(200),
    postal_code VARCHAR(20),
    city VARCHAR(120),
    country_code VARCHAR(2) NOT NULL,
    email VARCHAR(254),
    phone VARCHAR(50),
    website VARCHAR(254),
    bank_name VARCHAR(120),
    iban VARCHAR(50),
    bic VARCHAR(20),
    default_currency VARCHAR(3) NOT NULL CHECK (default_currency IN ('EUR', 'HUF')),
    default_language VARCHAR(2) NOT NULL CHECK (default_language IN ('DE', 'HU', 'EN')),
    invoice_prefix VARCHAR(20) NOT NULL DEFAULT '',
    next_invoice_number INTEGER NOT NULL DEFAULT 1 CHECK (next_invoice_number > 0),
    invoice_number_year INTEGER NOT NULL DEFAULT 0,
    default_payment_terms_days INTEGER NOT NULL DEFAULT 14 CHECK (default_payment_terms_days BETWEEN 0 AND 365),
    tax_exemption_note VARCHAR(300),
    invoice_accent_color VARCHAR(7) NOT NULL DEFAULT '#2563EB',
    invoice_footer VARCHAR(500),
    invoice_template VARCHAR(20) NOT NULL DEFAULT 'MODERN' CHECK (invoice_template IN ('MODERN', 'CLASSIC')),
    invoice_thank_you VARCHAR(300),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, legal_name),
    UNIQUE (user_id, id)
);

CREATE TABLE business_brand_assets (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    logo_data BYTEA NOT NULL,
    logo_content_type VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE businesses
    ADD COLUMN logo_asset_id BIGINT REFERENCES business_brand_assets(id) ON DELETE SET NULL;

CREATE INDEX business_brand_assets_business_idx ON business_brand_assets(user_id, business_id);

CREATE TABLE business_signature_assets (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    signature_data BYTEA NOT NULL,
    signature_content_type VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE businesses
    ADD COLUMN signature_asset_id BIGINT REFERENCES business_signature_assets(id) ON DELETE SET NULL;

CREATE INDEX business_signature_assets_business_idx ON business_signature_assets(user_id, business_id);

CREATE TABLE clients (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE RESTRICT,
    name VARCHAR(200) NOT NULL,
    client_type VARCHAR(20) NOT NULL DEFAULT 'BUSINESS'
        CHECK (client_type IN ('BUSINESS', 'PRIVATE')),
    segment VARCHAR(80) NOT NULL,
    contact_name VARCHAR(160),
    email VARCHAR(254),
    phone VARCHAR(50),
    tax_number VARCHAR(60),
    vat_id VARCHAR(40),
    address_line1 VARCHAR(200),
    address_line2 VARCHAR(200),
    postal_code VARCHAR(20),
    city VARCHAR(120),
    country_code VARCHAR(2) NOT NULL,
    notes VARCHAR(1000),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX clients_user_business_idx ON clients(user_id, business_id);
CREATE INDEX clients_user_segment_idx ON clients(user_id, segment);

CREATE TABLE invoices (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE RESTRICT,
    client_id BIGINT NOT NULL REFERENCES clients(id) ON DELETE RESTRICT,
    original_invoice_id BIGINT REFERENCES invoices(id) ON DELETE RESTRICT,
    invoice_type VARCHAR(20) NOT NULL DEFAULT 'INVOICE'
        CHECK (invoice_type IN ('INVOICE', 'CREDIT_NOTE')),
    invoice_number VARCHAR(80),
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT'
        CHECK (status IN ('DRAFT', 'ISSUED', 'PARTIALLY_PAID', 'PAID', 'CREDITED', 'CANCELLED')),
    compliance_status VARCHAR(20) NOT NULL DEFAULT 'NOT_READY'
        CHECK (compliance_status IN ('NOT_READY', 'NOT_REQUIRED', 'PENDING', 'SUBMITTED', 'ACCEPTED', 'REJECTED')),
    currency VARCHAR(3) NOT NULL CHECK (currency IN ('EUR', 'HUF')),
    language VARCHAR(2) NOT NULL CHECK (language IN ('DE', 'HU', 'EN')),
    issue_date DATE NOT NULL,
    service_date DATE NOT NULL,
    due_date DATE NOT NULL,
    notes VARCHAR(2000),
    correction_reason VARCHAR(500),
    seller_snapshot JSONB,
    client_snapshot JSONB,
    subtotal NUMERIC(14,2) NOT NULL DEFAULT 0,
    tax_total NUMERIC(14,2) NOT NULL DEFAULT 0,
    total NUMERIC(14,2) NOT NULL DEFAULT 0,
    issued_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (business_id, invoice_number)
);

CREATE INDEX invoices_user_business_idx ON invoices(user_id, business_id);
CREATE INDEX invoices_user_status_idx ON invoices(user_id, status);
CREATE INDEX invoices_due_date_idx ON invoices(user_id, due_date);

CREATE TABLE invoice_items (
    id BIGSERIAL PRIMARY KEY,
    invoice_id BIGINT NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    description VARCHAR(500) NOT NULL,
    quantity NUMERIC(14,3) NOT NULL CHECK (quantity > 0),
    unit VARCHAR(30) NOT NULL DEFAULT 'item',
    unit_price NUMERIC(14,2) NOT NULL,
    tax_rate NUMERIC(5,2) NOT NULL CHECK (tax_rate BETWEEN 0 AND 100),
    net_total NUMERIC(14,2) NOT NULL,
    tax_total NUMERIC(14,2) NOT NULL,
    gross_total NUMERIC(14,2) NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE invoice_payments (
    id BIGSERIAL PRIMARY KEY,
    invoice_id BIGINT NOT NULL REFERENCES invoices(id) ON DELETE RESTRICT,
    amount NUMERIC(14,2) NOT NULL CHECK (amount > 0),
    payment_date DATE NOT NULL,
    payment_method VARCHAR(30) NOT NULL DEFAULT 'BANK_TRANSFER',
    reference VARCHAR(120),
    notes VARCHAR(500),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX invoice_payments_invoice_idx ON invoice_payments(invoice_id);
