"""animals.hero_photo_id — profile portrait

Revision ID: 004_hero_photo
Revises: 003_maint_weight_events
Create Date: 2026-08-12
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_hero_photo"
down_revision: Union[str, None] = "003_maint_weight_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("animals", sa.Column("hero_photo_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_animals_hero_photo_id",
        "animals",
        "photos",
        ["hero_photo_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_animals_hero_photo_id", "animals", type_="foreignkey")
    op.drop_column("animals", "hero_photo_id")
