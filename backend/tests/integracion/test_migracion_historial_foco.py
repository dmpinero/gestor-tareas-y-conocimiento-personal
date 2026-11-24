"""Migración del historial del foco: crea la tabla `historial_foco`, abre el periodo
en curso del foco que hubiera, no cambia ningún otro dato y se deshace borrándola."""

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
_REVISION = "483e78c30e26"
_ANTERIOR = "e6a1c9d3f5b7"


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
            nombre="Migración portal", descripcion="d", fecha_creacion=datetime(2026, 11, 10, 9)
        )
        sesion.add(tarea)
        sesion.flush()
        subtarea = SubtareaModelo(tarea_id=tarea.id, nombre="Copiar")
        sesion.add(subtarea)
        sesion.commit()
        return tarea.id, subtarea.id

    return _sesion_y_cerrar(preparar)


def _ejecutar(sql: str, **parametros) -> None:
    def ejecutar(sesion) -> None:
        sesion.execute(text(sql), parametros)
        sesion.commit()

    _sesion_y_cerrar(ejecutar)


def _filas(tabla: str) -> list[tuple]:
    return _sesion_y_cerrar(
        lambda s: [tuple(f) for f in s.execute(text(f"SELECT * FROM {tabla} ORDER BY 1")).all()]
    )


def _foto() -> dict:
    def foto(sesion) -> dict:
        tablas = set(inspect(sesion.connection()).get_table_names())
        return {
            "tablas": tablas,
            "revision": sesion.scalar(text("SELECT version_num FROM alembic_version")),
        }

    datos = _sesion_y_cerrar(foto)
    for tabla in ("tareas", "subtareas", "foco_trabajo"):
        datos[tabla] = _filas(tabla)
    return datos


def _historial() -> list[tuple]:
    return _sesion_y_cerrar(
        lambda s: [
            tuple(f)
            for f in s.execute(
                text(
                    "SELECT tarea_id, subtarea_id, tarea_nombre, subtarea_nombre, desde, hasta "
                    "FROM historial_foco ORDER BY id"
                )
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
def test_con_foco_abre_su_periodo_en_curso_sin_cambiar_los_datos_y_se_deshace() -> None:
    id_tarea, id_subtarea = _preparar_datos()
    command.downgrade(_alembic(), _ANTERIOR)
    _ejecutar(
        "INSERT INTO foco_trabajo (id, tarea_id, subtarea_id, desde) "
        "VALUES (1, :t, :s, '2026-11-24 10:00:00')",
        t=id_tarea,
        s=id_subtarea,
    )
    antes = _foto()
    assert "historial_foco" not in antes["tablas"]

    command.upgrade(_alembic(), _REVISION)

    despues = _foto()
    assert despues["tablas"] == antes["tablas"] | {"historial_foco"}
    for clave in ("tareas", "subtareas", "foco_trabajo"):
        assert despues[clave] == antes[clave]
    assert despues["revision"] == _REVISION
    assert _historial() == [
        (id_tarea, id_subtarea, "Migración portal", "Copiar", datetime(2026, 11, 24, 10), None)
    ]

    # Solo un periodo en curso.
    with pytest.raises(DBAPIError, match="uq_historial_foco_en_curso"):
        _ejecutar(
            "INSERT INTO historial_foco (tarea_id, tarea_nombre, desde) "
            "VALUES (:t, 'x', '2026-11-24 11:00:00')",
            t=id_tarea,
        )
    # Borrar la subtarea y la tarea deja sus ids a NULL y conserva el periodo.
    _ejecutar("DELETE FROM subtareas WHERE id = :s", s=id_subtarea)
    _ejecutar("DELETE FROM tareas WHERE id = :t", t=id_tarea)
    assert _historial() == [
        (None, None, "Migración portal", "Copiar", datetime(2026, 11, 24, 10), None)
    ]

    command.downgrade(_alembic(), _ANTERIOR)

    final = _foto()
    assert final["tablas"] == antes["tablas"]
    assert final["revision"] == _ANTERIOR


@pytest.mark.usefixtures("volver_a_la_ultima")
def test_sin_foco_crea_el_historial_vacio_y_sube_baja_y_sube_sin_cambiar_datos() -> None:
    _preparar_datos()
    command.downgrade(_alembic(), _ANTERIOR)
    antes = _foto()

    command.upgrade(_alembic(), _REVISION)
    assert _historial() == []
    command.downgrade(_alembic(), _ANTERIOR)
    command.upgrade(_alembic(), _REVISION)

    despues = _foto()
    assert despues["tablas"] == antes["tablas"] | {"historial_foco"}
    for clave in ("tareas", "subtareas", "foco_trabajo"):
        assert despues[clave] == antes[clave]
    assert _historial() == []
