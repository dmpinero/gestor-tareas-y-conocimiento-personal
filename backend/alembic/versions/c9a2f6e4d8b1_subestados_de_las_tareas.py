"""subestados de las tareas

Revision ID: c9a2f6e4d8b1
Revises: b3e7d1a9c5f2
Create Date: 2026-11-19 18:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c9a2f6e4d8b1"
down_revision: str | Sequence[str] | None = "b3e7d1a9c5f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Sin distinguir mayúsculas pero sí tildes (ver modelos.INTERCALACION_NOMBRES_CATALOGO).
_INTERCALACION = "utf8mb4_0900_as_ci"


def upgrade() -> None:
    """Crea el catálogo de subestados (nombres únicos sin distinguir mayúsculas, como
    el de etiquetas) y el subestado opcional de las tareas (``tareas.subestado_id``):
    borrar un subestado deja sus tareas sin él (ON DELETE SET NULL). Todas las tareas
    que ya existen quedan sin subestado (NULL) y el resto de los datos no cambia."""
    op.create_table(
        "subestados",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=50, collation=_INTERCALACION), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nombre"),
    )
    op.add_column("tareas", sa.Column("subestado_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_tareas_subestado",
        "tareas",
        "subestados",
        ["subestado_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Quita a las tareas su subestado y borra el catálogo de subestados (se pierden
    los subestados asignados). El resto de los datos no cambia."""
    op.drop_constraint("fk_tareas_subestado", "tareas", type_="foreignkey")
    # Borrar la columna borra también el índice que MySQL creó para la clave.
    op.drop_column("tareas", "subestado_id")
    op.drop_table("subestados")
