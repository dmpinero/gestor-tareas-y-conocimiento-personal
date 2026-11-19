from collections.abc import Callable
from datetime import datetime
from enum import Enum

from gestor_tareas.aplicacion.comentario.anadir_comentario import (
    ahora_en_utc,
    instante_de_comentario,
)
from gestor_tareas.aplicacion.reintentos import reintentar_si_hay_conflicto
from gestor_tareas.aplicacion.tarea.asignar_grupo_estados import GrupoPedido
from gestor_tareas.aplicacion.tarea.asignar_workflow import WorkflowPedido
from gestor_tareas.aplicacion.tarea.resolver_catalogos import resolver_nombre, resolver_nombres
from gestor_tareas.dominio.etiqueta.repositorio import RepositorioEtiquetas
from gestor_tareas.dominio.excepciones import EntidadNoEncontradaError
from gestor_tareas.dominio.grupo_estados.repositorio import RepositorioGruposEstados
from gestor_tareas.dominio.persona.repositorio import RepositorioPersonas
from gestor_tareas.dominio.subestado.repositorio import RepositorioSubestados
from gestor_tareas.dominio.tarea.entidades import Oportunidad, Tarea, TipoTarea
from gestor_tareas.dominio.tarea.repositorio import RepositorioTareas
from gestor_tareas.dominio.workflow.repositorio import RepositorioWorkflows


class Conservar(Enum):
    """Valor de un dato que la edición no cambia (``ActualizarTarea``)."""

    SUBESTADO = "subestado"


class ActualizarTarea:
    """Sustituye todos los datos editables de una tarea ya existente.

    Las etiquetas y personas asignadas sustituyen por completo a las anteriores, y
    también el tipo y sus datos (sin tipo, la tarea pierde sus datos de
    oportunidad).

    El tipo no cambia las subtareas. El workflow también se sustituye: con uno
    distinto del que tenía (también si no tenía ninguno), la tarea recibe una
    subtarea nueva por cada paso del workflow, en su orden, después de las que ya
    tiene; con el mismo workflow o sin workflow, sus subtareas no cambian (ver
    ``WorkflowPedido``).

    El grupo de estados también se sustituye: con el mismo grupo, la tarea conserva
    su estado; con otro, queda en su primer estado, y sin grupo, sin estado. Con el
    estado en que queda, la tarea se congela, conserva su instante de congelación o
    deja de estar congelada (ver ``Tarea.ajustar_congelacion``); cambiar solo el
    vencimiento no cambia ese instante.

    El subestado es el único dato que no se sustituye si no se indica
    (``Conservar.SUBESTADO``, el valor por defecto): con un nombre se busca en su
    catálogo como las etiquetas (y se da de alta si no existe) y con ``None`` la
    tarea queda sin subestado.
    """

    def __init__(
        self,
        repositorio: RepositorioTareas,
        repositorio_etiquetas: RepositorioEtiquetas,
        repositorio_personas: RepositorioPersonas,
        repositorio_grupos: RepositorioGruposEstados,
        repositorio_workflows: RepositorioWorkflows,
        reloj: Callable[[], datetime] = ahora_en_utc,
        *,
        repositorio_subestados: RepositorioSubestados | None = None,
    ) -> None:
        self._repositorio = repositorio
        self._repositorio_etiquetas = repositorio_etiquetas
        self._repositorio_personas = repositorio_personas
        self._repositorio_grupos = repositorio_grupos
        self._repositorio_workflows = repositorio_workflows
        self._reloj = reloj
        self._repositorio_subestados = repositorio_subestados

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
        grupo_estados_id: int | None = None,
        workflow_id: int | None = None,
        subestado: str | None | Conservar = Conservar.SUBESTADO,
    ) -> Tarea:
        def guardar() -> Tarea:
            # Primero el workflow, después el grupo y por último la tarea (ver
            # WorkflowPedido y GrupoPedido). La tarea se lee con bloqueo: así se
            # conservan el estado y el workflow que tiene ahora, no los de una
            # lectura anterior.
            workflow = WorkflowPedido(self._repositorio_workflows, workflow_id, self._reloj)
            grupo = GrupoPedido(self._repositorio_grupos, grupo_estados_id)
            # El subestado se bloquea (o se da de alta) antes que la tarea, como el
            # workflow y el grupo, para que su borrado no se cruce con este guardado.
            nuevo_subestado = (
                subestado
                if isinstance(subestado, Conservar)
                else resolver_nombre(self._repositorio_subestados, subestado)
            )
            tarea = self._repositorio.obtener_para_modificar(id_tarea)
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
            if not isinstance(nuevo_subestado, Conservar):
                tarea.subestado = nuevo_subestado
            subtareas_nuevas = workflow.asignar(tarea)
            grupo.asignar(tarea)
            tarea.ajustar_congelacion(instante_de_comentario(self._reloj))
            return self._repositorio.actualizar(tarea, subtareas_nuevas)

        # Leer la tarea, dar de alta en los catálogos y guardar es una sola
        # transacción: si choca con otra petición simultánea, se repite entera.
        return reintentar_si_hay_conflicto(guardar)
