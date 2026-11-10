"""etiquetas, personas y fechas de creación y vencimiento de tareas

Revision ID: c4e2a7d9f1b3
Revises: 8b4e6d2c1a57
Create Date: 2026-11-09 20:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4e2a7d9f1b3"
down_revision: str | Sequence[str] | None = "8b4e6d2c1a57"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Sin distinguir mayúsculas pero sí tildes (ver modelos.INTERCALACION_NOMBRES_CATALOGO).
_INTERCALACION = "utf8mb4_0900_as_ci"


def upgrade() -> None:
    """Renombra fecha_hora a fecha_creacion conservando los datos, añade la fecha
    de vencimiento opcional y crea los catálogos de etiquetas y personas con sus
    relaciones N:M con las tareas."""
    op.alter_column(
        "tareas",
        "fecha_hora",
        new_column_name="fecha_creacion",
        existing_type=sa.DateTime(),
        existing_nullable=False,
    )
    op.add_column("tareas", sa.Column("fecha_vencimiento", sa.DateTime(), nullable=True))

    op.create_table(
        "etiquetas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=50, collation=_INTERCALACION), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nombre"),
    )
    op.create_table(
        "personas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=100, collation=_INTERCALACION), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nombre"),
    )
    op.create_table(
        "tarea_etiquetas",
        sa.Column("tarea_id", sa.Integer(), nullable=False),
        sa.Column("etiqueta_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["etiqueta_id"], ["etiquetas.id"]),
        sa.ForeignKeyConstraint(["tarea_id"], ["tareas.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("tarea_id", "etiqueta_id"),
    )
    op.create_table(
        "tarea_personas",
        sa.Column("tarea_id", sa.Integer(), nullable=False),
        sa.Column("persona_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["persona_id"], ["personas.id"]),
        sa.ForeignKeyConstraint(["tarea_id"], ["tareas.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("tarea_id", "persona_id"),
    )


def downgrade() -> None:
    """Elimina catálogos, relaciones y fecha de vencimiento, y devuelve a
    fecha_creacion su nombre anterior, fecha_hora, con los mismos valores."""
    op.drop_table("tarea_personas")
    op.drop_table("tarea_etiquetas")
    op.drop_table("personas")
    op.drop_table("etiquetas")
    op.drop_column("tareas", "fecha_vencimiento")
    op.alter_column(
        "tareas",
        "fecha_creacion",
        new_column_name="fecha_hora",
        existing_type=sa.DateTime(),
        existing_nullable=False,
    )
