CREATE TABLE IF NOT EXISTS businesses (
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
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, legal_name),
    UNIQUE (user_id, id)
);

CREATE TABLE IF NOT EXISTS clients (
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

CREATE INDEX IF NOT EXISTS clients_user_business_idx ON clients(user_id, business_id);
CREATE INDEX IF NOT EXISTS clients_user_segment_idx ON clients(user_id, segment);

CREATE TABLE IF NOT EXISTS invoices (
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

CREATE INDEX IF NOT EXISTS invoices_user_business_idx ON invoices(user_id, business_id);
CREATE INDEX IF NOT EXISTS invoices_user_status_idx ON invoices(user_id, status);
CREATE INDEX IF NOT EXISTS invoices_due_date_idx ON invoices(user_id, due_date);

CREATE TABLE IF NOT EXISTS invoice_items (
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

CREATE TABLE IF NOT EXISTS invoice_payments (
    id BIGSERIAL PRIMARY KEY,
    invoice_id BIGINT NOT NULL REFERENCES invoices(id) ON DELETE RESTRICT,
    amount NUMERIC(14,2) NOT NULL CHECK (amount > 0),
    payment_date DATE NOT NULL,
    payment_method VARCHAR(30) NOT NULL DEFAULT 'BANK_TRANSFER',
    reference VARCHAR(120),
    notes VARCHAR(500),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS invoice_payments_invoice_idx ON invoice_payments(invoice_id);
