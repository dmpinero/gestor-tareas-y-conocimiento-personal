"""edición de los comentarios

Revision ID: a3d9f6b2c8e1
Revises: f7c2d9e4a1b8
Create Date: 2026-11-11 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3d9f6b2c8e1"
down_revision: str | Sequence[str] | None = "f7c2d9e4a1b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Añade a los comentarios el instante de su última edición.

    ``editado`` guarda ese instante en UTC (DATETIME sin zona) y es NULL si el
    comentario nunca se editó, como todos los que ya existen.
    """
    op.add_column("comentarios", sa.Column("editado", sa.DateTime(timezone=False), nullable=True))


def downgrade() -> None:
    """Quita la columna ``editado``; el texto y la fecha de alta de los comentarios
    no cambian (se pierde solo cuándo se editaron)."""
    op.drop_column("comentarios", "editado")
