"""estado completada de las tareas

Revision ID: a7c3e9f2b4d8
Revises: e5b8d1f3a6c2
Create Date: 2026-11-10 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7c3e9f2b4d8"
down_revision: str | Sequence[str] | None = "e5b8d1f3a6c2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Añade el estado completada de las tareas; el valor por defecto de la columna
    deja pendientes las tareas existentes."""
    op.add_column(
        "tareas",
        sa.Column("completada", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    """Elimina el estado completada de las tareas; el resto de columnas no cambia."""
    op.drop_column("tareas", "completada")
