from datetime import datetime

from gestor_tareas.aplicacion.reintentos import reintentar_si_hay_conflicto
from gestor_tareas.aplicacion.tarea.resolver_catalogos import resolver_nombres
from gestor_tareas.dominio.etiqueta.repositorio import RepositorioEtiquetas
from gestor_tareas.dominio.persona.repositorio import RepositorioPersonas
from gestor_tareas.dominio.tarea.entidades import Oportunidad, Tarea, TipoTarea
from gestor_tareas.dominio.tarea.repositorio import RepositorioTareas


class CrearTarea:
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
            tarea = Tarea(
                nombre=nombre,
                prioridad=prioridad,
                descripcion=descripcion,
                fecha_creacion=fecha_creacion,
                fecha_vencimiento=fecha_vencimiento,
                etiquetas=resolver_nombres(self._repositorio_etiquetas, etiquetas or []),
                asignados=resolver_nombres(self._repositorio_personas, asignados or []),
                tipo=tipo,
                oportunidad=oportunidad,
            )
            return self._repositorio.crear(tarea)

        # Dar de alta en los catálogos y guardar la tarea es una sola transacción:
        # si choca con otra petición simultánea, se repite entera.
        return reintentar_si_hay_conflicto(guardar)
