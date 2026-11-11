"""Operaciones simultáneas sobre las subtareas de una tarea.

Cada hilo simula una petición: su propia sesión y su propia transacción, con los
repositorios reales sobre MySQL. Una barrera hace que todos empiecen a la vez.
"""

import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import pytest
from sqlalchemy import func, select

from gestor_tareas.aplicacion.tarea.anadir_subtarea import AnadirSubtarea
from gestor_tareas.aplicacion.tarea.editar_subtarea import EditarSubtarea
from gestor_tareas.aplicacion.tarea.eliminar_subtarea import EliminarSubtarea
from gestor_tareas.aplicacion.tarea.marcar_subtarea_resuelta import MarcarSubtareaResuelta
from gestor_tareas.dominio.excepciones import EntidadNoEncontradaError
from gestor_tareas.dominio.tarea.entidades import Subtarea, Tarea
from gestor_tareas.infraestructura.persistencia.modelos import PersonaModelo, SubtareaModelo
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_tareas_sqlalchemy import (
    RepositorioTareasSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.repositorios.repositorios_catalogos_sqlalchemy import (  # noqa: E501
    RepositorioPersonasSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.sesion import FabricaSesiones

_HILOS = 8


def _en_sesion[T](
    operacion: Callable[[RepositorioTareasSqlAlchemy, RepositorioPersonasSqlAlchemy], T],
) -> T:
    sesion = FabricaSesiones()
    try:
        return operacion(RepositorioTareasSqlAlchemy(sesion), RepositorioPersonasSqlAlchemy(sesion))
    finally:
        sesion.close()


def _a_la_vez(operaciones: list[Callable[[], object]]) -> list[object]:
    """Lanza las operaciones en paralelo y devuelve sus resultados (o excepciones)."""
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


def _contar(sesion_bd, modelo, *condiciones) -> int:
    sesion_bd.rollback()  # Instantánea nueva para ver lo confirmado por los hilos.
    return sesion_bd.scalar(select(func.count()).select_from(modelo).where(*condiciones))


def _nueva_tarea(sesion_bd) -> int:
    repositorio = RepositorioTareasSqlAlchemy(sesion_bd)
    tarea = Tarea(nombre="Mudanza", descripcion="d", fecha_creacion=datetime(2026, 11, 10))
    return repositorio.crear(tarea).id


@pytest.mark.parametrize("ronda", range(3))
def test_altas_simultaneas_con_una_persona_nueva_compartida(sesion_bd, ronda) -> None:
    id_tarea = _nueva_tarea(sesion_bd)
    persona = f"Ana{ronda}"

    resultados = _a_la_vez(
        [
            lambda i=i: _en_sesion(
                lambda t, p: AnadirSubtarea(t, p).ejecutar(
                    id_tarea, f"S{i}", asignado=persona if i % 2 else persona.upper()
                )
            )
            for i in range(_HILOS)
        ]
    )

    assert all(isinstance(r, Tarea) for r in resultados)
    asignados = {s.asignado for r in resultados for s in r.subtareas}
    assert len(asignados) == 1
    assert asignados.pop().casefold() == persona.casefold()
    assert _contar(sesion_bd, PersonaModelo, PersonaModelo.nombre == persona) == 1
    assert _contar(sesion_bd, SubtareaModelo, SubtareaModelo.tarea_id == id_tarea) == _HILOS


def test_eliminar_y_marcar_a_la_vez_la_misma_subtarea(sesion_bd) -> None:
    id_tarea = _nueva_tarea(sesion_bd)
    tarea = RepositorioTareasSqlAlchemy(sesion_bd).anadir_subtarea(id_tarea, Subtarea(nombre="X"))
    id_sub = tarea.subtareas[0].id

    operaciones = [
        lambda: _en_sesion(lambda t, _: EliminarSubtarea(t).ejecutar(id_tarea, id_sub)),
        *[
            lambda: _en_sesion(
                lambda t, _: MarcarSubtareaResuelta(t).ejecutar(id_tarea, id_sub, True)
            )
            for _ in range(_HILOS - 1)
        ],
    ]
    resultados = _a_la_vez(operaciones)

    # Cada marcado o bien llegó antes de la eliminación o bien después (y ya no
    # la encontró: 404); nunca un error 500. Si llegó antes, la tarea se relee
    # tras confirmar, así que la eliminación puede haberse confirmado entre medias
    # y la respuesta ya no incluye la subtarea; lo que nunca puede verse es la
    # subtarea sin resolver.
    assert isinstance(resultados[0], Tarea)
    assert resultados[0].subtareas == []
    for resultado in resultados[1:]:
        if isinstance(resultado, Tarea):
            assert [s.resuelta for s in resultado.subtareas] in ([True], [])
        else:
            assert str(resultado) == (
                f"No existe la subtarea con id {id_sub} en la tarea con id {id_tarea}"
            )
    assert _contar(sesion_bd, SubtareaModelo, SubtareaModelo.tarea_id == id_tarea) == 0


def test_editar_y_eliminar_a_la_vez_la_misma_subtarea(sesion_bd) -> None:
    id_tarea = _nueva_tarea(sesion_bd)
    tarea = RepositorioTareasSqlAlchemy(sesion_bd).anadir_subtarea(id_tarea, Subtarea(nombre="X"))
    id_sub = tarea.subtareas[0].id

    operaciones = [
        lambda: _en_sesion(lambda t, _: EliminarSubtarea(t).ejecutar(id_tarea, id_sub)),
        *[
            lambda i=i: _en_sesion(
                lambda t, p: EditarSubtarea(t, p).ejecutar(
                    id_tarea, id_sub, f"Y{i}", asignado="Ana", prioridad=3
                )
            )
            for i in range(_HILOS - 1)
        ],
    ]
    resultados = _a_la_vez(operaciones)

    # Cada edición llegó antes de la eliminación (y la respuesta, releída tras
    # confirmar, puede no incluir ya la subtarea) o después (404); nunca un 500 ni
    # la subtarea con datos a medias.
    assert isinstance(resultados[0], Tarea)
    assert resultados[0].subtareas == []
    for i, resultado in enumerate(resultados[1:]):
        if isinstance(resultado, Tarea):
            assert [(s.asignado, s.prioridad) for s in resultado.subtareas] in ([], [("Ana", 3)])
            assert all(s.nombre.startswith("Y") for s in resultado.subtareas), i
        else:
            assert str(resultado) == (
                f"No existe la subtarea con id {id_sub} en la tarea con id {id_tarea}"
            )
    assert _contar(sesion_bd, SubtareaModelo, SubtareaModelo.tarea_id == id_tarea) == 0
    # Si alguna edición llegó a tiempo, dio de alta a la persona una sola vez; si
    # ninguna, el alta se deshizo con su transacción.
    assert _contar(sesion_bd, PersonaModelo, PersonaModelo.nombre == "Ana") in (0, 1)
