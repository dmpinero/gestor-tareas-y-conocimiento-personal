"""Migración de los comentarios con formato: la columna `texto` de las tres tablas de
comentarios pasa a TEXT y los comentarios de texto plano pasan a HTML (un párrafo
escapado por línea); al deshacerla vuelven a texto plano de hasta 500 caracteres."""

from datetime import datetime
from pathlib import Path

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
_REVISION = "a9c4e1f7b3d2"
_ANTERIOR = "d2a8e5c3f7b1"
_TABLAS = ("comentarios", "comentarios_subtarea", "comentarios_paso_workflow")
_CREADO = "2026-11-10 16:30:05"

_PLANO = 'Llamar a <Ana> & "Luis"\n\nantes de las 10'
_HTML = '<p>Llamar a &lt;Ana&gt; &amp; "Luis"</p><p></p><p>antes de las 10</p>'

_FORMATO = (
    '<p><strong>Uno</strong> <span style="color:#e03131">rojo</span><br>dos</p>'
    '<ul><li>a &amp; b</li><li><a href="https://ejemplo.com" '
    'rel="noopener noreferrer nofollow">enlace</a></li></ul>'
)
_FORMATO_EN_PLANO = "Uno rojo\ndos\na & b\nenlace"


def _alembic() -> Config:
    # Sin el alembic.ini: su configuración de logs desactivaría los registradores
    # que ya existen en el proceso de los tests. env.py toma la URL de la aplicación.
    configuracion = Config()
    configuracion.set_main_option("script_location", str(_RAIZ / "alembic"))
    return configuracion


def _ids_padre() -> dict[str, tuple[str, int]]:
    """Crea una tarea con una subtarea y un workflow con un paso; devuelve, por tabla
    de comentarios, su columna padre y el id."""
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


def _insertar(padres: dict[str, tuple[str, int]], textos: list[str]) -> None:
    sesion = FabricaSesiones()
    try:
        for tabla, (columna, id_padre) in padres.items():
            for texto in textos:
                sesion.execute(
                    text(
                        f"INSERT INTO {tabla} ({columna}, texto, creado) "
                        "VALUES (:padre, :texto, :creado)"
                    ),
                    {"padre": id_padre, "texto": texto, "creado": _CREADO},
                )
        sesion.commit()
    finally:
        sesion.close()


def _estado() -> tuple[str, dict[str, tuple[str, list[str]]]]:
    """(la revisión actual, por tabla: el tipo de `texto` y los textos por id)."""
    sesion = FabricaSesiones()
    try:
        inspector = inspect(sesion.connection())
        tablas = {}
        for tabla in _TABLAS:
            columna = next(c for c in inspector.get_columns(tabla) if c["name"] == "texto")
            assert columna["nullable"] is False
            textos = sesion.scalars(text(f"SELECT texto FROM {tabla} ORDER BY id")).all()
            tablas[tabla] = (str(columna["type"]), list(textos))
        revision = sesion.scalar(text("SELECT version_num FROM alembic_version"))
        return revision, tablas
    finally:
        sesion.close()


def _todas(tipo: str, textos: list[str]) -> dict[str, tuple[str, list[str]]]:
    return {tabla: (tipo, textos) for tabla in _TABLAS}


def test_la_migracion_pasa_los_comentarios_a_html_y_se_deshace_a_texto_plano() -> None:
    padres = _ids_padre()
    largo = f"<p><em>{'a' * 600}</em></p>"
    _insertar(padres, [_HTML, _FORMATO, largo])
    assert _estado() == (_REVISION, _todas("TEXT", [_HTML, _FORMATO, largo]))

    try:
        # Al deshacerla, el HTML pasa a texto plano y se trunca a 500 caracteres.
        command.downgrade(_alembic(), _ANTERIOR)
        assert _estado() == (
            _ANTERIOR,
            _todas("VARCHAR(500)", [_PLANO, _FORMATO_EN_PLANO, "a" * 500]),
        )
        _insertar(padres, ["Sin saltos", "x"])
    finally:
        command.upgrade(_alembic(), "head")

    # Al aplicarla, cada texto plano pasa a un párrafo escapado por línea; el formato
    # perdido al deshacerla no vuelve.
    assert _estado() == (
        _REVISION,
        _todas(
            "TEXT",
            [
                _HTML,
                "<p>Uno rojo</p><p>dos</p><p>a &amp; b</p><p>enlace</p>",
                f"<p>{'a' * 500}</p>",
                "<p>Sin saltos</p>",
                "<p>x</p>",
            ],
        ),
    )
