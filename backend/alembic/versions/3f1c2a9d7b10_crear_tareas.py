"""crear tareas

Revision ID: 3f1c2a9d7b10
Revises:
Create Date: 2026-11-09 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3f1c2a9d7b10"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Crea la tabla de tareas."""
    op.create_table(
        "tareas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=200), nullable=False),
        sa.Column("prioridad", sa.Integer(), nullable=True),
        sa.Column("descripcion", sa.String(length=500), nullable=False),
        sa.CheckConstraint(
            "prioridad IS NULL OR prioridad BETWEEN 1 AND 5", name="ck_tareas_prioridad_rango"
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Elimina la tabla de tareas."""
    op.drop_table("tareas")
