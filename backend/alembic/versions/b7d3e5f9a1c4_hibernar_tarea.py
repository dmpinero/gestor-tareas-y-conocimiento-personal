"""hibernar tarea

Revision ID: b7d3e5f9a1c4
Revises: 483e78c30e26
Create Date: 2026-11-25 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7d3e5f9a1c4"
down_revision: str | Sequence[str] | None = "483e78c30e26"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Añade a las tareas el instante (UTC, sin zona en la columna) desde el que están
    hibernadas, o NULL si no lo están. Ninguna tarea existente queda hibernada y
    ningún otro dato cambia."""
    op.add_column("tareas", sa.Column("hibernada_desde", sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Quita la columna: las tareas hibernadas dejan de estarlo sin correr su
    vencimiento."""
    op.drop_column("tareas", "hibernada_desde")
