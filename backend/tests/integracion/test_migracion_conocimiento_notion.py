"""Migración del índice local de Notion: crea las páginas, sus trozos (FULLTEXT y en
cascada) y la fila del estado de la sincronización, sin cambiar las tareas; se
deshace quitando solo esas tablas."""

from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from alembic import command
from gestor_tareas.infraestructura.persistencia.sesion import FabricaSesiones
from tests.integracion.tablas import vaciar_tablas

_RAIZ = Path(__file__).resolve().parents[2]
_REVISION = "e9c3a7f1b5d2"
_ANTERIOR = "d7f2b9e4a6c1"
_TABLAS = {"notion_paginas", "notion_fragmentos", "notion_sincronizacion"}


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


@pytest.fixture
def volver_a_la_ultima():
    try:
        yield
    finally:
        command.upgrade(_alembic(), "head")


@pytest.mark.usefixtures("volver_a_la_ultima")
def test_crea_el_indice_vacio_con_fulltext_y_cascada_sin_cambiar_las_tareas_y_se_deshace() -> None:
    _sesion_y_cerrar(vaciar_tablas)
    command.downgrade(_alembic(), _ANTERIOR)
    _ejecutar(
        "INSERT INTO tareas (id, nombre, descripcion, fecha_creacion) VALUES "
        "(1, 'A', 'd', '2026-11-10 09:00:00')"
    )
    antes = _foto()
    assert not (_TABLAS & antes["tablas"])
    assert antes["revision"] == _ANTERIOR

    command.upgrade(_alembic(), _REVISION)

    despues = _foto()
    assert despues["revision"] == _REVISION
    assert despues["tareas"] == antes["tareas"]
    assert despues["tablas"] == antes["tablas"] | _TABLAS
    assert _consultar("SELECT COUNT(*) FROM notion_paginas") == [(0,)]
    assert _consultar("SELECT COUNT(*) FROM notion_fragmentos") == [(0,)]
    # Nunca sincronizado y ninguna sincronización en curso.
    assert _consultar(
        "SELECT id, ultima_sincronizacion, en_curso_desde FROM notion_sincronizacion"
    ) == [(1, None, None)]
    with pytest.raises(DBAPIError, match="ck_notion_sincronizacion_una_fila"):
        _ejecutar("INSERT INTO notion_sincronizacion (id) VALUES (2)")

    _ejecutar(
        "INSERT INTO notion_paginas (id, titulo, url, editada_en, sincronizada_en) VALUES "
        "('p1', 'Receta', 'https://n.so/p1', '2026-11-20 09:00:00', '2026-11-26 12:00:00'),"
        "('p2', 'Otra', 'https://n.so/p2', '2026-11-20 09:00:00', '2026-11-26 12:00:00')"
    )
    _ejecutar(
        "INSERT INTO notion_fragmentos (pagina_id, orden, texto) VALUES "
        "('p1', 0, 'La paella lleva azafrán'), ('p1', 1, 'Y arroz'), ('p2', 0, 'Nada más')"
    )
    with pytest.raises(IntegrityError):
        _ejecutar("INSERT INTO notion_fragmentos (pagina_id, orden, texto) VALUES ('p1', 0, 'x')")
    with pytest.raises(IntegrityError):
        _ejecutar("INSERT INTO notion_fragmentos (pagina_id, orden, texto) VALUES ('no', 0, 'x')")
    # La búsqueda de texto completo funciona sobre el índice nuevo.
    assert _consultar(
        "SELECT pagina_id, orden FROM notion_fragmentos "
        "WHERE MATCH(texto) AGAINST ('azafran' IN NATURAL LANGUAGE MODE)"
    ) == [("p1", 0)]
    _ejecutar("DELETE FROM notion_paginas WHERE id = 'p1'")
    assert _consultar("SELECT pagina_id, orden FROM notion_fragmentos") == [("p2", 0)]

    command.downgrade(_alembic(), _ANTERIOR)

    final = _foto()
    assert final["tablas"] == antes["tablas"]
    assert final["revision"] == _ANTERIOR
    assert final["tareas"] == antes["tareas"]

    # Y se puede volver a aplicar.
    command.upgrade(_alembic(), _REVISION)
    assert _consultar("SELECT COUNT(*) FROM notion_paginas") == [(0,)]
