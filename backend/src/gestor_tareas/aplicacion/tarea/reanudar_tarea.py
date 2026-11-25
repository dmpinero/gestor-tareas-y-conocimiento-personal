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


class ReanudarTarea:
    """Reanuda una tarea hibernada: su fecha de vencimiento (si tiene) se corre el
    tiempo que ha estado hibernada, hasta este instante, y deja de estarlo.

    Lanza ``EstadoDeHibernacionInvalidoError`` si no estaba hibernada. El resto de
    datos de la tarea se conserva.
    """

    def __init__(
        self,
        repositorio: RepositorioTareas,
        reloj: Callable[[], datetime] = ahora_en_utc,
    ) -> None:
        self._repositorio = repositorio
        self._reloj = reloj

    def ejecutar(self, id_tarea: int) -> Tarea:
        def guardar() -> Tarea:
            tarea = self._repositorio.reanudar(id_tarea, instante_de_comentario(self._reloj))
            if tarea is None:
                raise EntidadNoEncontradaError(f"No existe la tarea con id {id_tarea}")
            return tarea

        # Si choca con otra petición simultánea sobre la misma tarea, se repite.
        return reintentar_si_hay_conflicto(guardar)
