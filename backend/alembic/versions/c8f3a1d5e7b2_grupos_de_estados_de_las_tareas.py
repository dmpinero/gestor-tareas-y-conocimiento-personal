"""grupos de estados de las tareas

Revision ID: c8f3a1d5e7b2
Revises: b7e4c1d9f2a6
Create Date: 2026-11-11 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c8f3a1d5e7b2"
down_revision: str | Sequence[str] | None = "b7e4c1d9f2a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Sin distinguir mayúsculas pero sí tildes (ver modelos.INTERCALACION_NOMBRES_CATALOGO).
_INTERCALACION = "utf8mb4_0900_as_ci"


def upgrade() -> None:
    """Crea los grupos de estados y sus estados, vacíos, y añade a las tareas su grupo
    y su estado, opcionales.

    Las tareas que ya existían quedan sin grupo ni estado (las dos columnas a NULL);
    el resto de sus datos no cambia. El CHECK y la clave ajena compuesta garantizan
    que una tarea no tiene ni grupo ni estado, o que su estado es de su grupo.
    """
    op.create_table(
        "grupos_estados",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=50, collation=_INTERCALACION), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nombre"),
    )
    op.create_table(
        "estados_grupo",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("grupo_id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=50, collation=_INTERCALACION), nullable=False),
        sa.Column("posicion", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["grupo_id"], ["grupos_estados.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("grupo_id", "posicion", name="uq_estados_grupo_posicion"),
        sa.UniqueConstraint("grupo_id", "nombre", name="uq_estados_grupo_nombre"),
        sa.UniqueConstraint("grupo_id", "id", name="uq_estados_grupo_grupo_id"),
    )
    op.add_column("tareas", sa.Column("grupo_estados_id", sa.Integer(), nullable=True))
    op.add_column("tareas", sa.Column("estado_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_tareas_estado_del_grupo",
        "tareas",
        "estados_grupo",
        ["grupo_estados_id", "estado_id"],
        ["grupo_id", "id"],
    )
    op.create_foreign_key(
        "fk_tareas_grupo_estados", "tareas", "grupos_estados", ["grupo_estados_id"], ["id"]
    )
    op.create_check_constraint(
        "ck_tareas_grupo_y_estado", "tareas", "(grupo_estados_id IS NULL) = (estado_id IS NULL)"
    )


def downgrade() -> None:
    """Quita a las tareas su grupo y su estado y elimina los grupos de estados con sus
    estados. El resto de datos de las tareas no cambia; los grupos, sus estados y
    qué grupo y estado tenía cada tarea se pierden."""
    op.drop_constraint("ck_tareas_grupo_y_estado", "tareas", type_="check")
    op.drop_constraint("fk_tareas_grupo_estados", "tareas", type_="foreignkey")
    op.drop_constraint("fk_tareas_estado_del_grupo", "tareas", type_="foreignkey")
    # Borrar las columnas borra también los índices que MySQL creó para las claves.
    op.drop_column("tareas", "estado_id")
    op.drop_column("tareas", "grupo_estados_id")
    op.drop_table("estados_grupo")
    op.drop_table("grupos_estados")
