"""contador congelado de las tareas

Revision ID: e2c7a9f4b1d6
Revises: c5e1b8f4a2d7
Create Date: 2026-11-17 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e2c7a9f4b1d6"
down_revision: str | Sequence[str] | None = "c5e1b8f4a2d7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Añade a las tareas el instante (en UTC, sin zona) desde el que su contador de
    vencimiento está congelado, o NULL si no lo está.

    Las tareas que ya estaban completadas o en un estado llamado DONE (sin distinguir
    mayúsculas, en cualquier grupo) quedan congeladas desde el instante de la
    migración: su contador se para en el valor que muestra al desplegarla. Las demás
    quedan sin congelar. El resto de los datos no cambia.
    """
    op.add_column("tareas", sa.Column("congelada_en", sa.DateTime(), nullable=True))
    op.execute(
        "UPDATE tareas t LEFT JOIN estados_grupo e ON e.id = t.estado_id "
        "SET t.congelada_en = UTC_TIMESTAMP() "
        "WHERE t.completada OR LOWER(e.nombre) = 'done'"
    )


def downgrade() -> None:
    """Quita el instante de congelación: los contadores vuelven a correr todos. El
    resto de los datos no cambia."""
    op.drop_column("tareas", "congelada_en")
