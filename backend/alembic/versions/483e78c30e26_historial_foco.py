"""historial del foco

Revision ID: 483e78c30e26
Revises: e6a1c9d3f5b7
Create Date: 2026-11-24 16:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "483e78c30e26"
down_revision: str | Sequence[str] | None = "e6a1c9d3f5b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Crea el historial del foco: un periodo por cada vez que se fijó el foco, con
    la tarea y la subtarea opcional, sus nombres de ese momento y de cuándo a cuándo
    (UTC; ``hasta`` es NULL en el periodo en curso, y solo puede haber uno). Borrar la
    tarea o la subtarea deja su id a NULL y conserva el periodo.

    Si hay foco, abre su periodo en curso con el mismo ``desde``. Ninguna otra tabla
    cambia."""
    op.create_table(
        "historial_foco",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tarea_id", sa.Integer(), nullable=True),
        sa.Column("subtarea_id", sa.Integer(), nullable=True),
        sa.Column("tarea_nombre", sa.String(length=200), nullable=False),
        sa.Column("subtarea_nombre", sa.String(length=200), nullable=True),
        sa.Column("desde", sa.DateTime(timezone=False), nullable=False),
        sa.Column("hasta", sa.DateTime(timezone=False), nullable=True),
        # 1 en el periodo en curso y NULL en los cerrados: el índice único admite
        # muchos NULL, así que como mucho hay un periodo en curso.
        sa.Column(
            "en_curso",
            sa.SmallInteger(),
            sa.Computed("IF(hasta IS NULL, 1, NULL)", persisted=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["tarea_id"], ["tareas.id"], name="fk_historial_foco_tarea", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["subtarea_id"],
            ["subtareas.id"],
            name="fk_historial_foco_subtarea",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("en_curso", name="uq_historial_foco_en_curso"),
    )
    op.create_index("ix_historial_foco_desde", "historial_foco", ["desde"])
    op.execute(
        "INSERT INTO historial_foco (tarea_id, subtarea_id, tarea_nombre, subtarea_nombre, desde) "
        "SELECT f.tarea_id, f.subtarea_id, t.nombre, s.nombre, f.desde "
        "FROM foco_trabajo f "
        "JOIN tareas t ON t.id = f.tarea_id "
        "LEFT JOIN subtareas s ON s.id = f.subtarea_id"
    )


def downgrade() -> None:
    """Borra el historial del foco (se pierden sus periodos). El foco actual y el
    resto de los datos no cambian."""
    op.drop_table("historial_foco")
