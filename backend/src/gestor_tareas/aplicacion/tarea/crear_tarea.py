from collections.abc import Callable
from datetime import datetime

from gestor_tareas.aplicacion.comentario.anadir_comentario import (
    ahora_en_utc,
    instante_de_comentario,
)
from gestor_tareas.aplicacion.reintentos import reintentar_si_hay_conflicto
from gestor_tareas.aplicacion.tarea.asignar_grupo_estados import GrupoPedido
from gestor_tareas.aplicacion.tarea.asignar_workflow import WorkflowPedido
from gestor_tareas.aplicacion.tarea.resolver_catalogos import resolver_nombre, resolver_nombres
from gestor_tareas.dominio.etiqueta.repositorio import RepositorioEtiquetas
from gestor_tareas.dominio.grupo_estados.repositorio import RepositorioGruposEstados
from gestor_tareas.dominio.persona.repositorio import RepositorioPersonas
from gestor_tareas.dominio.subestado.repositorio import RepositorioSubestados
from gestor_tareas.dominio.tarea.entidades import Oportunidad, Tarea, TipoTarea
from gestor_tareas.dominio.tarea.repositorio import RepositorioTareas
from gestor_tareas.dominio.workflow.repositorio import RepositorioWorkflows


class CrearTarea:
    """Da de alta una tarea pendiente.

    Una tarea creada con un workflow recibe una subtarea por cada paso vigente del
    workflow, en su orden, pendiente y sin persona ni prioridad (ver
    ``WorkflowPedido``). El tipo de la tarea no le añade subtareas.

    El subestado (opcional) se busca en su catálogo como las etiquetas y se da de
    alta si no existe.

    Si nace en el estado DONE (el primero de su grupo), nace congelada desde este
    instante (ver ``Tarea.ajustar_congelacion``).
    """

    def __init__(
        self,
        repositorio: RepositorioTareas,
        repositorio_etiquetas: RepositorioEtiquetas,
        repositorio_personas: RepositorioPersonas,
        repositorio_workflows: RepositorioWorkflows,
        repositorio_grupos: RepositorioGruposEstados,
        reloj: Callable[[], datetime] = ahora_en_utc,
        *,
        repositorio_subestados: RepositorioSubestados | None = None,
    ) -> None:
        self._repositorio = repositorio
        self._repositorio_etiquetas = repositorio_etiquetas
        self._repositorio_personas = repositorio_personas
        self._repositorio_workflows = repositorio_workflows
        self._reloj = reloj
        self._repositorio_grupos = repositorio_grupos
        self._repositorio_subestados = repositorio_subestados

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
        workflow_id: int | None = None,
        subestado: str | None = None,
    ) -> Tarea:
        def guardar() -> Tarea:
            # Lo primero, para bloquear el workflow y el grupo antes que nada, en ese
            # orden (ver WorkflowPedido y GrupoPedido).
            workflow = WorkflowPedido(self._repositorio_workflows, workflow_id, self._reloj)
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
                subestado=resolver_nombre(self._repositorio_subestados, subestado),
            )
            tarea.subtareas = workflow.asignar(tarea)
            grupo.asignar(tarea)
            tarea.ajustar_congelacion(instante_de_comentario(self._reloj))
            return self._repositorio.crear(tarea)

        # Leer el workflow y el grupo de estados, dar de alta en los catálogos y
        # guardar la tarea es una sola transacción: si choca con otra petición
        # simultánea, se repite entera.
        return reintentar_si_hay_conflicto(guardar)
