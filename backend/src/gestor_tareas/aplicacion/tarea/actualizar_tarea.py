from datetime import datetime

from gestor_tareas.aplicacion.reintentos import reintentar_si_hay_conflicto
from gestor_tareas.aplicacion.tarea.resolver_catalogos import resolver_nombres
from gestor_tareas.dominio.etiqueta.repositorio import RepositorioEtiquetas
from gestor_tareas.dominio.excepciones import EntidadNoEncontradaError
from gestor_tareas.dominio.persona.repositorio import RepositorioPersonas
from gestor_tareas.dominio.tarea.entidades import Oportunidad, Tarea, TipoTarea
from gestor_tareas.dominio.tarea.repositorio import RepositorioTareas


class ActualizarTarea:
    """Sustituye todos los datos editables de una tarea ya existente.

    Las etiquetas y personas asignadas sustituyen por completo a las anteriores, y
    también el tipo y sus datos (sin tipo, la tarea pierde sus datos de oportunidad).
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
        tipo: TipoTarea | None = None,
        oportunidad: Oportunidad | None = None,
    ) -> Tarea:
        def guardar() -> Tarea:
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
            tarea.tipo = tipo
            tarea.oportunidad = oportunidad
            return self._repositorio.actualizar(tarea)

        # Leer la tarea, dar de alta en los catálogos y guardar es una sola
        # transacción: si choca con otra petición simultánea, se repite entera.
        return reintentar_si_hay_conflicto(guardar)
