"""Migración de las subtareas en Siguientes: ``cola_siguientes`` gana ``subtarea_id``
y un id propio, conservando las filas existentes como entradas de tarea entera (con
su lista y su posición); se deshace perdiendo solo las entradas de subtareas."""

from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from alembic import command
from gestor_tareas.infraestructura.persistencia.sesion import FabricaSesiones
from tests.integracion.tablas import vaciar_tablas

_RAIZ = Path(__file__).resolve().parents[2]
_REVISION = "a3d8f5c2e7b9"
_ANTERIOR = "e9c3a7f1b5d2"


def _alembic() -> Config:
    # Sin el alembic.ini: su configuración de logs desactivaría los registradores
    # que ya existen en el proceso de los tests. env.py toma la URL de la aplicación.
    configuracion = Config()
    configuracion.set_main_option("script_location", str(_RAIZ / "alembic"))
    return configuracion


def _sesion_y_cerrar(funcion):
    sesion = FabricaSesiones()
    try:
        return funcion(sesion)
    finally:
        sesion.close()


def _ejecutar(sql: str) -> None:
    def ejecutar(sesion) -> None:
        sesion.execute(text(sql))
        sesion.commit()

    _sesion_y_cerrar(ejecutar)


def _consultar(sql: str) -> list[tuple]:
    return _sesion_y_cerrar(lambda s: [tuple(f) for f in s.execute(text(sql)).all()])


def _columnas() -> set[str]:
    return _sesion_y_cerrar(
        lambda s: {c["name"] for c in inspect(s.connection()).get_columns("cola_siguientes")}
    )


def _revision() -> str:
    return _consultar("SELECT version_num FROM alembic_version")[0][0]


def _tareas() -> list[tuple]:
    return _consultar("SELECT id, nombre, completada FROM tareas ORDER BY id")


@pytest.fixture
def volver_a_la_ultima():
    try:
        yield
    finally:
        command.upgrade(_alembic(), "head")


@pytest.mark.usefixtures("volver_a_la_ultima")
def test_conserva_las_filas_como_tareas_enteras_admite_subtareas_y_se_deshace() -> None:
    _sesion_y_cerrar(vaciar_tablas)
    command.downgrade(_alembic(), _ANTERIOR)
    _ejecutar(
        "INSERT INTO tareas (id, nombre, descripcion, fecha_creacion) VALUES "
        "(1, 'A', 'd', '2026-11-10 09:00:00'), (2, 'B', 'd', '2026-11-10 09:00:00'), "
        "(3, 'C', 'd', '2026-11-10 09:00:00')"
    )
    _ejecutar("INSERT INTO subtareas (id, tarea_id, nombre) VALUES (10, 1, 'S1'), (11, 1, 'S2')")
    _ejecutar(
        "INSERT INTO cola_siguientes (tarea_id, lista, posicion) VALUES "
        "(1, 'siguientes', 1), (2, 'siguientes', 0), (3, 'sugerencias', 0)"
    )
    tareas = _tareas()
    assert _columnas() == {"tarea_id", "lista", "posicion"}

    command.upgrade(_alembic(), _REVISION)

    assert _revision() == _REVISION
    assert _tareas() == tareas
    assert _columnas() == {"id", "tarea_id", "subtarea_id", "subtarea_clave", "lista", "posicion"}
    assert _consultar(
        "SELECT tarea_id, subtarea_id, lista, posicion FROM cola_siguientes ORDER BY tarea_id"
    ) == [(1, None, "siguientes", 1), (2, None, "siguientes", 0), (3, None, "sugerencias", 0)]
    # Una tarea y sus subtareas a la vez, cada entrada una sola vez (también la de la
    # tarea entera, con NULL), y borrar la subtarea borra su entrada.
    _ejecutar(
        "INSERT INTO cola_siguientes (tarea_id, subtarea_id, lista, posicion) VALUES "
        "(1, 10, 'siguientes', 2), (1, 11, 'sugerencias', 1)"
    )
    for subtarea in ("NULL", "10"):
        with pytest.raises(IntegrityError):
            _ejecutar(
                "INSERT INTO cola_siguientes (tarea_id, subtarea_id, lista, posicion) "
                f"VALUES (1, {subtarea}, 'sugerencias', 5)"
            )
    with pytest.raises(IntegrityError):
        _ejecutar(
            "INSERT INTO cola_siguientes (tarea_id, subtarea_id, lista, posicion) "
            "VALUES (2, 999, 'siguientes', 5)"
        )
    _ejecutar("DELETE FROM subtareas WHERE id = 10")
    assert _consultar(
        "SELECT tarea_id, subtarea_id FROM cola_siguientes ORDER BY tarea_id, subtarea_clave"
    ) == [(1, None), (1, 11), (2, None), (3, None)]

    command.downgrade(_alembic(), _ANTERIOR)

    assert _revision() == _ANTERIOR
    assert _tareas() == tareas
    assert _columnas() == {"tarea_id", "lista", "posicion"}
    # Se pierden las entradas de subtareas; las de tareas enteras siguen como estaban.
    assert _consultar(
        "SELECT tarea_id, lista, posicion FROM cola_siguientes ORDER BY tarea_id"
    ) == [(1, "siguientes", 1), (2, "siguientes", 0), (3, "sugerencias", 0)]
    with pytest.raises(IntegrityError):
        _ejecutar(
            "INSERT INTO cola_siguientes (tarea_id, lista, posicion) VALUES (1, 'siguientes', 9)"
        )
    _ejecutar("DELETE FROM tareas WHERE id = 3")
    assert _consultar("SELECT tarea_id FROM cola_siguientes ORDER BY tarea_id") == [(1,), (2,)]

    # Y se puede volver a aplicar.
    command.upgrade(_alembic(), _REVISION)
    assert _consultar("SELECT tarea_id, subtarea_id FROM cola_siguientes ORDER BY tarea_id") == [
        (1, None),
        (2, None),
    ]
