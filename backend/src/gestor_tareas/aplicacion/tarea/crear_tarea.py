from datetime import datetime

from gestor_tareas.aplicacion.reintentos import reintentar_si_hay_conflicto
from gestor_tareas.aplicacion.tarea.asignar_grupo_estados import GrupoPedido
from gestor_tareas.aplicacion.tarea.resolver_catalogos import resolver_nombres
from gestor_tareas.dominio.etiqueta.repositorio import RepositorioEtiquetas
from gestor_tareas.dominio.grupo_estados.repositorio import RepositorioGruposEstados
from gestor_tareas.dominio.persona.repositorio import RepositorioPersonas
from gestor_tareas.dominio.tarea.entidades import Oportunidad, Subtarea, Tarea, TipoTarea
from gestor_tareas.dominio.tarea.repositorio import RepositorioTareas
from gestor_tareas.dominio.workflow_oportunidades.repositorio import (
    RepositorioWorkflowOportunidades,
)


class CrearTarea:
    """Da de alta una tarea pendiente.

    Una tarea creada como oportunidad recibe una subtarea por cada paso vigente del
    workflow de las oportunidades, en su orden, pendiente y sin persona ni
    prioridad.
    """

    def __init__(
        self,
        repositorio: RepositorioTareas,
        repositorio_etiquetas: RepositorioEtiquetas,
        repositorio_personas: RepositorioPersonas,
        repositorio_workflow: RepositorioWorkflowOportunidades,
        repositorio_grupos: RepositorioGruposEstados,
    ) -> None:
        self._repositorio = repositorio
        self._repositorio_etiquetas = repositorio_etiquetas
        self._repositorio_personas = repositorio_personas
        self._repositorio_workflow = repositorio_workflow
        self._repositorio_grupos = repositorio_grupos

    def _subtareas_del_workflow(self, tipo: TipoTarea | None) -> list[Subtarea]:
        """Una subtarea por cada paso vigente del workflow si la tarea es una
        oportunidad.

        Es una copia fija: las subtareas no guardan ninguna relación con los pasos
        del workflow, así que cambiarlo después no las altera.
        """
        if tipo is not TipoTarea.OPORTUNIDAD:
            return []
        return [
            Subtarea(nombre=paso.nombre)
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
        grupo_estados_id: int | None = None,
    ) -> Tarea:
        def guardar() -> Tarea:
            # Lo primero, para bloquear el grupo antes que nada (ver GrupoPedido).
            grupo = GrupoPedido(self._repositorio_grupos, grupo_estados_id)
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
                subtareas=self._subtareas_del_workflow(tipo),
            )
            grupo.asignar(tarea)
            return self._repositorio.crear(tarea)

        # Leer el grupo de estados, dar de alta en los catálogos, copiar el workflow y
        # guardar la tarea es una sola transacción: si choca con otra petición
        # simultánea, se repite entera.
        return reintentar_si_hay_conflicto(guardar)
