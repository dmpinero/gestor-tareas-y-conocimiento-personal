"""subtareas de las tareas

Revision ID: e8b3f1a6d2c4
Revises: d9a4c2e7f1b5
Create Date: 2026-11-10 22:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e8b3f1a6d2c4"
down_revision: str | Sequence[str] | None = "d9a4c2e7f1b5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Crea la tabla de las subtareas, vacía; las tareas existentes no cambian.

    Borrar la tarea borra sus subtareas; borrar una persona asignada a alguna
    subtarea lo impide la clave ajena (RESTRICT, como en ``tarea_personas``).
    """
    op.create_table(
        "subtareas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tarea_id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=200), nullable=False),
        sa.Column("persona_id", sa.Integer(), nullable=True),
        sa.Column("prioridad", sa.Integer(), nullable=True),
        sa.Column("resuelta", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.CheckConstraint(
            "prioridad IS NULL OR prioridad BETWEEN 1 AND 5", name="ck_subtareas_prioridad_rango"
        ),
        sa.ForeignKeyConstraint(["persona_id"], ["personas.id"]),
        sa.ForeignKeyConstraint(["tarea_id"], ["tareas.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Elimina la tabla de las subtareas; el resto de tablas no cambia."""
    op.drop_table("subtareas")
