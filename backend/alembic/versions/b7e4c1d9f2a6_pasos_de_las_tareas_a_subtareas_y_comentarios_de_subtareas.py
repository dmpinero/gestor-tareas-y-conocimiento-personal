"""pasos de las tareas a subtareas y comentarios de las subtareas

Revision ID: b7e4c1d9f2a6
Revises: a3d9f6b2c8e1
Create Date: 2026-11-11 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7e4c1d9f2a6"
down_revision: str | Sequence[str] | None = "a3d9f6b2c8e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Convierte los pasos de las tareas en subtareas, crea la tabla de los
    comentarios de las subtareas y elimina la de los pasos.

    Cada paso pasa a ser una subtarea de su tarea con su nombre, sin persona ni
    prioridad y resuelta si el paso estaba hecho. Se insertan ordenados por tarea y
    número de paso, así que los ids autoincrementales (que dan el orden de alta de
    las subtareas) respetan el orden de los pasos; quedan detrás de las subtareas
    que la tarea ya tuviera. Las demás filas de ``subtareas`` no cambian.
    """
    op.execute(
        """
        INSERT INTO subtareas (tarea_id, nombre, persona_id, prioridad, resuelta)
        SELECT tarea_id, nombre, NULL, NULL, hecho
        FROM pasos_tarea
        ORDER BY tarea_id, numero
        """
    )
    op.create_table(
        "comentarios_subtarea",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("subtarea_id", sa.Integer(), nullable=False),
        sa.Column("texto", sa.String(length=500), nullable=False),
        sa.Column("creado", sa.DateTime(timezone=False), nullable=False),
        sa.Column("editado", sa.DateTime(timezone=False), nullable=True),
        sa.ForeignKeyConstraint(["subtarea_id"], ["subtareas.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.drop_table("pasos_tarea")


def downgrade() -> None:
    """Elimina los comentarios de las subtareas y vuelve a crear la tabla de los
    pasos de las tareas, vacía y con su esquema original.

    La conversión no se deshace en los datos: las subtareas creadas a partir de los
    pasos se quedan como subtareas y no vuelven a ser pasos (no se distinguen de las
    demás). Los comentarios de las subtareas se pierden. Para recuperar el estado
    anterior hay que restaurar la copia de seguridad hecha antes de migrar.
    """
    op.drop_table("comentarios_subtarea")
    op.create_table(
        "pasos_tarea",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tarea_id", sa.Integer(), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=50), nullable=False),
        sa.Column("hecho", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.ForeignKeyConstraint(["tarea_id"], ["tareas.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tarea_id", "numero", name="uq_pasos_tarea_numero"),
    )
