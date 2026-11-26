"""Vínculos entre tareas.

Un vínculo relaciona dos tareas distintas de forma simple (sin tipos) y en los dos
sentidos: si A está vinculada con B, B lo está con A. Vincular tareas que ya lo
estaban no cambia nada; al quitar un vínculo, o al borrar una de las dos tareas,
desaparece en los dos sentidos.
"""

from collections.abc import Iterable


class VinculoInvalidoError(Exception):
    """Se lanza al vincular una tarea consigo misma o sin indicar ninguna tarea."""


def ids_a_vincular(id_tarea: int, ids: Iterable[int]) -> list[int]:
    """Los ids de las tareas que se van a vincular con ``id_tarea``, sin repetir y en
    orden ascendente. Lanza ``VinculoInvalidoError`` si no hay ninguno o si incluyen
    la propia tarea."""
    unicos = sorted(set(ids))
    if not unicos:
        raise VinculoInvalidoError("Hay que indicar al menos una tarea que vincular")
    if id_tarea in unicos:
        raise VinculoInvalidoError("Una tarea no puede vincularse consigo misma")
    return unicos
