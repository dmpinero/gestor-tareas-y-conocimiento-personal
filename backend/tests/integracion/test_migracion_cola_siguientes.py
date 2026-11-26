"""Migración de la cola de siguientes tareas: crea la tabla de la cola vacía, sin
cambiar las tareas, con borrado en cascada al borrar la tarea; se deshace quitando
solo esa tabla."""

from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from alembic import command
from gestor_tareas.infraestructura.persistencia.sesion import FabricaSesiones
from tests.integracion.tablas import vaciar_tablas

_RAIZ = Path(__file__).resolve().parents[2]
_REVISION = "d7f2b9e4a6c1"
_ANTERIOR = "c4e8a2f6b1d9"


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


def _foto() -> dict:
    def foto(sesion) -> dict:
        return {
            "tablas": set(inspect(sesion.connection()).get_table_names()),
            "tareas": [
                tuple(f)
                for f in sesion.execute(
                    text("SELECT id, nombre, descripcion, fecha_creacion FROM tareas ORDER BY id")
                ).all()
            ],
            "revision": sesion.scalar(text("SELECT version_num FROM alembic_version")),
        }

    return _sesion_y_cerrar(foto)


def _cola() -> list[tuple[int, int]]:
    return _sesion_y_cerrar(
        lambda s: [
            tuple(f)
            for f in s.execute(
                text("SELECT tarea_id, posicion FROM cola_siguientes ORDER BY tarea_id")
            ).all()
        ]
    )


@pytest.fixture
def volver_a_la_ultima():
    try:
        yield
    finally:
        command.upgrade(_alembic(), "head")


@pytest.mark.usefixtures("volver_a_la_ultima")
def test_crea_la_tabla_vacia_con_cascada_sin_cambiar_las_tareas_y_se_deshace() -> None:
    _sesion_y_cerrar(vaciar_tablas)
    command.downgrade(_alembic(), _ANTERIOR)
    _ejecutar(
        "INSERT INTO tareas (id, nombre, descripcion, fecha_creacion) VALUES "
        "(1, 'A', 'd', '2026-11-10 09:00:00'), (2, 'B', 'd', '2026-11-10 09:00:00')"
    )
    antes = _foto()
    assert "cola_siguientes" not in antes["tablas"]
    assert antes["revision"] == _ANTERIOR

    command.upgrade(_alembic(), _REVISION)

    despues = _foto()
    assert despues["revision"] == _REVISION
    assert despues["tareas"] == antes["tareas"]
    assert despues["tablas"] == antes["tablas"] | {"cola_siguientes"}
    assert _cola() == []
    # Una fila por tarea, posición obligatoria y borrado en cascada desde la tarea.
    _ejecutar("INSERT INTO cola_siguientes VALUES (1, 0), (2, 1)")
    with pytest.raises(IntegrityError):
        _ejecutar("INSERT INTO cola_siguientes VALUES (1, 5)")
    columnas = _sesion_y_cerrar(
        lambda s: {c["name"]: c for c in inspect(s.connection()).get_columns("cola_siguientes")}
    )
    assert set(columnas) == {"tarea_id", "posicion"}
    assert not columnas["posicion"]["nullable"]
    _ejecutar("DELETE FROM tareas WHERE id = 1")
    assert _cola() == [(2, 1)]

    command.downgrade(_alembic(), _ANTERIOR)

    final = _foto()
    assert final["tablas"] == antes["tablas"]
    assert final["revision"] == _ANTERIOR
    assert final["tareas"] == [t for t in antes["tareas"] if t[0] != 1]

    # Y se puede volver a aplicar.
    command.upgrade(_alembic(), _REVISION)
    assert _cola() == []
