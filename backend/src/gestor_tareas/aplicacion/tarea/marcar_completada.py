from gestor_tareas.aplicacion.reintentos import reintentar_si_hay_conflicto
from gestor_tareas.dominio.excepciones import EntidadNoEncontradaError
from gestor_tareas.dominio.tarea.entidades import Tarea
from gestor_tareas.dominio.tarea.repositorio import RepositorioTareas


class MarcarCompletada:
    """Marca una tarea existente como completada o la deja pendiente.

    Solo cambia el estado; el resto de datos de la tarea se conserva.
    """

    def __init__(self, repositorio: RepositorioTareas) -> None:
        self._repositorio = repositorio

    def ejecutar(self, id_tarea: int, completada: bool) -> Tarea:
        def guardar() -> Tarea:
            tarea = self._repositorio.cambiar_completada(id_tarea, completada)
            if tarea is None:
                raise EntidadNoEncontradaError(f"No existe la tarea con id {id_tarea}")
            return tarea

        # Si choca con otra petición simultánea sobre la misma tarea, se repite.
        return reintentar_si_hay_conflicto(guardar)
