ALTER TABLE businesses
    ADD COLUMN IF NOT EXISTS invoice_template VARCHAR(20) NOT NULL DEFAULT 'MODERN'
        CHECK (invoice_template IN ('MODERN', 'CLASSIC')),
    ADD COLUMN IF NOT EXISTS invoice_thank_you VARCHAR(300);

CREATE TABLE IF NOT EXISTS business_signature_assets (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    signature_data BYTEA NOT NULL,
    signature_content_type VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE businesses
    ADD COLUMN IF NOT EXISTS signature_asset_id BIGINT REFERENCES business_signature_assets(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS business_signature_assets_business_idx
    ON business_signature_assets(user_id, business_id);
