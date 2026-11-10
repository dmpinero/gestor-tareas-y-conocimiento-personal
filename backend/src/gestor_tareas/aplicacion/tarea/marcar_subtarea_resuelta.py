from gestor_tareas.aplicacion.reintentos import reintentar_si_hay_conflicto
from gestor_tareas.aplicacion.tarea.errores_subtarea import subtarea_no_encontrada
from gestor_tareas.dominio.tarea.entidades import Tarea
from gestor_tareas.dominio.tarea.repositorio import RepositorioTareas


class MarcarSubtareaResuelta:
    """Marca una subtarea como resuelta o la vuelve a dejar pendiente.

    Solo cambia esa subtarea; el resto de datos de la tarea se conserva.
    """

    def __init__(self, repositorio: RepositorioTareas) -> None:
        self._repositorio = repositorio

    def ejecutar(self, id_tarea: int, id_subtarea: int, resuelta: bool) -> Tarea:
        def guardar() -> Tarea:
            tarea = self._repositorio.cambiar_resuelta_subtarea(id_tarea, id_subtarea, resuelta)
            if tarea is None:
                raise subtarea_no_encontrada(self._repositorio, id_tarea, id_subtarea)
            return tarea

        # Si choca con otra petición simultánea sobre la misma tarea, se repite.
        return reintentar_si_hay_conflicto(guardar)
