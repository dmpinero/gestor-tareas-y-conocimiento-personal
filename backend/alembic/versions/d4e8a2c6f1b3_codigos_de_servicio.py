"""códigos de servicio

Revision ID: d4e8a2c6f1b3
Revises: c9a2f6e4d8b1
Create Date: 2026-11-23 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e8a2c6f1b3"
down_revision: str | Sequence[str] | None = "c9a2f6e4d8b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Sin distinguir mayúsculas pero sí tildes (ver modelos.INTERCALACION_NOMBRES_CATALOGO).
_INTERCALACION = "utf8mb4_0900_as_ci"


def upgrade() -> None:
    """Crea el catálogo de códigos de servicio del alta de oportunidades AXAS MS3
    (nombres de hasta 20 caracteres, únicos sin distinguir mayúsculas). Ninguna otra
    tabla cambia."""
    op.create_table(
        "codigos_servicio",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=20, collation=_INTERCALACION), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nombre"),
    )


def downgrade() -> None:
    """Borra el catálogo de códigos de servicio (se pierden los códigos). El resto de
    los datos no cambia."""
    op.drop_table("codigos_servicio")
