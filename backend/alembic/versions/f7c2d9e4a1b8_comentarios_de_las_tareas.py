"""comentarios de las tareas

Revision ID: f7c2d9e4a1b8
Revises: e8b3f1a6d2c4
Create Date: 2026-11-10 22:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f7c2d9e4a1b8"
down_revision: str | Sequence[str] | None = "e8b3f1a6d2c4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Crea la tabla del histórico de comentarios de las tareas, vacía.

    ``creado`` guarda el instante de alta en UTC (DATETIME sin zona). Borrar la
    tarea borra sus comentarios.
    """
    op.create_table(
        "comentarios",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tarea_id", sa.Integer(), nullable=False),
        sa.Column("texto", sa.String(length=500), nullable=False),
        sa.Column("creado", sa.DateTime(timezone=False), nullable=False),
        sa.ForeignKeyConstraint(["tarea_id"], ["tareas.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Elimina la tabla de los comentarios; el resto de tablas no cambia."""
    op.drop_table("comentarios")
