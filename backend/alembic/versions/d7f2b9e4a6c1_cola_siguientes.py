"""cola de siguientes tareas

Revision ID: d7f2b9e4a6c1
Revises: c4e8a2f6b1d9
Create Date: 2026-11-26 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d7f2b9e4a6c1"
down_revision: str | Sequence[str] | None = "c4e8a2f6b1d9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Crea la cola de siguientes tareas, vacía: una fila por tarea con su posición.
    Borrar la tarea borra su fila. Ningún otro dato cambia."""
    op.create_table(
        "cola_siguientes",
        sa.Column("tarea_id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("posicion", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["tarea_id"],
            ["tareas.id"],
            name="fk_cola_siguientes_tarea",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("tarea_id"),
    )


def downgrade() -> None:
    """Quita la tabla: se pierde la cola de siguientes."""
    op.drop_table("cola_siguientes")
