"""Baseline the current LifeOS schema.

Revision ID: 20260901_01
Revises:
Create Date: 2026-09-01
"""
from pathlib import Path
from typing import Sequence, Union

from alembic import op


revision: str = "20260901_01"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    schema_path = Path(__file__).resolve().parents[2] / "app" / "database" / "schema.sql"
    schema_sql = schema_path.read_text(encoding="utf-8")
    if "DROP TABLE" in schema_sql.upper() or "DROP TYPE" in schema_sql.upper():
        raise RuntimeError("Refusing to apply a destructive baseline schema")
    op.execute(schema_sql)


def downgrade() -> None:
    raise RuntimeError(
        "The baseline downgrade is intentionally disabled because it would destroy LifeOS data"
    )
