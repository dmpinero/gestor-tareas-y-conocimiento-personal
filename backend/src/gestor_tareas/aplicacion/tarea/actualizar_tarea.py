from datetime import datetime

from gestor_tareas.aplicacion.tarea.resolver_catalogos import resolver_nombres
from gestor_tareas.dominio.etiqueta.repositorio import RepositorioEtiquetas
from gestor_tareas.dominio.excepciones import EntidadNoEncontradaError
from gestor_tareas.dominio.persona.repositorio import RepositorioPersonas
from gestor_tareas.dominio.tarea.entidades import Tarea
from gestor_tareas.dominio.tarea.repositorio import RepositorioTareas


class ActualizarTarea:
    """Sustituye todos los datos editables de una tarea ya existente.

    Las etiquetas y personas asignadas sustituyen por completo a las anteriores.
    """

    def __init__(
        self,
        repositorio: RepositorioTareas,
        repositorio_etiquetas: RepositorioEtiquetas,
        repositorio_personas: RepositorioPersonas,
    ) -> None:
        self._repositorio = repositorio
        self._repositorio_etiquetas = repositorio_etiquetas
        self._repositorio_personas = repositorio_personas

    def ejecutar(
        self,
        id_tarea: int,
        nombre: str,
        descripcion: str,
        fecha_creacion: datetime,
        prioridad: int | None = None,
        fecha_vencimiento: datetime | None = None,
        etiquetas: list[str] | None = None,
        asignados: list[str] | None = None,
    ) -> Tarea:
        tarea = self._repositorio.obtener_por_id(id_tarea)
        if tarea is None:
            raise EntidadNoEncontradaError(f"No existe la tarea con id {id_tarea}")

        tarea.nombre = nombre
        tarea.prioridad = prioridad
        tarea.descripcion = descripcion
        tarea.fecha_creacion = fecha_creacion
        tarea.fecha_vencimiento = fecha_vencimiento
        tarea.etiquetas = resolver_nombres(self._repositorio_etiquetas, etiquetas or [])
        tarea.asignados = resolver_nombres(self._repositorio_personas, asignados or [])
        return self._repositorio.actualizar(tarea)
