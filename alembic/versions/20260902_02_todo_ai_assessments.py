"""Add user-scoped AI TODO assessments.

Revision ID: 20260902_02
Revises: 20260902_01
Create Date: 2026-09-02
"""
from typing import Sequence, Union

from alembic import op


revision: str = "20260902_02"
down_revision: Union[str, Sequence[str], None] = "20260902_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS todo_ai_assessments (
            id BIGSERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            todo_id INTEGER NOT NULL REFERENCES todos(id) ON DELETE CASCADE,
            content_fingerprint CHAR(64) NOT NULL,
            classification VARCHAR(32) NOT NULL CHECK (classification IN (
                'FULLY_AI_ACTIONABLE', 'PARTIALLY_AI_ACTIONABLE', 'HUMAN_REQUIRED'
            )),
            confidence SMALLINT NOT NULL CHECK (confidence BETWEEN 0 AND 100),
            reason VARCHAR(600) NOT NULL,
            ai_steps JSONB NOT NULL DEFAULT '[]'::jsonb,
            human_steps JSONB NOT NULL DEFAULT '[]'::jsonb,
            missing_information JSONB NOT NULL DEFAULT '[]'::jsonb,
            supported_actions JSONB NOT NULL DEFAULT '[]'::jsonb,
            assessment_source VARCHAR(12) NOT NULL CHECK (assessment_source IN ('AI', 'RULES')),
            model_name VARCHAR(80),
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (user_id, todo_id)
        );

        CREATE INDEX IF NOT EXISTS todo_ai_assessments_user_idx
            ON todo_ai_assessments(user_id, classification, updated_at DESC);
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS todo_ai_assessments")
