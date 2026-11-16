"""Migración del vínculo de las subtareas con el paso del workflow del que vienen:
añade la columna y vincula las subtareas que ya existían por su nombre; se deshace
quitando solo esa columna."""

from pathlib import Path

from alembic.config import Config
from sqlalchemy import inspect, text

from alembic import command
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_tareas_sqlalchemy import (  # noqa: E501
    RepositorioTareasSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.sesion import FabricaSesiones
from tests.integracion.tablas import vaciar_tablas

_RAIZ = Path(__file__).resolve().parents[2]
_REVISION = "c5e1b8f4a2d7"
_ANTERIOR = "a9c4e1f7b3d2"


def _alembic() -> Config:
    # Sin el alembic.ini: su configuración de logs desactivaría los registradores
    # que ya existen en el proceso de los tests. env.py toma la URL de la aplicación.
    configuracion = Config()
    configuracion.set_main_option("script_location", str(_RAIZ / "alembic"))
    return configuracion


def _ejecutar(sql: str, **parametros: object) -> int | None:
    """Ejecuta la sentencia en su propia transacción y devuelve el id insertado."""
    sesion = FabricaSesiones()
    try:
        resultado = sesion.execute(text(sql), parametros)
        sesion.commit()
        return resultado.lastrowid
    finally:
        sesion.close()


def _workflow(nombre: str, *pasos: str) -> dict[str, int]:
    """Da de alta el workflow con esos pasos y devuelve el id de cada paso por nombre
    (el del primero si se repite)."""
    id_workflow = _ejecutar("INSERT INTO workflows (nombre) VALUES (:n)", n=nombre)
    ids: dict[str, int] = {}
    for numero, paso in enumerate(pasos, start=1):
        id_paso = _ejecutar(
            "INSERT INTO pasos_workflow (workflow_id, numero, nombre) VALUES (:w, :num, :n)",
            w=id_workflow,
            num=numero,
            n=paso,
        )
        assert id_paso is not None
        ids.setdefault(paso, id_paso)
    ids["__workflow__"] = id_workflow or 0
    return ids


def _tarea(nombre: str, id_workflow: int | None, *subtareas: str) -> tuple[int, list[int]]:
    id_tarea = _ejecutar(
        "INSERT INTO tareas (nombre, descripcion, fecha_creacion, workflow_id) "
        "VALUES (:n, 'd', '2026-11-10 09:00:00', :w)",
        n=nombre,
        w=id_workflow,
    )
    assert id_tarea is not None
    ids = [
        _ejecutar(
            "INSERT INTO subtareas (tarea_id, nombre) VALUES (:t, :n)", t=id_tarea, n=subtarea
        )
        for subtarea in subtareas
    ]
    return id_tarea, [i for i in ids if i is not None]


def _pasos_de_las_subtareas() -> dict[int, int | None]:
    sesion = FabricaSesiones()
    try:
        filas = sesion.execute(text("SELECT id, paso_id FROM subtareas")).all()
        return {fila.id: fila.paso_id for fila in filas}
    finally:
        sesion.close()


def _estado() -> tuple[bool, list[tuple], str]:
    """(si existe la columna, las subtareas, la revisión actual)."""
    sesion = FabricaSesiones()
    try:
        columnas = {c["name"] for c in inspect(sesion.connection()).get_columns("subtareas")}
        subtareas = sesion.execute(
            text("SELECT id, tarea_id, nombre, resuelta FROM subtareas ORDER BY id")
        ).all()
        revision = sesion.scalar(text("SELECT version_num FROM alembic_version"))
        return "paso_id" in columnas, [tuple(s) for s in subtareas], revision
    finally:
        sesion.close()


def _nombres_de_las_subtareas(id_tarea: int) -> list[str]:
    sesion = FabricaSesiones()
    try:
        tarea = RepositorioTareasSqlAlchemy(sesion).obtener_por_id(id_tarea)
        assert tarea is not None
        return [s.nombre for s in tarea.subtareas]
    finally:
        sesion.close()


def test_la_migracion_vincula_las_subtareas_con_el_paso_del_mismo_nombre_de_su_workflow() -> None:
    sesion = FabricaSesiones()
    try:
        vaciar_tablas(sesion)
    finally:
        sesion.close()
    command.downgrade(_alembic(), _ANTERIOR)
    try:
        assert _estado()[0] is False
        ventas = _workflow("Ventas", "Contacto", "Propuesta", "Cierre", "Seguimiento")
        compras = _workflow("Compras", "Pedido", "Contacto")
        # Los pasos que faltaban se añadieron al final, después de una subtarea a mano.
        (
            venta,
            (
                contacto,
                duplicada,
                pedido,
                a_mano,
                cierre,
                propuesta,
                minusculas,
            ),
        ) = _tarea(
            "Venta",
            ventas["__workflow__"],
            "Contacto",
            "Contacto",
            "Pedido",
            "Llamar",
            "Cierre",
            "Propuesta",
            "seguimiento",
        )
        _, (sin_workflow,) = _tarea("Leer", None, "Contacto")
        _, (de_compras,) = _tarea("Compra", compras["__workflow__"], "Contacto")
    except BaseException:
        command.upgrade(_alembic(), "head")
        raise

    command.upgrade(_alembic(), "head")

    assert _estado()[0] is True
    assert _estado()[2] == _REVISION
    assert _pasos_de_las_subtareas() == {
        contacto: ventas["Contacto"],
        # Varias con el nombre del mismo paso: solo la de menor id.
        duplicada: None,
        # Nombre de un paso de otro workflow, no del de su tarea.
        pedido: None,
        a_mano: None,
        cierre: ventas["Cierre"],
        propuesta: ventas["Propuesta"],
        # El nombre tiene que ser exactamente el mismo.
        minusculas: None,
        # Una tarea sin workflow no se toca.
        sin_workflow: None,
        de_compras: compras["Contacto"],
    }
    # Y se muestran en el orden de los pasos, con las demás después por orden de alta.
    assert _nombres_de_las_subtareas(venta) == [
        "Contacto",
        "Propuesta",
        "Cierre",
        "Contacto",
        "Pedido",
        "Llamar",
        "seguimiento",
    ]


def test_deshacer_la_migracion_quita_solo_la_columna() -> None:
    sesion = FabricaSesiones()
    try:
        vaciar_tablas(sesion)
    finally:
        sesion.close()
    ventas = _workflow("Ventas", "Contacto", "Cierre")
    _tarea("Venta", ventas["__workflow__"], "Cierre", "Contacto", "Llamar")
    _ejecutar("UPDATE subtareas SET paso_id = :p WHERE nombre = 'Contacto'", p=ventas["Contacto"])
    _, subtareas, revision = _estado()
    assert revision == _REVISION

    try:
        command.downgrade(_alembic(), _ANTERIOR)
        assert _estado() == (False, subtareas, _ANTERIOR)
    finally:
        command.upgrade(_alembic(), "head")

    # Al volver a aplicarla se vinculan de nuevo por su nombre.
    assert _estado() == (True, subtareas, _REVISION)
    ids = [s[0] for s in subtareas]
    assert _pasos_de_las_subtareas() == {
        ids[0]: ventas["Cierre"],
        ids[1]: ventas["Contacto"],
        ids[2]: None,
    }
