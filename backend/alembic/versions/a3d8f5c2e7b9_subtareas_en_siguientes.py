"""subtareas en la cola de siguientes y en las sugerencias elegidas

Revision ID: a3d8f5c2e7b9
Revises: e9c3a7f1b5d2
Create Date: 2026-11-27 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3d8f5c2e7b9"
down_revision: str | Sequence[str] | None = "e9c3a7f1b5d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLA = "cola_siguientes"
_FK_TAREA = "fk_cola_siguientes_tarea"
_FK_SUBTAREA = "fk_cola_siguientes_subtarea"
_UNICA = "uq_cola_siguientes_entrada"


def _fk_tarea() -> None:
    op.create_foreign_key(_FK_TAREA, _TABLA, "tareas", ["tarea_id"], ["id"], ondelete="CASCADE")


def upgrade() -> None:
    """Una entrada de las listas puede ser también una subtarea: ``cola_siguientes``
    gana ``subtarea_id`` (NULL en una tarea entera; borrar la subtarea borra su fila)
    y un id propio autoincremental como clave, en vez de ``tarea_id``. La unicidad
    pasa a ser por ``(tarea_id, subtarea_clave)``, con la columna generada
    ``subtarea_clave = COALESCE(subtarea_id, 0)`` para que también valga con NULL. Es
    virtual: MySQL no admite ON DELETE CASCADE en la base de una columna generada
    guardada.

    Las filas existentes se conservan tal cual (lista y posición) como entradas de
    tarea entera. Ningún otro dato cambia."""
    # La clave ajena de la tarea usa el índice de la clave primaria: se quita antes
    # y se vuelve a crear sobre el índice único nuevo.
    op.drop_constraint(_FK_TAREA, _TABLA, type_="foreignkey")
    op.execute(
        f"ALTER TABLE {_TABLA} DROP PRIMARY KEY, "
        "ADD COLUMN id INT NOT NULL AUTO_INCREMENT PRIMARY KEY FIRST"
    )
    op.add_column(_TABLA, sa.Column("subtarea_id", sa.Integer(), nullable=True))
    op.add_column(
        _TABLA,
        sa.Column(
            "subtarea_clave",
            sa.Integer(),
            sa.Computed("COALESCE(subtarea_id, 0)", persisted=False),
            nullable=False,
        ),
    )
    op.create_unique_constraint(_UNICA, _TABLA, ["tarea_id", "subtarea_clave"])
    _fk_tarea()
    op.create_foreign_key(
        _FK_SUBTAREA, _TABLA, "subtareas", ["subtarea_id"], ["id"], ondelete="CASCADE"
    )


def downgrade() -> None:
    """Vuelve a una fila por tarea con ``tarea_id`` como clave. Se pierden las
    entradas de subtareas (de las dos listas); las de tareas enteras se conservan con
    su lista y su posición."""
    op.execute(f"DELETE FROM {_TABLA} WHERE subtarea_id IS NOT NULL")
    op.drop_constraint(_FK_SUBTAREA, _TABLA, type_="foreignkey")
    op.drop_constraint(_FK_TAREA, _TABLA, type_="foreignkey")
    op.drop_constraint(_UNICA, _TABLA, type_="unique")
    op.drop_column(_TABLA, "subtarea_clave")
    op.drop_column(_TABLA, "subtarea_id")
    op.execute(f"ALTER TABLE {_TABLA} DROP PRIMARY KEY, DROP COLUMN id, ADD PRIMARY KEY (tarea_id)")
    _fk_tarea()
