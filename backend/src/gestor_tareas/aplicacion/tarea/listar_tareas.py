from gestor_tareas.dominio.tarea.entidades import Tarea
from gestor_tareas.dominio.tarea.repositorio import RepositorioTareas


class ListarTareas:
    def __init__(self, repositorio: RepositorioTareas) -> None:
        self._repositorio = repositorio

    def ejecutar(self) -> list[Tarea]:
        return self._repositorio.listar()
