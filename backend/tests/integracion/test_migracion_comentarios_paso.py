"""Migración de los comentarios de los pasos: crea una tabla nueva sin tocar los datos
que ya existen, y se deshace quitando solo esa tabla."""

from pathlib import Path

from alembic.config import Config
from sqlalchemy import inspect, select, text

from alembic import command
from gestor_tareas.infraestructura.persistencia.modelos import (
    ComentarioSubtareaModelo,
    PasoWorkflowModelo,
    WorkflowModelo,
)
from gestor_tareas.infraestructura.persistencia.sesion import FabricaSesiones
from tests.integracion.tablas import vaciar_tablas

_RAIZ = Path(__file__).resolve().parents[2]
_ANTERIOR = "f3b9d7a2c6e4"
# Revisión más reciente: la de los comentarios con formato, posterior a esta.
_ULTIMA = "a9c4e1f7b3d2"
_TABLA = "comentarios_paso_workflow"


def _alembic() -> Config:
    # Sin el alembic.ini: su configuración de logs desactivaría los registradores
    # que ya existen en el proceso de los tests. env.py toma la URL de la aplicación.
    configuracion = Config()
    configuracion.set_main_option("script_location", str(_RAIZ / "alembic"))
    return configuracion


def _estado() -> tuple[bool, list[tuple], str]:
    """(si existe la tabla, los pasos con su workflow, la revisión actual)."""
    sesion = FabricaSesiones()
    try:
        existe = inspect(sesion.connection()).has_table(_TABLA)
        pasos = sesion.execute(
            select(WorkflowModelo.nombre, PasoWorkflowModelo.numero, PasoWorkflowModelo.nombre)
            .join(PasoWorkflowModelo, PasoWorkflowModelo.workflow_id == WorkflowModelo.id)
            .order_by(PasoWorkflowModelo.id)
        ).all()
        revision = sesion.scalar(text("SELECT version_num FROM alembic_version"))
        return existe, [tuple(p) for p in pasos], revision
    finally:
        sesion.close()


def test_la_migracion_crea_la_tabla_y_se_deshace_sin_tocar_los_datos_existentes() -> None:
    sesion = FabricaSesiones()
    try:
        vaciar_tablas(sesion)
        workflow = WorkflowModelo(nombre="Ventas")
        sesion.add(workflow)
        sesion.flush()
        sesion.add(PasoWorkflowModelo(workflow_id=workflow.id, numero=1, nombre="Contacto"))
        sesion.execute(
            text(
                f"INSERT INTO {_TABLA} (paso_id, texto, creado) "
                "SELECT id, 'Llamar', '2026-11-10 16:30:05' FROM pasos_workflow"
            )
        )
        sesion.commit()
    finally:
        sesion.close()
    pasos = [("Ventas", 1, "Contacto")]
    assert _estado() == (True, pasos, _ULTIMA)

    try:
        command.downgrade(_alembic(), _ANTERIOR)
        assert _estado() == (False, pasos, _ANTERIOR)
    finally:
        command.upgrade(_alembic(), "head")

    # Vuelve a crearla, vacía, con los mismos datos de antes en el resto de tablas.
    assert _estado() == (True, pasos, _ULTIMA)
    sesion = FabricaSesiones()
    try:
        assert sesion.scalar(text(f"SELECT COUNT(*) FROM {_TABLA}")) == 0
        assert sesion.scalars(select(ComentarioSubtareaModelo.id)).all() == []
        # Y con el borrado en cascada desde el paso.
        id_paso = sesion.scalar(select(PasoWorkflowModelo.id))
        sesion.execute(
            text(
                f"INSERT INTO {_TABLA} (paso_id, texto, creado) "
                "VALUES (:paso, 'x', '2026-11-10 16:30:05')"
            ),
            {"paso": id_paso},
        )
        sesion.execute(text("DELETE FROM pasos_workflow"))
        assert sesion.scalar(text(f"SELECT COUNT(*) FROM {_TABLA}")) == 0
        sesion.rollback()
    finally:
        sesion.close()
