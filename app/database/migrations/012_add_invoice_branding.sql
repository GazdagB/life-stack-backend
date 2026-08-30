ALTER TABLE businesses
    ADD COLUMN IF NOT EXISTS website VARCHAR(254),
    ADD COLUMN IF NOT EXISTS invoice_accent_color VARCHAR(7) NOT NULL DEFAULT '#2563EB',
    ADD COLUMN IF NOT EXISTS invoice_footer VARCHAR(500);

CREATE TABLE IF NOT EXISTS business_brand_assets (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    logo_data BYTEA NOT NULL,
    logo_content_type VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE businesses
    ADD COLUMN IF NOT EXISTS logo_asset_id BIGINT REFERENCES business_brand_assets(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS business_brand_assets_business_idx
    ON business_brand_assets(user_id, business_id);
