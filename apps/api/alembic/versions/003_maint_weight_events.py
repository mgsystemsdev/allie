"""Add maintenance + weight one-shot alert settings.

Revision ID: 003_maint_weight_events
Revises: 002_settings_email
Create Date: 2026-08-07
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_maint_weight_events"
down_revision: Union[str, None] = "002_settings_email"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "app_settings",
        sa.Column("event_maint_water", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.add_column(
        "app_settings",
        sa.Column("event_maint_substrate", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.add_column(
        "app_settings",
        sa.Column("event_maint_deep_clean", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.add_column(
        "app_settings",
        sa.Column("event_weight_due", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.add_column(
        "app_settings",
        sa.Column("weight_log_interval_days", sa.Integer(), nullable=False, server_default="7"),
    )


def downgrade() -> None:
    op.drop_column("app_settings", "weight_log_interval_days")
    op.drop_column("app_settings", "event_weight_due")
    op.drop_column("app_settings", "event_maint_deep_clean")
    op.drop_column("app_settings", "event_maint_substrate")
    op.drop_column("app_settings", "event_maint_water")
