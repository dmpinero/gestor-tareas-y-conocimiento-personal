"""comentarios de 5000 caracteres

Revision ID: b3e7d1a9c5f2
Revises: f1a6c3e8b2d9
Create Date: 2026-11-19 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3e7d1a9c5f2"
down_revision: str | Sequence[str] | None = "f1a6c3e8b2d9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Las tres tablas de comentarios: de las tareas, de las subtareas y de los pasos.
_TABLAS = ("comentarios", "comentarios_subtarea", "comentarios_paso_workflow")

# Bytes que admite una columna TEXT de MySQL (el tipo anterior a esta revisión).
_BYTES_MAXIMOS_TEXT = 65535


def upgrade() -> None:
    """Amplía la columna ``texto`` de las tres tablas de comentarios de ``TEXT``
    (65 535 bytes) a ``MEDIUMTEXT`` (16 MB): la API admite ahora 5000 caracteres
    visibles y 50000 de HTML saneado, que con caracteres de hasta 4 bytes no caben
    en un TEXT. El contenido de los comentarios que ya existen no cambia."""
    for tabla in _TABLAS:
        op.alter_column(
            tabla,
            "texto",
            existing_type=sa.Text(),
            type_=mysql.MEDIUMTEXT(),
            existing_nullable=False,
        )


def downgrade() -> None:
    """Devuelve la columna ``texto`` a ``TEXT`` sin cambiar ningún comentario.

    Si algún comentario no cabe en un TEXT (más de 65 535 bytes), se detiene sin
    cambiar nada: MySQL lo truncaría o fallaría a medias. Antes hay que acortar o
    borrar esos comentarios.
    """
    conexion = op.get_bind()
    for tabla in _TABLAS:
        demasiado_largos = conexion.scalar(
            sa.text(
                f"SELECT COUNT(*) FROM {tabla} WHERE LENGTH(texto) > {_BYTES_MAXIMOS_TEXT}"  # noqa: S608
            )
        )
        if demasiado_largos:
            raise RuntimeError(
                f"No se puede deshacer la migración: {demasiado_largos} comentario(s) de "
                f"la tabla {tabla} ocupan más de {_BYTES_MAXIMOS_TEXT} bytes y no caben "
                "en la columna TEXT anterior. Acórtalos o bórralos antes de deshacerla."
            )
    for tabla in _TABLAS:
        op.alter_column(
            tabla,
            "texto",
            existing_type=mysql.MEDIUMTEXT(),
            type_=sa.Text(),
            existing_nullable=False,
        )
