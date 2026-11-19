"""imagenes de los comentarios

Revision ID: f1a6c3e8b2d9
Revises: e2c7a9f4b1d6
Create Date: 2026-11-19 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1a6c3e8b2d9"
down_revision: str | Sequence[str] | None = "e2c7a9f4b1d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Crea la tabla de las imágenes de los comentarios (capturas de pantalla), con
    su contenido en un MEDIUMBLOB (hasta 16 MB; la API admite 5 MB). El resto de
    las tablas y de los datos no cambia."""
    op.create_table(
        "imagenes",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("tipo", sa.String(length=20), nullable=False),
        sa.Column("tamano", sa.Integer(), nullable=False),
        sa.Column(
            "contenido",
            sa.LargeBinary().with_variant(mysql.MEDIUMBLOB(), "mysql"),
            nullable=False,
        ),
        sa.Column("creada", sa.DateTime(timezone=False), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Borra la tabla de las imágenes (y las imágenes subidas). Los comentarios no
    cambian: los que tenían imágenes conservan su HTML, pero esas imágenes ya no se
    pueden descargar (404)."""
    op.drop_table("imagenes")
