"""Migración de las tareas vinculadas: crea la tabla de vínculos vacía, sin cambiar
las tareas, con borrado en cascada al borrar cualquiera de las dos tareas; se deshace
quitando solo esa tabla."""

from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import inspect, text

from alembic import command
from gestor_tareas.infraestructura.persistencia.sesion import FabricaSesiones
from tests.integracion.tablas import vaciar_tablas

_RAIZ = Path(__file__).resolve().parents[2]
_REVISION = "c4e8a2f6b1d9"
_ANTERIOR = "b7d3e5f9a1c4"


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


def _vinculos() -> list[tuple[int, int]]:
    return _sesion_y_cerrar(
        lambda s: [
            tuple(f)
            for f in s.execute(
                text("SELECT tarea_id, vinculada_id FROM tareas_vinculadas ORDER BY 1, 2")
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
        "(1, 'A', 'd', '2026-11-10 09:00:00'), (2, 'B', 'd', '2026-11-10 09:00:00'), "
        "(3, 'C', 'd', '2026-11-10 09:00:00')"
    )
    antes = _foto()
    assert "tareas_vinculadas" not in antes["tablas"]
    assert antes["revision"] == _ANTERIOR

    command.upgrade(_alembic(), _REVISION)

    despues = _foto()
    assert despues["revision"] == _REVISION
    assert despues["tareas"] == antes["tareas"]
    assert despues["tablas"] == antes["tablas"] | {"tareas_vinculadas"}
    assert _vinculos() == []
    # Clave primaria compuesta y borrado en cascada desde las dos columnas.
    _ejecutar("INSERT INTO tareas_vinculadas VALUES (1, 2), (2, 1), (1, 3), (3, 1)")
    _ejecutar("DELETE FROM tareas WHERE id = 2")
    assert _vinculos() == [(1, 3), (3, 1)]
    _ejecutar("DELETE FROM tareas WHERE id = 2")

    command.downgrade(_alembic(), _ANTERIOR)

    final = _foto()
    assert final["tablas"] == antes["tablas"]
    assert final["revision"] == _ANTERIOR
    assert final["tareas"] == [t for t in antes["tareas"] if t[0] != 2]

    # Y se puede volver a aplicar.
    command.upgrade(_alembic(), _REVISION)
    assert _vinculos() == []
