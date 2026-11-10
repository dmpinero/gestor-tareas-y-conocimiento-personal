"""pasos del workflow de las oportunidades

Revision ID: b6d2f8a4c1e9
Revises: a7c3e9f2b4d8
Create Date: 2026-11-10 19:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b6d2f8a4c1e9"
down_revision: str | Sequence[str] | None = "a7c3e9f2b4d8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Crea la tabla de los pasos del workflow de las oportunidades, vacía; el número
    de cada paso (su posición) es único."""
    op.create_table(
        "pasos_workflow_oportunidades",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=50), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("numero"),
    )


def downgrade() -> None:
    """Elimina la tabla de los pasos del workflow; el resto de tablas no cambia."""
    op.drop_table("pasos_workflow_oportunidades")
