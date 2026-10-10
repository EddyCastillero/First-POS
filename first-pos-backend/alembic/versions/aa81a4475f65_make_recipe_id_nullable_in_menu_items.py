"""make_recipe_id_nullable_in_menu_items

Revision ID: aa81a4475f65
Revises: e0080a108afc
Create Date: 2026-10-10 03:25:17.419641

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aa81a4475f65'
down_revision: Union[str, Sequence[str], None] = 'e0080a108afc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Permitir que recipe_id sea nullable al desvincular recetas de platillos inactivos/retirados."""
    op.alter_column('menu_items', 'recipe_id',
               existing_type=sa.UUID(),
               nullable=True)


def downgrade() -> None:
    """Revertir a not nullable."""
    op.alter_column('menu_items', 'recipe_id',
               existing_type=sa.UUID(),
               nullable=False)
