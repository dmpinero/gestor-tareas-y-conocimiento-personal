"""pasos de las tareas de tipo oportunidad

Revision ID: d9a4c2e7f1b5
Revises: b6d2f8a4c1e9
Create Date: 2026-11-10 21:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d9a4c2e7f1b5"
down_revision: str | Sequence[str] | None = "b6d2f8a4c1e9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Crea la tabla de los pasos de las tareas, vacía.

    Las oportunidades que ya existían no reciben pasos: solo se copian del workflow
    al crear una oportunidad nueva. Los pasos son una copia, sin clave ajena a los
    del workflow; borrar la tarea borra sus pasos.
    """
    op.create_table(
        "pasos_tarea",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tarea_id", sa.Integer(), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=50), nullable=False),
        sa.Column("hecho", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.ForeignKeyConstraint(["tarea_id"], ["tareas.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tarea_id", "numero", name="uq_pasos_tarea_numero"),
    )


def downgrade() -> None:
    """Elimina la tabla de los pasos de las tareas; el resto de tablas no cambia."""
    op.drop_table("pasos_tarea")
