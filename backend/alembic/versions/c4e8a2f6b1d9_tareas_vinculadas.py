"""tareas vinculadas

Revision ID: c4e8a2f6b1d9
Revises: b7d3e5f9a1c4
Create Date: 2026-11-26 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4e8a2f6b1d9"
down_revision: str | Sequence[str] | None = "b7d3e5f9a1c4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Crea la tabla de vínculos entre tareas, vacía. Cada vínculo se guarda en los dos
    sentidos; borrar cualquiera de las dos tareas borra sus filas. Ningún otro dato
    cambia."""
    op.create_table(
        "tareas_vinculadas",
        sa.Column("tarea_id", sa.Integer(), nullable=False),
        sa.Column("vinculada_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["tarea_id"],
            ["tareas.id"],
            name="fk_tareas_vinculadas_tarea",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["vinculada_id"],
            ["tareas.id"],
            name="fk_tareas_vinculadas_vinculada",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("tarea_id", "vinculada_id"),
    )


def downgrade() -> None:
    """Quita la tabla: las tareas pierden sus vínculos."""
    op.drop_table("tareas_vinculadas")
