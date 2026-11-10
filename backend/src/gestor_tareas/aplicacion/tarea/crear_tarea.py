from datetime import datetime

from gestor_tareas.aplicacion.reintentos import reintentar_si_hay_conflicto
from gestor_tareas.aplicacion.tarea.resolver_catalogos import resolver_nombres
from gestor_tareas.dominio.etiqueta.repositorio import RepositorioEtiquetas
from gestor_tareas.dominio.persona.repositorio import RepositorioPersonas
from gestor_tareas.dominio.tarea.entidades import Oportunidad, PasoOportunidad, Tarea, TipoTarea
from gestor_tareas.dominio.tarea.repositorio import RepositorioTareas
from gestor_tareas.dominio.workflow_oportunidades.repositorio import (
    RepositorioWorkflowOportunidades,
)


class CrearTarea:
    """Da de alta una tarea pendiente.

    Una tarea creada como oportunidad recibe una copia de los pasos vigentes del
    workflow de las oportunidades, en su orden y pendientes.
    """

    def __init__(
        self,
        repositorio: RepositorioTareas,
        repositorio_etiquetas: RepositorioEtiquetas,
        repositorio_personas: RepositorioPersonas,
        repositorio_workflow: RepositorioWorkflowOportunidades,
    ) -> None:
        self._repositorio = repositorio
        self._repositorio_etiquetas = repositorio_etiquetas
        self._repositorio_personas = repositorio_personas
        self._repositorio_workflow = repositorio_workflow

    def _copiar_workflow(self, tipo: TipoTarea | None) -> list[PasoOportunidad]:
        """Copia los pasos vigentes del workflow si la tarea es una oportunidad.

        La copia es fija: no guarda ninguna relación con los pasos del workflow.
        """
        if tipo is not TipoTarea.OPORTUNIDAD:
            return []
        return [
            PasoOportunidad(numero=paso.numero, nombre=paso.nombre)
            for paso in self._repositorio_workflow.leer_pasos_para_copiar()
        ]

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
                pasos_oportunidad=self._copiar_workflow(tipo),
            )
            return self._repositorio.crear(tarea)

        # Dar de alta en los catálogos, copiar el workflow y guardar la tarea es una
        # sola transacción: si choca con otra petición simultánea, se repite entera.
        return reintentar_si_hay_conflicto(guardar)
