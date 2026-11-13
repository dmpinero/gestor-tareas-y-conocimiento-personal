"""comentarios de los pasos del workflow

Revision ID: d2a8e5c3f7b1
Revises: f3b9d7a2c6e4
Create Date: 2026-11-13 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d2a8e5c3f7b1"
down_revision: str | Sequence[str] | None = "f3b9d7a2c6e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Crea la tabla de los comentarios de los pasos de los workflows, vacía. Borrar un
    paso (o su workflow) borra sus comentarios. No cambia ningún dato existente."""
    op.create_table(
        "comentarios_paso_workflow",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("paso_id", sa.Integer(), nullable=False),
        sa.Column("texto", sa.String(length=500), nullable=False),
        sa.Column("creado", sa.DateTime(timezone=False), nullable=False),
        sa.Column("editado", sa.DateTime(timezone=False), nullable=True),
        sa.ForeignKeyConstraint(
            ["paso_id"],
            ["pasos_workflow.id"],
            name="fk_comentarios_paso_workflow_paso",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Elimina la tabla de los comentarios de los pasos, con sus comentarios. Los
    workflows, sus pasos y las tareas (con sus subtareas y los comentarios copiados en
    ellas) no cambian."""
    op.drop_table("comentarios_paso_workflow")
