"""paso del workflow de las subtareas

Revision ID: c5e1b8f4a2d7
Revises: a9c4e1f7b3d2
Create Date: 2026-11-16 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c5e1b8f4a2d7"
down_revision: str | Sequence[str] | None = "a9c4e1f7b3d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _vinculos() -> list[dict[str, int]]:
    """Paso del workflow de su tarea que corresponde a cada subtarea que ya existía.

    Para cada tarea con workflow y cada paso de ese workflow (por número), la
    subtarea de menor id con exactamente el mismo nombre (mismas mayúsculas y
    tildes) que aún no tenga paso. Así, si varias subtareas tienen el nombre de un
    mismo paso, solo se vincula la de menor id. Las tareas sin workflow y las
    subtareas con otros nombres no se tocan.
    """
    conexion = op.get_bind()
    pasos = conexion.execute(
        sa.text(
            "SELECT t.id AS tarea_id, p.id AS paso_id, p.nombre "
            "FROM tareas t JOIN pasos_workflow p ON p.workflow_id = t.workflow_id "
            "ORDER BY t.id, p.numero"
        )
    ).all()
    subtareas = conexion.execute(
        sa.text(
            "SELECT s.id, s.tarea_id, s.nombre FROM subtareas s "
            "JOIN tareas t ON t.id = s.tarea_id WHERE t.workflow_id IS NOT NULL "
            "ORDER BY s.id"
        )
    ).all()
    libres: dict[tuple[int, str], list[int]] = {}
    for subtarea in subtareas:
        libres.setdefault((subtarea.tarea_id, subtarea.nombre), []).append(subtarea.id)
    vinculos = []
    for paso in pasos:
        candidatas = libres.get((paso.tarea_id, paso.nombre))
        if candidatas:
            vinculos.append({"id": candidatas.pop(0), "paso": paso.paso_id})
    return vinculos


def upgrade() -> None:
    """Añade a las subtareas el paso del workflow del que nacen (opcional; borrar el
    paso las deja sin él) y vincula las que ya existían por su nombre (ver
    ``_vinculos``). El resto de los datos no cambia."""
    op.add_column("subtareas", sa.Column("paso_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_subtareas_paso",
        "subtareas",
        "pasos_workflow",
        ["paso_id"],
        ["id"],
        ondelete="SET NULL",
    )
    vinculos = _vinculos()
    if vinculos:
        op.get_bind().execute(
            sa.text("UPDATE subtareas SET paso_id = :paso WHERE id = :id"), vinculos
        )


def downgrade() -> None:
    """Quita a las subtareas su paso: vuelven a ordenarse por orden de alta. El resto
    de los datos no cambia."""
    op.drop_constraint("fk_subtareas_paso", "subtareas", type_="foreignkey")
    # Borrar la columna borra también el índice que MySQL creó para la clave.
    op.drop_column("subtareas", "paso_id")
