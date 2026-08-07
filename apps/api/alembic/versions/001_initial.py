"""initial schema + seed Allie

Revision ID: 001_initial
Revises:
Create Date: 2026-08-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "animals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("species", sa.String(200), nullable=False),
        sa.Column("common_name", sa.String(200), nullable=False, server_default=""),
        sa.Column("dob", sa.Date(), nullable=False),
        sa.Column("sex", sa.String(20), nullable=False, server_default="female"),
        sa.Column("owner", sa.String(200), nullable=False, server_default=""),
        sa.Column("status", sa.String(50), nullable=False, server_default="Active & Healthy"),
    )

    temperament = postgresql.ENUM("calm", "nippy", "musk", name="temperament", create_type=False)
    shed_status = postgresql.ENUM("clear", "blue", "opaque", "shed", name="shed_status", create_type=False)
    elimination_kind = postgresql.ENUM("feces", "urates", "both", name="elimination_kind", create_type=False)
    maintenance_kind = postgresql.ENUM(
        "water", "substrate", "deep_clean", name="maintenance_kind", create_type=False
    )
    photo_kind = postgresql.ENUM(
        "growth", "shed", "body_condition", "other", name="photo_kind", create_type=False
    )

    op.execute(
        "DO $$ BEGIN CREATE TYPE temperament AS ENUM ('calm', 'nippy', 'musk'); EXCEPTION WHEN duplicate_object THEN null; END $$;"
    )
    op.execute(
        "DO $$ BEGIN CREATE TYPE shed_status AS ENUM ('clear', 'blue', 'opaque', 'shed'); EXCEPTION WHEN duplicate_object THEN null; END $$;"
    )
    op.execute(
        "DO $$ BEGIN CREATE TYPE elimination_kind AS ENUM ('feces', 'urates', 'both'); EXCEPTION WHEN duplicate_object THEN null; END $$;"
    )
    op.execute(
        "DO $$ BEGIN CREATE TYPE maintenance_kind AS ENUM ('water', 'substrate', 'deep_clean'); EXCEPTION WHEN duplicate_object THEN null; END $$;"
    )
    op.execute(
        "DO $$ BEGIN CREATE TYPE photo_kind AS ENUM ('growth', 'shed', 'body_condition', 'other'); EXCEPTION WHEN duplicate_object THEN null; END $$;"
    )

    op.create_table(
        "feeds",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("animal_id", sa.Integer(), sa.ForeignKey("animals.id"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("prey_type", sa.String(100), nullable=False),
        sa.Column("prey_weight_g", sa.Float(), nullable=True),
        sa.Column("accepted", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("snake_weight_g", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_feeds_animal_id", "feeds", ["animal_id"])

    op.create_table(
        "regurgitations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("animal_id", sa.Integer(), sa.ForeignKey("animals.id"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("related_feed_id", sa.Integer(), sa.ForeignKey("feeds.id"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("severity", sa.String(50), nullable=False, server_default="moderate"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_regurgitations_animal_id", "regurgitations", ["animal_id"])

    op.create_table(
        "weights",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("animal_id", sa.Integer(), sa.ForeignKey("animals.id"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("weight_g", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_weights_animal_id", "weights", ["animal_id"])

    op.create_table(
        "handlings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("animal_id", sa.Integer(), sa.ForeignKey("animals.id"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("duration_min", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("temperament", temperament, nullable=False),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_handlings_animal_id", "handlings", ["animal_id"])

    op.create_table(
        "shed_cycles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("animal_id", sa.Integer(), sa.ForeignKey("animals.id"), nullable=False),
        sa.Column("status", shed_status, nullable=False),
        sa.Column("started_at", sa.Date(), nullable=False),
        sa.Column("completed_at", sa.Date(), nullable=True),
        sa.Column("quality", sa.String(100), nullable=True),
        sa.Column("eyes", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_shed_cycles_animal_id", "shed_cycles", ["animal_id"])

    op.create_table(
        "env_readings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("animal_id", sa.Integer(), sa.ForeignKey("animals.id"), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("temp_hot_f", sa.Float(), nullable=False),
        sa.Column("temp_cool_f", sa.Float(), nullable=False),
        sa.Column("temp_night_f", sa.Float(), nullable=True),
        sa.Column("humidity_pct", sa.Float(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_env_readings_animal_id", "env_readings", ["animal_id"])

    op.create_table(
        "eliminations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("animal_id", sa.Integer(), sa.ForeignKey("animals.id"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("kind", elimination_kind, nullable=False),
        sa.Column("related_feed_id", sa.Integer(), sa.ForeignKey("feeds.id"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_eliminations_animal_id", "eliminations", ["animal_id"])

    op.create_table(
        "maintenance",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("animal_id", sa.Integer(), sa.ForeignKey("animals.id"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("kind", maintenance_kind, nullable=False),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_maintenance_animal_id", "maintenance", ["animal_id"])

    op.create_table(
        "photos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("animal_id", sa.Integer(), sa.ForeignKey("animals.id"), nullable=False),
        sa.Column("taken_at", sa.Date(), nullable=False),
        sa.Column("kind", photo_kind, nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("caption", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_photos_animal_id", "photos", ["animal_id"])

    op.create_table(
        "treatments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("animal_id", sa.Integer(), sa.ForeignKey("animals.id"), nullable=False),
        sa.Column("started_at", sa.Date(), nullable=False),
        sa.Column("ended_at", sa.Date(), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("reason", sa.String(300), nullable=False, server_default=""),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_treatments_animal_id", "treatments", ["animal_id"])

    op.create_table(
        "contacts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("animal_id", sa.Integer(), sa.ForeignKey("animals.id"), nullable=False),
        sa.Column("label", sa.String(200), nullable=False),
        sa.Column("phone", sa.String(50), nullable=False, server_default=""),
        sa.Column("clinic", sa.String(200), nullable=False, server_default=""),
        sa.Column("is_emergency", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_contacts_animal_id", "contacts", ["animal_id"])

    op.create_table(
        "journal_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("animal_id", sa.Integer(), sa.ForeignKey("animals.id"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_journal_entries_animal_id", "journal_entries", ["animal_id"])

    op.create_table(
        "vet_visits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("animal_id", sa.Integer(), sa.ForeignKey("animals.id"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("reason", sa.String(300), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_vet_visits_animal_id", "vet_visits", ["animal_id"])

    op.execute(
        """
        INSERT INTO animals (name, species, common_name, dob, sex, owner, status)
        VALUES (
            'Allie',
            'Morelia bredli',
            'Centralian Carpet Python',
            '2025-08-21',
            'female',
            'Miguel Gonzalez',
            'Active & Healthy'
        )
        """
    )


def downgrade() -> None:
    for table in [
        "vet_visits",
        "journal_entries",
        "contacts",
        "treatments",
        "photos",
        "maintenance",
        "eliminations",
        "env_readings",
        "shed_cycles",
        "handlings",
        "weights",
        "regurgitations",
        "feeds",
        "animals",
    ]:
        op.drop_table(table)
    for enum_name in ["photo_kind", "maintenance_kind", "elimination_kind", "shed_status", "temperament"]:
        sa.Enum(name=enum_name).drop(op.get_bind(), checkfirst=True)
