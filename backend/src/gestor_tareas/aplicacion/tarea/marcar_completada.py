from collections.abc import Callable
from datetime import datetime

from gestor_tareas.aplicacion.comentario.anadir_comentario import (
    ahora_en_utc,
    instante_de_comentario,
)
from gestor_tareas.aplicacion.reintentos import reintentar_si_hay_conflicto
from gestor_tareas.dominio.excepciones import EntidadNoEncontradaError
from gestor_tareas.dominio.tarea.entidades import Tarea
from gestor_tareas.dominio.tarea.repositorio import RepositorioTareas


class MarcarCompletada:
    """Marca una tarea existente como completada o la deja pendiente.

    Solo cambia el estado y, con él, el contador de vencimiento: completada, queda
    congelada desde este instante (o conserva el que tenía si ya lo estaba, p. ej.
    por estar en DONE); pendiente y fuera de DONE, deja de estar congelada. El resto
    de datos de la tarea se conserva.
    """

    def __init__(
        self,
        repositorio: RepositorioTareas,
        reloj: Callable[[], datetime] = ahora_en_utc,
    ) -> None:
        self._repositorio = repositorio
        self._reloj = reloj

    def ejecutar(self, id_tarea: int, completada: bool) -> Tarea:
        def guardar() -> Tarea:
            tarea = self._repositorio.cambiar_completada(
                id_tarea, completada, instante_de_comentario(self._reloj)
            )
            if tarea is None:
                raise EntidadNoEncontradaError(f"No existe la tarea con id {id_tarea}")
            return tarea

        # Si choca con otra petición simultánea sobre la misma tarea, se repite.
        return reintentar_si_hay_conflicto(guardar)
