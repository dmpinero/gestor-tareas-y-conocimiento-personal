from datetime import datetime

from gestor_tareas.dominio.excepciones import EntidadNoEncontradaError
from gestor_tareas.dominio.tarea.entidades import Tarea
from gestor_tareas.dominio.tarea.repositorio import RepositorioTareas


class ActualizarTarea:
    """Sustituye todos los datos editables de una tarea ya existente."""

    def __init__(self, repositorio: RepositorioTareas) -> None:
        self._repositorio = repositorio

    def ejecutar(
        self,
        id_tarea: int,
        nombre: str,
        descripcion: str,
        fecha_hora: datetime,
        prioridad: int | None = None,
    ) -> Tarea:
        tarea = self._repositorio.obtener_por_id(id_tarea)
        if tarea is None:
            raise EntidadNoEncontradaError(f"No existe la tarea con id {id_tarea}")

        tarea.nombre = nombre
        tarea.prioridad = prioridad
        tarea.descripcion = descripcion
        tarea.fecha_hora = fecha_hora
        return self._repositorio.actualizar(tarea)
