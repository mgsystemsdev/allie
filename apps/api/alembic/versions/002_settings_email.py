"""app_settings + email_send_log

Revision ID: 002_settings_email
Revises: 001_initial
Create Date: 2026-08-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_settings_email"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("reminder_email", sa.String(320), nullable=False, server_default=""),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="America/Chicago"),
        sa.Column("digest_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("digest_time_1", sa.String(5), nullable=False, server_default="08:00"),
        sa.Column("digest_time_2", sa.String(5), nullable=False, server_default="20:00"),
        sa.Column("digest_second_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("feed_ready_days", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("handle_clear_hours", sa.Integer(), nullable=False, server_default="72"),
        sa.Column("handling_max_gap_days", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("maint_water_days", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("maint_substrate_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("maint_deep_clean_days", sa.Integer(), nullable=False, server_default="90"),
        sa.Column("feed_interval_mode", sa.String(20), nullable=False, server_default="auto"),
        sa.Column("feed_interval_days", sa.Integer(), nullable=True),
        sa.Column("event_handle_cleared", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("event_feed_overdue", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("event_handling_gap", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("event_shed_status", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("event_regurg", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("digest_show_feed", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("digest_show_maint", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("digest_show_shed", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("digest_show_handle", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("digest_show_activity", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.execute(
        """
        INSERT INTO app_settings (
            id, email_enabled, reminder_email, timezone,
            digest_enabled, digest_time_1, digest_time_2, digest_second_enabled,
            feed_ready_days, handle_clear_hours, handling_max_gap_days,
            maint_water_days, maint_substrate_days, maint_deep_clean_days,
            feed_interval_mode
        ) VALUES (
            1, true, 'allie.carpet.python@gmail.com', 'America/Chicago',
            true, '08:00', '20:00', true,
            2, 72, 2,
            3, 30, 90,
            'auto'
        )
        """
    )
    op.create_table(
        "email_send_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("dedupe_key", sa.String(200), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("dedupe_key"),
    )
    op.create_index("ix_email_send_log_kind", "email_send_log", ["kind"])


def downgrade() -> None:
    op.drop_table("email_send_log")
    op.drop_table("app_settings")
