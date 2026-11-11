"""Operaciones simultáneas sobre un mismo comentario.

Cada hilo simula una petición: su propia sesión y su propia transacción, con el
repositorio real sobre MySQL. Una barrera hace que todos empiecen a la vez.
"""

import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

from sqlalchemy import func, select

from gestor_tareas.aplicacion.comentario.editar_comentario import EditarComentario
from gestor_tareas.aplicacion.comentario.eliminar_comentario import EliminarComentario
from gestor_tareas.dominio.comentario.entidades import Comentario
from gestor_tareas.dominio.excepciones import EntidadNoEncontradaError
from gestor_tareas.dominio.tarea.entidades import Tarea
from gestor_tareas.infraestructura.persistencia.modelos import ComentarioModelo
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_comentarios_sqlalchemy import (  # noqa: E501
    RepositorioComentariosSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_tareas_sqlalchemy import (
    RepositorioTareasSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.sesion import FabricaSesiones

_HILOS = 8


def _en_sesion[T](operacion: Callable[[RepositorioComentariosSqlAlchemy], T]) -> T:
    sesion = FabricaSesiones()
    try:
        return operacion(RepositorioComentariosSqlAlchemy(sesion))
    finally:
        sesion.close()


def _a_la_vez(operaciones: list[Callable[[], object]]) -> list[object]:
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


def test_editar_y_eliminar_a_la_vez_el_mismo_comentario(sesion_bd) -> None:
    tarea = Tarea(nombre="Mudanza", descripcion="d", fecha_creacion=datetime(2026, 11, 10))
    id_tarea = RepositorioTareasSqlAlchemy(sesion_bd).crear(tarea).id
    alta = datetime(2026, 11, 10, 8, 0, tzinfo=UTC)
    id_comentario = (
        RepositorioComentariosSqlAlchemy(sesion_bd)
        .crear(Comentario(id_tarea=id_tarea, texto="X", creado=alta))
        .id
    )

    resultados = _a_la_vez(
        [
            lambda: _en_sesion(lambda r: EliminarComentario(r).ejecutar(id_tarea, id_comentario)),
            *[
                lambda i=i: _en_sesion(
                    lambda r: EditarComentario(r).ejecutar(id_tarea, id_comentario, f"Y{i}")
                )
                for i in range(_HILOS - 1)
            ],
        ]
    )

    # Cada edición llegó antes de la eliminación (y devuelve lo que guardó) o
    # después (404); nunca un error 500.
    assert resultados[0] is None
    for i, resultado in enumerate(resultados[1:]):
        if isinstance(resultado, Comentario):
            assert (resultado.id, resultado.texto, resultado.creado) == (
                id_comentario,
                f"Y{i}",
                alta,
            )
            assert resultado.editado is not None
        else:
            assert str(resultado) == (
                f"No existe el comentario con id {id_comentario} en la tarea con id {id_tarea}"
            )
    sesion_bd.rollback()
    total = sesion_bd.scalar(
        select(func.count())
        .select_from(ComentarioModelo)
        .where(ComentarioModelo.tarea_id == id_tarea)
    )
    assert total == 0
