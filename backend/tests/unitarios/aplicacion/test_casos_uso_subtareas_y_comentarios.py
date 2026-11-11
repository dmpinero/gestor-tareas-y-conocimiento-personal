from datetime import UTC, datetime, timedelta, timezone

import pytest

from gestor_tareas.aplicacion.comentario.anadir_comentario import AnadirComentario, ahora_en_utc
from gestor_tareas.aplicacion.comentario.listar_comentarios import ListarComentarios
from gestor_tareas.aplicacion.tarea.actualizar_tarea import ActualizarTarea
from gestor_tareas.aplicacion.tarea.anadir_subtarea import AnadirSubtarea
from gestor_tareas.aplicacion.tarea.eliminar_subtarea import EliminarSubtarea
from gestor_tareas.aplicacion.tarea.marcar_subtarea_resuelta import MarcarSubtareaResuelta
from gestor_tareas.dominio.comentario.entidades import Comentario
from gestor_tareas.dominio.excepciones import EntidadNoEncontradaError
from gestor_tareas.dominio.tarea.entidades import Oportunidad, Subtarea, Tarea, TipoTarea
from tests.unitarios.aplicacion.dobles import (
    RepositorioComentariosFalso,
    RepositorioEtiquetasFalso,
    RepositorioGruposEstadosFalso,
    RepositorioPersonasFalso,
    RepositorioTareasFalso,
)

_FECHA = datetime(2026, 11, 10, 9, 0, 0)


def _repos(*personas: str) -> tuple[RepositorioTareasFalso, RepositorioPersonasFalso, int]:
    tareas = RepositorioTareasFalso()
    id_tarea = tareas.crear(Tarea(nombre="Mudanza", descripcion="d", fecha_creacion=_FECHA)).id
    return tareas, RepositorioPersonasFalso(*personas), id_tarea


def test_anadir_subtarea_la_guarda_pendiente_y_devuelve_la_tarea() -> None:
    tareas, personas, id_tarea = _repos()

    tarea = AnadirSubtarea(tareas, personas).ejecutar(id_tarea, "Embalar")

    assert tarea.subtareas == [Subtarea(id=1, nombre="Embalar")]
    assert tareas.obtener_por_id(id_tarea).subtareas == [Subtarea(id=1, nombre="Embalar")]
    assert personas.listar() == []


def test_anadir_subtarea_reutiliza_la_persona_con_su_grafia_o_la_da_de_alta() -> None:
    tareas, personas, id_tarea = _repos("Ana")
    caso = AnadirSubtarea(tareas, personas)

    caso.ejecutar(id_tarea, "Camión", asignado="ANA", prioridad=2)
    tarea = caso.ejecutar(id_tarea, "Cajas", asignado="Luis", prioridad=None)

    assert tarea.subtareas == [
        Subtarea(id=1, nombre="Camión", asignado="Ana", prioridad=2),
        Subtarea(id=2, nombre="Cajas", asignado="Luis"),
    ]
    assert [p.nombre for p in personas.listar()] == ["Ana", "Luis"]


def test_anadir_subtarea_a_una_tarea_que_no_existe_lanza_error() -> None:
    tareas, personas, _ = _repos()

    with pytest.raises(EntidadNoEncontradaError, match="No existe la tarea con id 99"):
        AnadirSubtarea(tareas, personas).ejecutar(99, "Embalar")


def test_marcar_subtarea_resuelta_y_reabrirla() -> None:
    tareas, personas, id_tarea = _repos()
    AnadirSubtarea(tareas, personas).ejecutar(id_tarea, "Embalar")
    AnadirSubtarea(tareas, personas).ejecutar(id_tarea, "Limpiar")
    caso = MarcarSubtareaResuelta(tareas)

    resuelta = caso.ejecutar(id_tarea, 1, True)
    assert [(s.nombre, s.resuelta) for s in resuelta.subtareas] == [
        ("Embalar", True),
        ("Limpiar", False),
    ]

    reabierta = caso.ejecutar(id_tarea, 1, False)
    assert [s.resuelta for s in reabierta.subtareas] == [False, False]
    assert [s.resuelta for s in tareas.obtener_por_id(id_tarea).subtareas] == [False, False]


def test_eliminar_subtarea_la_quita_de_la_tarea() -> None:
    tareas, personas, id_tarea = _repos()
    AnadirSubtarea(tareas, personas).ejecutar(id_tarea, "Embalar")
    AnadirSubtarea(tareas, personas).ejecutar(id_tarea, "Limpiar")

    tarea = EliminarSubtarea(tareas).ejecutar(id_tarea, 1)

    assert [s.nombre for s in tarea.subtareas] == ["Limpiar"]
    assert [s.nombre for s in tareas.obtener_por_id(id_tarea).subtareas] == ["Limpiar"]


@pytest.mark.parametrize(
    "operacion",
    [
        lambda tareas, i, s: MarcarSubtareaResuelta(tareas).ejecutar(i, s, True),
        lambda tareas, i, s: EliminarSubtarea(tareas).ejecutar(i, s),
    ],
    ids=["marcar", "eliminar"],
)
def test_operar_sobre_una_subtarea_inexistente_o_de_otra_tarea_lanza_error(operacion) -> None:
    tareas, personas, id_tarea = _repos()
    otra = tareas.crear(Tarea(nombre="Viaje", descripcion="d", fecha_creacion=_FECHA)).id
    AnadirSubtarea(tareas, personas).ejecutar(otra, "Reservar")

    with pytest.raises(EntidadNoEncontradaError, match="No existe la tarea con id 99$"):
        operacion(tareas, 99, 1)
    with pytest.raises(
        EntidadNoEncontradaError,
        match=f"No existe la subtarea con id 1 en la tarea con id {id_tarea}$",
    ):
        operacion(tareas, id_tarea, 1)
    assert [s.nombre for s in tareas.obtener_por_id(otra).subtareas] == ["Reservar"]


def test_editar_la_tarea_conserva_sus_subtareas() -> None:
    tareas, personas, id_tarea = _repos()
    AnadirSubtarea(tareas, personas).ejecutar(id_tarea, "Embalar")
    MarcarSubtareaResuelta(tareas).ejecutar(id_tarea, 1, True)

    tarea = ActualizarTarea(
        tareas, RepositorioEtiquetasFalso(), personas, RepositorioGruposEstadosFalso()
    ).ejecutar(
        id_tarea,
        nombre="Mudanza",
        descripcion="d",
        fecha_creacion=_FECHA,
        tipo=TipoTarea.OPORTUNIDAD,
        oportunidad=Oportunidad(codigo="OP"),
    )

    assert tarea.subtareas == [Subtarea(id=1, nombre="Embalar", resuelta=True)]


def test_anadir_comentario_pone_el_instante_en_utc_sin_fraccion_de_segundo() -> None:
    tareas, _, id_tarea = _repos()
    comentarios = RepositorioComentariosFalso(tareas)
    madrid = timezone(timedelta(hours=1))
    reloj = lambda: datetime(2026, 11, 10, 17, 30, 5, 987654, tzinfo=madrid)  # noqa: E731

    comentario = AnadirComentario(comentarios, reloj).ejecutar(id_tarea, "Llamar")

    esperado = Comentario(
        id=1,
        id_tarea=id_tarea,
        texto="Llamar",
        creado=datetime(2026, 11, 10, 16, 30, 5, tzinfo=UTC),
    )
    assert comentario == esperado
    assert comentario.creado.utcoffset() == timedelta(0)
    assert comentarios.comentarios == [esperado]


def test_anadir_comentario_usa_por_defecto_la_hora_actual_en_utc() -> None:
    antes = datetime.now(UTC)
    ahora = ahora_en_utc()
    assert ahora.utcoffset() == timedelta(0)
    assert antes <= ahora <= datetime.now(UTC)


def test_comentar_o_listar_en_una_tarea_que_no_existe_lanza_error() -> None:
    tareas, _, _ = _repos()
    comentarios = RepositorioComentariosFalso(tareas)

    with pytest.raises(EntidadNoEncontradaError, match="No existe la tarea con id 99"):
        AnadirComentario(comentarios).ejecutar(99, "Hola")
    with pytest.raises(EntidadNoEncontradaError, match="No existe la tarea con id 99"):
        ListarComentarios(comentarios).ejecutar(99)
    assert comentarios.comentarios == []


def test_listar_comentarios_devuelve_los_de_la_tarea_en_orden_cronologico() -> None:
    tareas, _, id_tarea = _repos()
    otra = tareas.crear(Tarea(nombre="Viaje", descripcion="d", fecha_creacion=_FECHA)).id
    comentarios = RepositorioComentariosFalso(tareas)
    instantes = iter(
        [
            datetime(2026, 11, 10, 12, 0, tzinfo=UTC),
            datetime(2026, 11, 10, 11, 0, tzinfo=UTC),
            datetime(2026, 11, 10, 11, 0, tzinfo=UTC),
        ]
    )
    caso = AnadirComentario(comentarios, lambda: next(instantes))
    caso.ejecutar(id_tarea, "Tercero")
    caso.ejecutar(otra, "De otra")
    caso.ejecutar(id_tarea, "Segundo")

    listado = ListarComentarios(comentarios).ejecutar(id_tarea)

    assert [c.texto for c in listado] == ["Segundo", "Tercero"]
    assert ListarComentarios(comentarios).ejecutar(otra)[0].texto == "De otra"
