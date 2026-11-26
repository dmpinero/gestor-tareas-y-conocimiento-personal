from gestor_tareas.aplicacion.reintentos import reintentar_si_hay_conflicto
from gestor_tareas.dominio.excepciones import EntidadNoEncontradaError
from gestor_tareas.dominio.tarea.entidades import Tarea
from gestor_tareas.dominio.tarea.repositorio import RepositorioTareas


class DesvincularTarea:
    """Quita el vínculo entre dos tareas, en los dos sentidos, y devuelve la primera.

    Si no estaban vinculadas no cambia nada. Lanza ``EntidadNoEncontradaError`` si
    alguna de las dos no existe.
    """

    def __init__(self, repositorio: RepositorioTareas) -> None:
        self._repositorio = repositorio

    def ejecutar(self, id_tarea: int, id_vinculada: int) -> Tarea:
        def guardar() -> Tarea:
            tarea = self._repositorio.desvincular(id_tarea, id_vinculada)
            if tarea is None:
                raise EntidadNoEncontradaError(f"No existe la tarea con id {id_tarea}")
            return tarea

        # Si choca con otra petición simultánea sobre las mismas tareas, se repite.
        return reintentar_si_hay_conflicto(guardar)
