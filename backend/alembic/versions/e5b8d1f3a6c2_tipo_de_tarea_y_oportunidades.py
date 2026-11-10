"""tipo de tarea y datos de las oportunidades

Revision ID: e5b8d1f3a6c2
Revises: c4e2a7d9f1b3
Create Date: 2026-11-10 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5b8d1f3a6c2"
down_revision: str | Sequence[str] | None = "c4e2a7d9f1b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Lista fija de esta revisión: una migración posterior que añada un tipo debe
# rehacer este CHECK con la lista nueva.
_CHECK_TIPO = "tipo IS NULL OR tipo IN ('oportunidad')"


def upgrade() -> None:
    """Añade el tipo opcional de las tareas (las existentes quedan sin tipo) y la
    tabla 1:1 con los datos de las tareas de tipo oportunidad."""
    op.add_column("tareas", sa.Column("tipo", sa.String(length=30), nullable=True))
    op.create_check_constraint("ck_tareas_tipo_valido", "tareas", _CHECK_TIPO)
    op.create_table(
        "oportunidades",
        sa.Column("tarea_id", sa.Integer(), nullable=False),
        sa.Column("codigo", sa.String(length=10), nullable=False),
        sa.Column("descripcion", sa.String(length=200), nullable=True),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["tarea_id"], ["tareas.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("tarea_id"),
    )


def downgrade() -> None:
    """Elimina los datos de las oportunidades y el tipo de las tareas; el resto de
    columnas de las tareas no cambia."""
    op.drop_table("oportunidades")
    # MySQL no deja borrar una columna a la que se refiere un CHECK.
    op.drop_constraint("ck_tareas_tipo_valido", "tareas", type_="check")
    op.drop_column("tareas", "tipo")
