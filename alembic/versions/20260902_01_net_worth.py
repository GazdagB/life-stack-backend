"""Add user-scoped net worth items and valuation snapshots.

Revision ID: 20260902_01
Revises: 20260901_01
Create Date: 2026-09-02
"""
from typing import Sequence, Union

from alembic import op


revision: str = "20260902_01"
down_revision: Union[str, Sequence[str], None] = "20260901_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS net_worth_items (
            id BIGSERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(120) NOT NULL,
            kind VARCHAR(12) NOT NULL CHECK (kind IN ('ASSET', 'LIABILITY')),
            category VARCHAR(20) NOT NULL CHECK (category IN (
                'CASH', 'BANK', 'INVESTMENT', 'PROPERTY', 'VEHICLE',
                'BUSINESS', 'LOAN', 'CREDIT_CARD', 'OTHER'
            )),
            current_value NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (current_value >= 0),
            currency VARCHAR(3) NOT NULL DEFAULT 'EUR',
            ownership_percent NUMERIC(5,2) NOT NULL DEFAULT 100
                CHECK (ownership_percent > 0 AND ownership_percent <= 100),
            linked_bank_account_id BIGINT REFERENCES bank_accounts(id) ON DELETE SET NULL,
            notes VARCHAR(500),
            active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (user_id, linked_bank_account_id)
        );

        CREATE INDEX IF NOT EXISTS net_worth_items_user_idx
            ON net_worth_items(user_id, active, kind, currency);

        CREATE TABLE IF NOT EXISTS net_worth_snapshots (
            id BIGSERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            item_id BIGINT NOT NULL REFERENCES net_worth_items(id) ON DELETE CASCADE,
            value NUMERIC(18,2) NOT NULL CHECK (value >= 0),
            currency VARCHAR(3) NOT NULL,
            kind VARCHAR(12) NOT NULL CHECK (kind IN ('ASSET', 'LIABILITY')),
            ownership_percent NUMERIC(5,2) NOT NULL
                CHECK (ownership_percent > 0 AND ownership_percent <= 100),
            recorded_on DATE NOT NULL,
            source VARCHAR(12) NOT NULL DEFAULT 'MANUAL'
                CHECK (source IN ('MANUAL', 'BANK_SYNC')),
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (item_id, recorded_on)
        );

        CREATE INDEX IF NOT EXISTS net_worth_snapshots_user_date_idx
            ON net_worth_snapshots(user_id, recorded_on DESC);
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS net_worth_snapshots")
    op.execute("DROP TABLE IF EXISTS net_worth_items")
