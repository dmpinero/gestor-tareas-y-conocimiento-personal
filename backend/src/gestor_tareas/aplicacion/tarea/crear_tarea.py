from gestor_tareas.dominio.tarea.entidades import Tarea
from gestor_tareas.dominio.tarea.repositorio import RepositorioTareas


class CrearTarea:
    def __init__(self, repositorio: RepositorioTareas) -> None:
        self._repositorio = repositorio

    def ejecutar(self, nombre: str, descripcion: str, prioridad: int | None = None) -> Tarea:
        tarea = Tarea(nombre=nombre, prioridad=prioridad, descripcion=descripcion)
        return self._repositorio.crear(tarea)
