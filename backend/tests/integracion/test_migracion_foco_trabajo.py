"""Migración del foco de trabajo: crea la tabla `foco_trabajo` (una sola fila, con
id = 1, que se borra con su tarea o su subtarea) sin cambiar ningún otro dato, y se
deshace borrándola."""

from datetime import datetime
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.exc import DBAPIError

from alembic import command
from gestor_tareas.infraestructura.persistencia.modelos import SubtareaModelo, TareaModelo
from gestor_tareas.infraestructura.persistencia.sesion import FabricaSesiones
from tests.integracion.tablas import vaciar_tablas

_RAIZ = Path(__file__).resolve().parents[2]
_REVISION = "e6a1c9d3f5b7"
_ANTERIOR = "d4e8a2c6f1b3"


def _alembic() -> Config:
    configuracion = Config()
    configuracion.set_main_option("script_location", str(_RAIZ / "alembic"))
    return configuracion


def _sesion_y_cerrar(funcion):
    sesion = FabricaSesiones()
    try:
        return funcion(sesion)
    finally:
        sesion.close()


def _preparar_datos() -> tuple[int, int]:
    def preparar(sesion) -> tuple[int, int]:
        vaciar_tablas(sesion)
        tarea = TareaModelo(
            nombre="Tarea", descripcion="d", fecha_creacion=datetime(2026, 11, 10, 9)
        )
        sesion.add(tarea)
        sesion.flush()
        subtarea = SubtareaModelo(tarea_id=tarea.id, nombre="Paso")
        sesion.add(subtarea)
        sesion.commit()
        return tarea.id, subtarea.id

    return _sesion_y_cerrar(preparar)


def _foto() -> dict:
    def foto(sesion) -> dict:
        return {
            "tablas": set(inspect(sesion.connection()).get_table_names()),
            "tareas": [tuple(f) for f in sesion.execute(text("SELECT * FROM tareas")).all()],
            "subtareas": [tuple(f) for f in sesion.execute(text("SELECT * FROM subtareas")).all()],
            "revision": sesion.scalar(text("SELECT version_num FROM alembic_version")),
        }

    return _sesion_y_cerrar(foto)


def _ejecutar(sql: str, **parametros) -> None:
    def ejecutar(sesion) -> None:
        sesion.execute(text(sql), parametros)
        sesion.commit()

    _sesion_y_cerrar(ejecutar)


def _filas_de_foco() -> list[tuple]:
    return _sesion_y_cerrar(
        lambda s: [tuple(f) for f in s.execute(text("SELECT * FROM foco_trabajo")).all()]
    )


def test_la_migracion_crea_la_tabla_sin_cambiar_los_datos_y_se_deshace() -> None:
    id_tarea, id_subtarea = _preparar_datos()
    command.downgrade(_alembic(), _ANTERIOR)
    try:
        antes = _foto()
        assert "foco_trabajo" not in antes["tablas"]
        assert len(antes["tareas"]) == 1

        command.upgrade(_alembic(), _REVISION)

        despues = _foto()
        assert despues["tablas"] == antes["tablas"] | {"foco_trabajo"}
        for clave in ("tareas", "subtareas"):
            assert despues[clave] == antes[clave]
        assert despues["revision"] == _REVISION
        assert _filas_de_foco() == []

        insertar = (
            "INSERT INTO foco_trabajo (id, tarea_id, subtarea_id, desde) "
            "VALUES (:id, :t, :s, '2026-11-24 10:00:00')"
        )
        # Solo admite la fila con id = 1.
        with pytest.raises(DBAPIError, match="ck_foco_trabajo_una_fila"):
            _ejecutar(insertar, id=2, t=id_tarea, s=None)
        # La subtarea es opcional y borrarla borra el foco.
        _ejecutar(insertar, id=1, t=id_tarea, s=id_subtarea)
        _ejecutar("DELETE FROM subtareas WHERE id = :s", s=id_subtarea)
        assert _filas_de_foco() == []
        # Borrar la tarea también borra el foco.
        _ejecutar(insertar, id=1, t=id_tarea, s=None)
        _ejecutar("DELETE FROM tareas WHERE id = :t", t=id_tarea)
        assert _filas_de_foco() == []

        command.downgrade(_alembic(), _ANTERIOR)

        final = _foto()
        assert "foco_trabajo" not in final["tablas"]
        assert final["tablas"] == antes["tablas"]
        assert final["revision"] == _ANTERIOR
    finally:
        command.upgrade(_alembic(), "head")
