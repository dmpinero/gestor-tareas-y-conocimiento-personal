"""Reglas de la cola de siguientes tareas.

La cola es una lista ordenada de tareas, cada una como mucho una vez. Las tareas
completadas siguen guardadas en su sitio pero no se ven: al reabrirlas vuelven a
aparecer donde estaban. Borrar una tarea, o ponerla en foco (a ella o a una subtarea
suya), la saca de la cola.
"""

from collections.abc import Sequence
from dataclasses import dataclass


class TareaCompletadaEnLaColaError(Exception):
    """Se lanza al añadir a la cola de siguientes una tarea completada."""


class OrdenDeLaColaInvalidoError(Exception):
    """Se lanza al reordenar la cola con una lista que no es exactamente la cola
    visible (con repetidos, con tareas de menos o con tareas que no están o están
    completadas)."""


@dataclass(frozen=True)
class EntradaDeLaCola:
    """Una tarea guardada en la cola, visible o no (completada)."""

    tarea_id: int
    completada: bool


def comprobar_que_se_puede_anadir(completada: bool) -> None:
    """Lanza ``TareaCompletadaEnLaColaError`` si la tarea está completada."""
    if completada:
        raise TareaCompletadaEnLaColaError("No se puede añadir a siguientes una tarea completada")


def nuevo_orden_de_la_cola(entradas: Sequence[EntradaDeLaCola], ids: Sequence[int]) -> list[int]:
    """El orden completo de la cola tras reordenar las visibles como dice ``ids``: las
    visibles en ese orden y, detrás, las completadas en el orden que tenían.

    ``entradas`` es la cola guardada en su orden actual. Lanza
    ``OrdenDeLaColaInvalidoError`` si ``ids`` no incluye cada tarea visible
    exactamente una vez, y ninguna más."""
    visibles = {e.tarea_id for e in entradas if not e.completada}
    if len(set(ids)) != len(ids) or set(ids) != visibles:
        raise OrdenDeLaColaInvalidoError(
            "El orden debe incluir cada tarea de la cola exactamente una vez, y ninguna más"
        )
    return [*ids, *(e.tarea_id for e in entradas if e.completada)]
