"""Add guided AI TODO work sessions and messages.

Revision ID: 20260902_03
Revises: 20260902_02
Create Date: 2026-09-02
"""
from typing import Sequence, Union

from alembic import op


revision: str = "20260902_03"
down_revision: Union[str, Sequence[str], None] = "20260902_02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS todo_ai_work_sessions (
            id BIGSERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            todo_id INTEGER NOT NULL REFERENCES todos(id) ON DELETE CASCADE,
            content_fingerprint CHAR(64) NOT NULL,
            phase VARCHAR(24) NOT NULL DEFAULT 'GATHERING_INFORMATION'
                CHECK (phase IN ('GATHERING_INFORMATION', 'WORKING', 'DRAFT_READY')),
            questions JSONB NOT NULL DEFAULT '[]'::jsonb,
            human_steps JSONB NOT NULL DEFAULT '[]'::jsonb,
            deliverable_title VARCHAR(240),
            deliverable_content TEXT,
            model_name VARCHAR(80),
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (user_id, todo_id)
        );

        CREATE TABLE IF NOT EXISTS todo_ai_work_messages (
            id BIGSERIAL PRIMARY KEY,
            session_id BIGINT NOT NULL REFERENCES todo_ai_work_sessions(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            role VARCHAR(12) NOT NULL CHECK (role IN ('USER', 'ASSISTANT')),
            content VARCHAR(6000) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS todo_ai_work_messages_session_idx
            ON todo_ai_work_messages(session_id, id);
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS todo_ai_work_messages")
    op.execute("DROP TABLE IF EXISTS todo_ai_work_sessions")
