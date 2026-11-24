"""foco de trabajo

Revision ID: e6a1c9d3f5b7
Revises: d4e8a2c6f1b3
Create Date: 2026-11-24 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e6a1c9d3f5b7"
down_revision: str | Sequence[str] | None = "d4e8a2c6f1b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Crea el foco de trabajo: como mucho una fila (``id = 1``) con la tarea, y la
    subtarea opcional, con la que se está trabajando y desde cuándo (UTC). Borrar la
    tarea o la subtarea borra la fila. Ninguna otra tabla cambia."""
    op.create_table(
        "foco_trabajo",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("tarea_id", sa.Integer(), nullable=False),
        sa.Column("subtarea_id", sa.Integer(), nullable=True),
        sa.Column("desde", sa.DateTime(timezone=False), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_foco_trabajo_una_fila"),
        sa.ForeignKeyConstraint(
            ["tarea_id"], ["tareas.id"], name="fk_foco_trabajo_tarea", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["subtarea_id"], ["subtareas.id"], name="fk_foco_trabajo_subtarea", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Borra el foco de trabajo (se pierde el foco actual). El resto de los datos no
    cambia."""
    op.drop_table("foco_trabajo")
