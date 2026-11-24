from collections.abc import Callable
from datetime import datetime

from gestor_tareas.aplicacion.comentario.anadir_comentario import (
    ahora_en_utc,
    instante_de_comentario,
)
from gestor_tareas.aplicacion.reintentos import reintentar_si_hay_conflicto
from gestor_tareas.aplicacion.tarea.errores_subtarea import subtarea_no_encontrada
from gestor_tareas.dominio.foco.repositorio import RepositorioFoco
from gestor_tareas.dominio.tarea.entidades import Tarea
from gestor_tareas.dominio.tarea.repositorio import RepositorioTareas


class EliminarSubtarea:
    """Borra una subtarea de una tarea; el resto de datos de la tarea se conserva.

    Con ``foco``, si la subtarea estaba en foco, cierra ahora su periodo del
    historial en la misma transacción que el borrado (el foco se quita con ella).
    """

    def __init__(
        self,
        repositorio: RepositorioTareas,
        foco: RepositorioFoco | None = None,
        reloj: Callable[[], datetime] = ahora_en_utc,
    ) -> None:
        self._repositorio = repositorio
        self._foco = foco
        self._reloj = reloj

    def ejecutar(self, id_tarea: int, id_subtarea: int) -> Tarea:
        def guardar() -> Tarea:
            if self._foco is not None:
                # Sin confirmar: lo confirma (o lo deshace) el borrado.
                self._foco.cerrar_periodo_de_subtarea(
                    id_tarea, id_subtarea, instante_de_comentario(self._reloj)
                )
            tarea = self._repositorio.eliminar_subtarea(id_tarea, id_subtarea)
            if tarea is None:
                raise subtarea_no_encontrada(self._repositorio, id_tarea, id_subtarea)
            return tarea

        # Si choca con otra petición simultánea sobre la misma tarea, se repite.
        return reintentar_si_hay_conflicto(guardar)
