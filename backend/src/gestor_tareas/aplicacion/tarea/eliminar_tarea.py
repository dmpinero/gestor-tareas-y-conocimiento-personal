from gestor_tareas.aplicacion.reintentos import reintentar_si_hay_conflicto
from gestor_tareas.dominio.excepciones import EntidadNoEncontradaError
from gestor_tareas.dominio.tarea.repositorio import RepositorioTareas


class EliminarTarea:
    """Borra una tarea con sus subtareas, sus comentarios y los de sus subtareas.

    Las etiquetas y personas del catálogo se conservan.
    """

    def __init__(self, repositorio: RepositorioTareas) -> None:
        self._repositorio = repositorio

    def ejecutar(self, id_tarea: int) -> None:
        def borrar() -> None:
            if not self._repositorio.eliminar(id_tarea):
                raise EntidadNoEncontradaError(f"No existe la tarea con id {id_tarea}")

        # Si choca con otra petición simultánea sobre la misma tarea, se repite.
        reintentar_si_hay_conflicto(borrar)
