"""Migración de los comentarios de 5000 caracteres: la columna `texto` de las tres
tablas de comentarios pasa de TEXT a MEDIUMTEXT sin cambiar ningún comentario, y se
deshace volviendo a TEXT solo si todos los comentarios caben."""

from datetime import datetime
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import inspect, text

from alembic import command
from gestor_tareas.infraestructura.persistencia.modelos import (
    PasoWorkflowModelo,
    SubtareaModelo,
    TareaModelo,
    WorkflowModelo,
)
from gestor_tareas.infraestructura.persistencia.sesion import FabricaSesiones
from tests.integracion.tablas import vaciar_tablas

_RAIZ = Path(__file__).resolve().parents[2]
_REVISION = "b3e7d1a9c5f2"
_ANTERIOR = "f1a6c3e8b2d9"
_TABLAS = ("comentarios", "comentarios_subtarea", "comentarios_paso_workflow")
_CREADO = "2026-11-10 16:30:05"
_TEXTOS = [
    '<p><strong>Uno</strong> <span style="color:#e03131">rojo</span> &amp; ñandú</p>',
    f"<p>{'á' * 5000}</p>",
    '<p>Captura<img src="/api/v1/imagenes/' + "a" * 32 + '" alt="Captura"></p>',
]


def _alembic() -> Config:
    configuracion = Config()
    configuracion.set_main_option("script_location", str(_RAIZ / "alembic"))
    return configuracion


def _ids_padre() -> dict[str, tuple[str, int]]:
    sesion = FabricaSesiones()
    try:
        vaciar_tablas(sesion)
        tarea = TareaModelo(
            nombre="Mudanza", descripcion="d", fecha_creacion=datetime(2026, 11, 10, 9)
        )
        workflow = WorkflowModelo(nombre="Ventas")
        sesion.add_all([tarea, workflow])
        sesion.flush()
        subtarea = SubtareaModelo(tarea_id=tarea.id, nombre="Cajas")
        paso = PasoWorkflowModelo(workflow_id=workflow.id, numero=1, nombre="Contacto")
        sesion.add_all([subtarea, paso])
        sesion.commit()
        return {
            "comentarios": ("tarea_id", tarea.id),
            "comentarios_subtarea": ("subtarea_id", subtarea.id),
            "comentarios_paso_workflow": ("paso_id", paso.id),
        }
    finally:
        sesion.close()


def _ejecutar(sql: str, **parametros: object) -> None:
    sesion = FabricaSesiones()
    try:
        sesion.execute(text(sql), parametros)
        sesion.commit()
    finally:
        sesion.close()


def _insertar(tabla: str, columna: str, id_padre: int, texto: str) -> None:
    _ejecutar(
        f"INSERT INTO {tabla} ({columna}, texto, creado) VALUES (:p, :t, :c)",  # noqa: S608
        p=id_padre,
        t=texto,
        c=_CREADO,
    )


def _estado() -> tuple[str, dict[str, tuple[str, list[tuple]]]]:
    """(la revisión actual, por tabla: el tipo de `texto` y todas sus filas por id)."""
    sesion = FabricaSesiones()
    try:
        inspector = inspect(sesion.connection())
        tablas = {}
        for tabla in _TABLAS:
            columna = next(c for c in inspector.get_columns(tabla) if c["name"] == "texto")
            assert columna["nullable"] is False
            filas = sesion.execute(text(f"SELECT * FROM {tabla} ORDER BY id")).all()  # noqa: S608
            # Solo el tipo base: con otra intercalación del servidor el inspector
            # añade " COLLATE …" (p. ej. "TEXT COLLATE utf8mb4_unicode_ci").
            tipo = str(columna["type"]).upper().split(" COLLATE ")[0]
            tablas[tabla] = (tipo, [tuple(f) for f in filas])
        revision = sesion.scalar(text("SELECT version_num FROM alembic_version"))
        return revision, tablas
    finally:
        sesion.close()


def _con_tipo(tipo: str, tablas: dict[str, tuple[str, list[tuple]]]) -> dict:
    return {tabla: (tipo, filas) for tabla, (_, filas) in tablas.items()}


def test_la_migracion_amplia_los_comentarios_sin_cambiarlos_y_se_deshace() -> None:
    padres = _ids_padre()
    command.downgrade(_alembic(), _ANTERIOR)
    try:
        for tabla, (columna, id_padre) in padres.items():
            for texto in _TEXTOS:
                _insertar(tabla, columna, id_padre, texto)
        revision, antes = _estado()
        assert revision == _ANTERIOR
        assert {tipo for tipo, _ in antes.values()} == {"TEXT"}

        command.upgrade(_alembic(), _REVISION)

        assert _estado() == (_REVISION, _con_tipo("MEDIUMTEXT", antes))
        # Cabe un comentario de 50000 caracteres de 4 bytes (lo que no cabía en TEXT).
        columna, id_padre = padres["comentarios"]
        _insertar("comentarios", columna, id_padre, "😀" * 50000)
        _ejecutar("DELETE FROM comentarios WHERE texto = :t", t="😀" * 50000)

        command.downgrade(_alembic(), _ANTERIOR)

        assert _estado() == (_ANTERIOR, antes)
    finally:
        command.upgrade(_alembic(), "head")


def test_deshacer_la_migracion_se_niega_si_un_comentario_no_cabe_en_text() -> None:
    padres = _ids_padre()
    command.downgrade(_alembic(), _REVISION)
    try:
        columna, id_padre = padres["comentarios_subtarea"]
        _insertar("comentarios_subtarea", columna, id_padre, f"<p>{'á' * 40000}</p>")
        antes = _estado()

        with pytest.raises(RuntimeError, match="No se puede deshacer la migración") as error:
            command.downgrade(_alembic(), _ANTERIOR)

        assert "comentarios_subtarea" in str(error.value)
        assert "65535 bytes" in str(error.value)
        assert _estado() == antes
    finally:
        command.upgrade(_alembic(), "head")
