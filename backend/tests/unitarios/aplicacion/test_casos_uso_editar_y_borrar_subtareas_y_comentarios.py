from datetime import UTC, datetime, timedelta, timezone

import pytest

from gestor_tareas.aplicacion.comentario.anadir_comentario import AnadirComentario
from gestor_tareas.aplicacion.comentario.editar_comentario import EditarComentario
from gestor_tareas.aplicacion.comentario.eliminar_comentario import EliminarComentario
from gestor_tareas.aplicacion.tarea.anadir_subtarea import AnadirSubtarea
from gestor_tareas.aplicacion.tarea.editar_subtarea import EditarSubtarea
from gestor_tareas.aplicacion.tarea.marcar_subtarea_resuelta import MarcarSubtareaResuelta
from gestor_tareas.dominio.comentario.entidades import Comentario
from gestor_tareas.dominio.excepciones import EntidadNoEncontradaError
from gestor_tareas.dominio.tarea.entidades import Subtarea, Tarea
from tests.unitarios.aplicacion.dobles import (
    RepositorioComentariosFalso,
    RepositorioPersonasFalso,
    RepositorioTareasFalso,
)

_FECHA = datetime(2026, 11, 10, 9, 0, 0)
_ALTA = datetime(2026, 11, 10, 8, 0, 0, tzinfo=UTC)


def _repos(*personas: str) -> tuple[RepositorioTareasFalso, RepositorioPersonasFalso, int]:
    tareas = RepositorioTareasFalso()
    id_tarea = tareas.crear(Tarea(nombre="Mudanza", descripcion="d", fecha_creacion=_FECHA)).id
    return tareas, RepositorioPersonasFalso(*personas), id_tarea


def test_editar_subtarea_sustituye_sus_datos_y_conserva_el_estado_resuelta() -> None:
    tareas, personas, id_tarea = _repos("Ana")
    AnadirSubtarea(tareas, personas).ejecutar(id_tarea, "Embalar")
    AnadirSubtarea(tareas, personas).ejecutar(id_tarea, "Limpiar")
    MarcarSubtareaResuelta(tareas).ejecutar(id_tarea, 1, True)

    tarea = EditarSubtarea(tareas, personas).ejecutar(
        id_tarea, 1, "Embalar libros", asignado="ANA", prioridad=3
    )

    esperadas = [
        Subtarea(id=1, nombre="Embalar libros", asignado="Ana", prioridad=3, resuelta=True),
        Subtarea(id=2, nombre="Limpiar"),
    ]
    assert tarea.subtareas == esperadas
    assert tareas.obtener_por_id(id_tarea).subtareas == esperadas
    assert [p.nombre for p in personas.listar()] == ["Ana"]


def test_editar_subtarea_sin_persona_ni_prioridad_las_vacia_y_una_persona_nueva_se_da_de_alta() -> (
    None
):
    tareas, personas, id_tarea = _repos()
    AnadirSubtarea(tareas, personas).ejecutar(id_tarea, "Embalar", asignado="Ana", prioridad=2)
    caso = EditarSubtarea(tareas, personas)

    vaciada = caso.ejecutar(id_tarea, 1, "Embalar")
    assert vaciada.subtareas == [Subtarea(id=1, nombre="Embalar")]

    con_luis = caso.ejecutar(id_tarea, 1, "Embalar", asignado="Luis", prioridad=None)
    assert con_luis.subtareas == [Subtarea(id=1, nombre="Embalar", asignado="Luis")]
    assert [p.nombre for p in personas.listar()] == ["Ana", "Luis"]


def test_editar_una_subtarea_inexistente_o_de_otra_tarea_lanza_error() -> None:
    tareas, personas, id_tarea = _repos()
    otra = tareas.crear(Tarea(nombre="Viaje", descripcion="d", fecha_creacion=_FECHA)).id
    AnadirSubtarea(tareas, personas).ejecutar(otra, "Reservar")
    caso = EditarSubtarea(tareas, personas)

    with pytest.raises(EntidadNoEncontradaError, match="No existe la tarea con id 99$"):
        caso.ejecutar(99, 1, "X")
    with pytest.raises(
        EntidadNoEncontradaError,
        match=f"No existe la subtarea con id 1 en la tarea con id {id_tarea}$",
    ):
        caso.ejecutar(id_tarea, 1, "X")
    assert tareas.obtener_por_id(otra).subtareas == [Subtarea(id=1, nombre="Reservar")]


def _con_comentario() -> tuple[RepositorioTareasFalso, RepositorioComentariosFalso, int, int]:
    tareas, _, id_tarea = _repos()
    comentarios = RepositorioComentariosFalso(tareas)
    comentario = AnadirComentario(comentarios, lambda: _ALTA).ejecutar(id_tarea, "Llamar")
    return tareas, comentarios, id_tarea, comentario.id


def test_editar_comentario_cambia_el_texto_conserva_el_alta_y_pone_editado_en_utc() -> None:
    _, comentarios, id_tarea, id_comentario = _con_comentario()
    madrid = timezone(timedelta(hours=1))
    reloj = lambda: datetime(2026, 11, 10, 17, 30, 5, 987654, tzinfo=madrid)  # noqa: E731

    comentario = EditarComentario(comentarios, reloj).ejecutar(
        id_tarea, id_comentario, "Llamar\nmañana"
    )

    esperado = Comentario(
        id=id_comentario,
        id_tarea=id_tarea,
        texto="Llamar\nmañana",
        creado=_ALTA,
        editado=datetime(2026, 11, 10, 16, 30, 5, tzinfo=UTC),
    )
    assert comentario == esperado
    assert comentario.editado.utcoffset() == timedelta(0)
    assert comentarios.comentarios == [esperado]


def test_un_comentario_nuevo_no_esta_editado() -> None:
    _, comentarios, _, _ = _con_comentario()

    assert [c.editado for c in comentarios.comentarios] == [None]


def test_eliminar_comentario_lo_quita_del_historico() -> None:
    _, comentarios, id_tarea, id_comentario = _con_comentario()
    otro = AnadirComentario(comentarios, lambda: _ALTA).ejecutar(id_tarea, "Otro")

    EliminarComentario(comentarios).ejecutar(id_tarea, id_comentario)

    assert comentarios.comentarios == [otro]


@pytest.mark.parametrize(
    "operacion",
    [
        lambda repo, i, c: EditarComentario(repo).ejecutar(i, c, "Otro"),
        lambda repo, i, c: EliminarComentario(repo).ejecutar(i, c),
    ],
    ids=["editar", "eliminar"],
)
def test_operar_sobre_un_comentario_inexistente_o_de_otra_tarea_lanza_error(operacion) -> None:
    tareas, comentarios, id_tarea, id_comentario = _con_comentario()
    otra = tareas.crear(Tarea(nombre="Viaje", descripcion="d", fecha_creacion=_FECHA)).id
    antes = list(comentarios.comentarios)

    with pytest.raises(EntidadNoEncontradaError, match="No existe la tarea con id 99$"):
        operacion(comentarios, 99, id_comentario)
    with pytest.raises(
        EntidadNoEncontradaError,
        match=f"No existe el comentario con id {id_comentario} en la tarea con id {otra}$",
    ):
        operacion(comentarios, otra, id_comentario)
    with pytest.raises(
        EntidadNoEncontradaError,
        match=f"No existe el comentario con id 999 en la tarea con id {id_tarea}$",
    ):
        operacion(comentarios, id_tarea, 999)
    assert comentarios.comentarios == antes
