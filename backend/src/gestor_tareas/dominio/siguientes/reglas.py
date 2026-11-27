"""Reglas de la cola de siguientes tareas y de las sugerencias elegidas.

Cada una es una lista ordenada de entradas, y cada entrada es una tarea entera o una
subtarea suya (``ClaveDeEntrada``). Una entrada está como mucho en una de las dos
listas (añadirla a una la quita de la otra y la pone al final); una tarea y una
subtarea suya son entradas distintas. Las reglas de abajo valen para cada lista por
separado. Las entradas de tareas completadas, o de subtareas resueltas, siguen
guardadas en su sitio pero no se ven: al reabrirlas vuelven a aparecer donde
estaban. Borrar una tarea o una subtarea quita sus entradas. Poner en foco una tarea
entera quita su entrada; poner en foco una subtarea quita la suya y la de su tarea.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from gestor_tareas.dominio.siguientes.entidades import ClaveDeEntrada


class TareaCompletadaEnLaColaError(Exception):
    """Se lanza al añadir a la cola de siguientes una tarea completada (o una subtarea
    de una tarea completada)."""


class SubtareaResueltaEnLaColaError(Exception):
    """Se lanza al añadir a la cola de siguientes una subtarea resuelta."""


class OrdenDeLaColaInvalidoError(Exception):
    """Se lanza al reordenar la cola con una lista que no es exactamente la cola
    visible (con repetidas, con entradas de menos o con entradas que no están o no se
    ven)."""


@dataclass(frozen=True)
class EntradaDeLaCola:
    """Una entrada guardada en la cola, visible o no. ``completada`` es que no se ve:
    su tarea está completada o, si es de una subtarea, la subtarea está resuelta."""

    tarea_id: int
    completada: bool
    subtarea_id: int | None = None

    @property
    def clave(self) -> ClaveDeEntrada:
        return ClaveDeEntrada(self.tarea_id, self.subtarea_id)


def comprobar_que_se_puede_anadir(completada: bool, resuelta: bool = False) -> None:
    """Lanza ``TareaCompletadaEnLaColaError`` si la tarea está completada y, si no,
    ``SubtareaResueltaEnLaColaError`` si la entrada es de una subtarea resuelta."""
    if completada:
        raise TareaCompletadaEnLaColaError("No se puede añadir a siguientes una tarea completada")
    if resuelta:
        raise SubtareaResueltaEnLaColaError("No se puede añadir a siguientes una subtarea resuelta")


def nuevo_orden_de_la_cola(
    entradas: Sequence[EntradaDeLaCola], claves: Sequence[ClaveDeEntrada]
) -> list[ClaveDeEntrada]:
    """El orden completo de la cola tras reordenar las visibles como dice ``claves``:
    las visibles en ese orden y, detrás, las que no se ven en el orden que tenían.

    ``entradas`` es la cola guardada en su orden actual. Lanza
    ``OrdenDeLaColaInvalidoError`` si ``claves`` no incluye cada entrada visible
    exactamente una vez, y ninguna más."""
    claves = [ClaveDeEntrada(*c) for c in claves]
    visibles = {e.clave for e in entradas if not e.completada}
    if len(set(claves)) != len(claves) or set(claves) != visibles:
        raise OrdenDeLaColaInvalidoError(
            "El orden debe incluir cada entrada de la cola exactamente una vez, y ninguna más"
        )
    return [*claves, *(e.clave for e in entradas if e.completada)]
