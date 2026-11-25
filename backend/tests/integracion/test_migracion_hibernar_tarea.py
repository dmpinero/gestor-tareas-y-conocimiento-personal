"""Migración de la hibernación de las tareas: añade la columna con el instante desde el
que la tarea está hibernada, vacía (ninguna tarea existente queda hibernada) y sin
cambiar ningún otro dato; se deshace quitando solo esa columna."""

from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import inspect, text

from alembic import command
from gestor_tareas.infraestructura.persistencia.sesion import FabricaSesiones
from tests.integracion.tablas import vaciar_tablas

_RAIZ = Path(__file__).resolve().parents[2]
_REVISION = "b7d3e5f9a1c4"
_ANTERIOR = "483e78c30e26"


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


def _ejecutar(sql: str, **parametros) -> None:
    def ejecutar(sesion) -> None:
        sesion.execute(text(sql), parametros)
        sesion.commit()

    _sesion_y_cerrar(ejecutar)


_COLUMNAS_ANTERIORES = (
    "id, nombre, prioridad, descripcion, fecha_creacion, fecha_vencimiento, completada, "
    "congelada_en"
)


def _foto() -> dict:
    def foto(sesion) -> dict:
        columnas = {
            c["name"]: (str(c["type"]), c["nullable"])
            for c in inspect(sesion.connection()).get_columns("tareas")
        }
        return {
            "columnas": columnas,
            "tareas": [
                tuple(f)
                for f in sesion.execute(
                    text(f"SELECT {_COLUMNAS_ANTERIORES} FROM tareas ORDER BY id")
                ).all()
            ],
            "revision": sesion.scalar(text("SELECT version_num FROM alembic_version")),
        }

    return _sesion_y_cerrar(foto)


def _hibernadas() -> list:
    return _sesion_y_cerrar(
        lambda s: list(s.scalars(text("SELECT hibernada_desde FROM tareas ORDER BY id")))
    )


@pytest.fixture
def volver_a_la_ultima():
    try:
        yield
    finally:
        command.upgrade(_alembic(), "head")


@pytest.mark.usefixtures("volver_a_la_ultima")
def test_anade_la_columna_vacia_sin_cambiar_los_datos_y_se_deshace() -> None:
    _sesion_y_cerrar(vaciar_tablas)
    command.downgrade(_alembic(), _ANTERIOR)
    _ejecutar(
        "INSERT INTO tareas (nombre, descripcion, fecha_creacion, fecha_vencimiento, "
        "completada, congelada_en) VALUES "
        "('pendiente', 'd', '2026-11-10 09:00:00', '2026-12-01 10:00:00', 0, NULL), "
        "('completada', 'd', '2026-11-10 09:00:00', NULL, 1, '2026-11-20 08:00:00')"
    )
    antes = _foto()
    assert "hibernada_desde" not in antes["columnas"]
    assert antes["revision"] == _ANTERIOR

    command.upgrade(_alembic(), _REVISION)

    despues = _foto()
    assert despues["revision"] == _REVISION
    assert despues["tareas"] == antes["tareas"]
    assert set(despues["columnas"]) == set(antes["columnas"]) | {"hibernada_desde"}
    assert despues["columnas"]["hibernada_desde"] == ("DATETIME", True)
    assert _hibernadas() == [None, None]

    command.downgrade(_alembic(), _ANTERIOR)

    final = _foto()
    assert final == antes

    # Y se puede volver a aplicar.
    command.upgrade(_alembic(), _REVISION)
    assert _foto()["tareas"] == antes["tareas"]
    assert _hibernadas() == [None, None]
