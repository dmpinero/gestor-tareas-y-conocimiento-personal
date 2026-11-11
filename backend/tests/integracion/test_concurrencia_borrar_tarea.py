"""Borrado de una tarea a la vez que otras operaciones sobre ella.

Cada hilo simula una petición: su propia sesión y su propia transacción, con los
casos de uso y los repositorios reales sobre MySQL. Una barrera hace que todos
empiecen a la vez. Cualquier orden es válido: lo que se confirma antes del borrado
desaparece con la tarea y lo que llega después responde que la tarea (o la
subtarea) no existe. Nunca queda nada huérfano ni se escapa otro error.
"""

import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select

from gestor_tareas.aplicacion.comentario.anadir_comentario import AnadirComentario
from gestor_tareas.aplicacion.comentario_subtarea.anadir_comentario_subtarea import (
    AnadirComentarioSubtarea,
)
from gestor_tareas.aplicacion.comentario_subtarea.editar_comentario_subtarea import (
    EditarComentarioSubtarea,
)
from gestor_tareas.aplicacion.tarea.anadir_subtarea import AnadirSubtarea
from gestor_tareas.aplicacion.tarea.eliminar_tarea import EliminarTarea
from gestor_tareas.aplicacion.tarea.marcar_subtarea_resuelta import MarcarSubtareaResuelta
from gestor_tareas.dominio.comentario.entidades import ComentarioSubtarea
from gestor_tareas.dominio.excepciones import EntidadNoEncontradaError
from gestor_tareas.dominio.tarea.entidades import Subtarea, Tarea
from gestor_tareas.infraestructura.persistencia import modelos
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_comentarios_sqlalchemy import (  # noqa: E501
    RepositorioComentariosSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_comentarios_subtarea_sqlalchemy import (  # noqa: E501
    RepositorioComentariosSubtareaSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_tareas_sqlalchemy import (
    RepositorioTareasSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.repositorios.repositorios_catalogos_sqlalchemy import (  # noqa: E501
    RepositorioPersonasSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.sesion import FabricaSesiones

_RONDAS = 5
_CREADO = datetime(2026, 11, 10, 9, 30, 0, tzinfo=UTC)


def _en_sesion[T](operacion: Callable[[object], T]) -> T:
    sesion = FabricaSesiones()
    try:
        return operacion(sesion)
    finally:
        sesion.close()


def _a_la_vez(operaciones: list[Callable[[], object]]) -> list[object]:
    """Lanza las operaciones en paralelo y devuelve sus resultados, o el error de
    "no existe" si lo lanzan (cualquier otra excepción hace fallar el test)."""
    barrera = threading.Barrier(len(operaciones))

    def tras_la_barrera(operacion: Callable[[], object]) -> object:
        barrera.wait()
        try:
            return operacion()
        except EntidadNoEncontradaError as error:
            return error

    with ThreadPoolExecutor(max_workers=len(operaciones)) as ejecutor:
        futuros = [ejecutor.submit(tras_la_barrera, op) for op in operaciones]
        return [futuro.result() for futuro in futuros]


def _contar(sesion_bd, consulta) -> int:
    sesion_bd.rollback()  # Instantánea nueva para ver lo confirmado por los hilos.
    return sesion_bd.scalar(consulta)


def _preparar(sesion_bd) -> tuple[int, int, int]:
    """Tarea con una subtarea que ya tiene un comentario: (tarea, subtarea, comentario)."""
    tarea = RepositorioTareasSqlAlchemy(sesion_bd).crear(
        Tarea(
            nombre="Mudanza",
            descripcion="d",
            fecha_creacion=datetime(2026, 11, 10),
            subtareas=[Subtarea(nombre="Cajas")],
        )
    )
    id_subtarea = tarea.subtareas[0].id
    comentario = RepositorioComentariosSubtareaSqlAlchemy(sesion_bd).crear(
        ComentarioSubtarea(
            id_tarea=tarea.id, id_subtarea=id_subtarea, texto="Pedir", creado=_CREADO
        )
    )
    return tarea.id, id_subtarea, comentario.id


@pytest.mark.parametrize("ronda", range(_RONDAS))
def test_borrar_la_tarea_a_la_vez_que_se_le_anaden_subtareas_y_comentarios(
    sesion_bd, ronda
) -> None:
    id_tarea, id_subtarea, id_comentario = _preparar(sesion_bd)
    persona = f"Ana{ronda}"

    resultados = _a_la_vez(
        [
            lambda: _en_sesion(
                lambda s: EliminarTarea(RepositorioTareasSqlAlchemy(s)).ejecutar(id_tarea)
            ),
            lambda: _en_sesion(
                lambda s: EliminarTarea(RepositorioTareasSqlAlchemy(s)).ejecutar(id_tarea)
            ),
            lambda: _en_sesion(
                lambda s: AnadirSubtarea(
                    RepositorioTareasSqlAlchemy(s), RepositorioPersonasSqlAlchemy(s)
                ).ejecutar(id_tarea, "Camión", asignado=persona)
            ),
            lambda: _en_sesion(
                lambda s: AnadirComentario(RepositorioComentariosSqlAlchemy(s)).ejecutar(
                    id_tarea, "De la tarea"
                )
            ),
            lambda: _en_sesion(
                lambda s: AnadirComentarioSubtarea(
                    RepositorioComentariosSubtareaSqlAlchemy(s)
                ).ejecutar(id_tarea, id_subtarea, "De la subtarea")
            ),
            lambda: _en_sesion(
                lambda s: EditarComentarioSubtarea(
                    RepositorioComentariosSubtareaSqlAlchemy(s)
                ).ejecutar(id_tarea, id_subtarea, id_comentario, "Editado")
            ),
            lambda: _en_sesion(
                lambda s: MarcarSubtareaResuelta(RepositorioTareasSqlAlchemy(s)).ejecutar(
                    id_tarea, id_subtarea, True
                )
            ),
        ]
    )

    # Solo uno de los dos borrados encuentra la tarea; el otro responde que no existe.
    borrados = resultados[:2]
    assert sorted(isinstance(r, EntidadNoEncontradaError) for r in borrados) == [False, True]
    assert str(next(r for r in borrados if r is not None)) == (
        f"No existe la tarea con id {id_tarea}"
    )
    # El resto o se confirmó antes del borrado o responde que la tarea o la subtarea
    # no existe.
    mensajes_validos = {
        f"No existe la tarea con id {id_tarea}",
        f"No existe la subtarea con id {id_subtarea} en la tarea con id {id_tarea}",
        f"No existe el comentario con id {id_comentario} en la subtarea con id {id_subtarea}",
    }
    for resultado in resultados[2:]:
        if isinstance(resultado, EntidadNoEncontradaError):
            assert str(resultado) in mensajes_validos

    # No queda nada de la tarea en ninguna tabla.
    consultas = [
        select(func.count()).where(modelos.TareaModelo.id == id_tarea),
        select(func.count()).where(modelos.SubtareaModelo.tarea_id == id_tarea),
        select(func.count()).where(modelos.ComentarioModelo.tarea_id == id_tarea),
        select(func.count()).select_from(modelos.ComentarioSubtareaModelo),
    ]
    assert [_contar(sesion_bd, c) for c in consultas] == [0, 0, 0, 0]
    # La persona se queda en el catálogo si el alta de la subtarea llegó a
    # confirmarse antes del borrado: borrar una tarea nunca borra personas del
    # catálogo. Si el alta respondió que la tarea no existe, hay dos órdenes
    # válidos: o encontró la tarea ya borrada (y deshizo el alta de la persona), o
    # se confirmó justo antes del borrado y, al releer la tarea para responder,
    # ya no existía (la persona se queda). Nunca queda más de una.
    anadida = not isinstance(resultados[2], EntidadNoEncontradaError)
    personas = select(func.count()).where(modelos.PersonaModelo.nombre == persona)
    if anadida:
        assert _contar(sesion_bd, personas) == 1
    else:
        assert _contar(sesion_bd, personas) in (0, 1)


def test_la_persona_de_una_subtarea_confirmada_se_queda_al_borrar_la_tarea(sesion_bd) -> None:
    """El orden que antes hacía fallar la prueba anterior, de forma determinista."""
    id_tarea, _, _ = _preparar(sesion_bd)
    sesion_bd.rollback()

    _en_sesion(
        lambda s: AnadirSubtarea(
            RepositorioTareasSqlAlchemy(s), RepositorioPersonasSqlAlchemy(s)
        ).ejecutar(id_tarea, "Camión", asignado="Berta")
    )
    _en_sesion(lambda s: EliminarTarea(RepositorioTareasSqlAlchemy(s)).ejecutar(id_tarea))

    subtareas = select(func.count()).where(modelos.SubtareaModelo.tarea_id == id_tarea)
    personas = select(func.count()).where(modelos.PersonaModelo.nombre == "Berta")
    assert _contar(sesion_bd, subtareas) == 0
    assert _contar(sesion_bd, personas) == 1
