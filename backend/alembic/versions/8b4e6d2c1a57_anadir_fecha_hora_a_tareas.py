"""añadir fecha_hora a tareas

Revision ID: 8b4e6d2c1a57
Revises: 3f1c2a9d7b10
Create Date: 2026-11-09 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8b4e6d2c1a57"
down_revision: str | Sequence[str] | None = "3f1c2a9d7b10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Añade la columna obligatoria fecha_hora.

    Las filas existentes reciben la fecha y hora actuales gracias a un valor por
    defecto temporal en el servidor, que se elimina a continuación: el modelo no
    declara ningún valor por defecto, la fecha y hora la elige siempre la persona
    usuaria.
    """
    op.add_column(
        "tareas",
        sa.Column(
            "fecha_hora",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.alter_column(
        "tareas",
        "fecha_hora",
        existing_type=sa.DateTime(),
        existing_nullable=False,
        server_default=None,
    )


def downgrade() -> None:
    """Elimina la columna fecha_hora."""
    op.drop_column("tareas", "fecha_hora")
