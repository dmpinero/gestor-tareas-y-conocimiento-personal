"""workflows con nombre

Revision ID: f3b9d7a2c6e4
Revises: c8f3a1d5e7b2
Create Date: 2026-11-12 11:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f3b9d7a2c6e4"
down_revision: str | Sequence[str] | None = "c8f3a1d5e7b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Sin distinguir mayúsculas pero sí tildes (ver modelos.INTERCALACION_NOMBRES_CATALOGO).
_INTERCALACION = "utf8mb4_0900_as_ci"

# Nombre del workflow que recibe los pasos del único workflow que había.
_WORKFLOW_OPORTUNIDADES = "Workflow Oportunidades"


def upgrade() -> None:
    """Pasa del único workflow de las oportunidades a workflows con nombre, y añade a
    las tareas su workflow, opcional.

    Crea la tabla ``workflows`` con el workflow «Workflow Oportunidades» y le asigna
    todos los pasos que ya existían, con sus mismos ids, números y nombres: la tabla
    de los pasos se renombra a ``pasos_workflow`` y recibe la columna del workflow. El
    número pasa a ser único dentro de cada workflow. Las tareas de tipo oportunidad
    que ya existían pasan a tener el workflow «Workflow Oportunidades» (sus subtareas
    salieron de él, y así elegirlo después no duplica sus pasos); las demás quedan sin
    workflow. Las subtareas y el resto de los datos de las tareas no cambian.
    """
    op.create_table(
        "workflows",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=50, collation=_INTERCALACION), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nombre"),
    )
    op.execute(
        sa.text("INSERT INTO workflows (nombre) VALUES (:nombre)").bindparams(
            nombre=_WORKFLOW_OPORTUNIDADES
        )
    )
    op.rename_table("pasos_workflow_oportunidades", "pasos_workflow")
    op.add_column("pasos_workflow", sa.Column("workflow_id", sa.Integer(), nullable=True))
    op.execute("UPDATE pasos_workflow SET workflow_id = (SELECT MIN(id) FROM workflows)")
    op.alter_column("pasos_workflow", "workflow_id", existing_type=sa.Integer(), nullable=False)
    # Primero la restricción única nueva (que sirve de índice de la clave ajena) y
    # después se quita la antigua, que MySQL llamó como su columna.
    op.create_unique_constraint(
        "uq_pasos_workflow_numero", "pasos_workflow", ["workflow_id", "numero"]
    )
    op.drop_constraint("numero", "pasos_workflow", type_="unique")
    op.create_foreign_key(
        "fk_pasos_workflow_workflow",
        "pasos_workflow",
        "workflows",
        ["workflow_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.add_column("tareas", sa.Column("workflow_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_tareas_workflow", "tareas", "workflows", ["workflow_id"], ["id"])
    op.execute(
        sa.text(
            "UPDATE tareas SET workflow_id = (SELECT id FROM workflows WHERE nombre = :nombre) "
            "WHERE tipo = 'oportunidad'"
        ).bindparams(nombre=_WORKFLOW_OPORTUNIDADES)
    )


def downgrade() -> None:
    """Vuelve al único workflow de las oportunidades.

    Quita a las tareas su workflow (sus subtareas no cambian) y devuelve a
    ``pasos_workflow_oportunidades`` los pasos del workflow «Workflow Oportunidades»
    (sin distinguir mayúsculas), con sus mismos ids, números y nombres. Los demás
    workflows y sus pasos se pierden, igual que qué workflow tenía cada tarea; si ya
    no existe «Workflow Oportunidades», el workflow de las oportunidades queda vacío.
    """
    op.drop_constraint("fk_tareas_workflow", "tareas", type_="foreignkey")
    # Borrar la columna borra también el índice que MySQL creó para la clave.
    op.drop_column("tareas", "workflow_id")
    op.execute(
        sa.text(
            "DELETE p FROM pasos_workflow p "
            "LEFT JOIN workflows w ON w.id = p.workflow_id AND w.nombre = :nombre "
            "WHERE w.id IS NULL"
        ).bindparams(nombre=_WORKFLOW_OPORTUNIDADES)
    )
    op.drop_constraint("fk_pasos_workflow_workflow", "pasos_workflow", type_="foreignkey")
    op.create_unique_constraint("numero", "pasos_workflow", ["numero"])
    op.drop_constraint("uq_pasos_workflow_numero", "pasos_workflow", type_="unique")
    op.drop_column("pasos_workflow", "workflow_id")
    op.rename_table("pasos_workflow", "pasos_workflow_oportunidades")
    op.drop_table("workflows")
