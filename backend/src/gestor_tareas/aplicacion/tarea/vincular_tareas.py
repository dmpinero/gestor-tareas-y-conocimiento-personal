from collections.abc import Iterable

from gestor_tareas.aplicacion.reintentos import reintentar_si_hay_conflicto
from gestor_tareas.dominio.excepciones import EntidadNoEncontradaError
from gestor_tareas.dominio.tarea.entidades import Tarea
from gestor_tareas.dominio.tarea.repositorio import RepositorioTareas
from gestor_tareas.dominio.tarea.vinculos import ids_a_vincular


class VincularTareas:
    """Vincula una tarea con una o varias tareas existentes, en los dos sentidos.

    Las que ya estaban vinculadas se ignoran. Lanza ``VinculoInvalidoError`` si no se
    indica ninguna o si incluyen la propia tarea, y ``EntidadNoEncontradaError`` si
    la tarea o alguna de las indicadas no existe; en esos casos no vincula ninguna.
    """

    def __init__(self, repositorio: RepositorioTareas) -> None:
        self._repositorio = repositorio

    def ejecutar(self, id_tarea: int, ids: Iterable[int]) -> Tarea:
        vinculables = ids_a_vincular(id_tarea, ids)

        def guardar() -> Tarea:
            tarea = self._repositorio.vincular(id_tarea, vinculables)
            if tarea is None:
                raise EntidadNoEncontradaError(f"No existe la tarea con id {id_tarea}")
            return tarea

        # Si choca con otra petición simultánea sobre las mismas tareas, se repite.
        return reintentar_si_hay_conflicto(guardar)
