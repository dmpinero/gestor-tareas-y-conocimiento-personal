"""Sincronización de las tareas abiertas de un workflow con sus pasos actuales.

Las subtareas son una copia de los pasos hecha al asignar el workflow; después de
editarlo, la persona usuaria puede pedir que sus tareas no completadas se pongan al
día (ver ``gestor_tareas.dominio.workflow.sincronizacion``). Antes se consultan los
cambios pendientes, sin modificar nada.
"""

from collections.abc import Callable
from datetime import datetime

from gestor_tareas.aplicacion.comentario.anadir_comentario import (
    ahora_en_utc,
    instante_de_comentario,
)
from gestor_tareas.aplicacion.reintentos import reintentar_si_hay_conflicto
from gestor_tareas.aplicacion.tarea.asignar_workflow import subtareas_de_pasos
from gestor_tareas.dominio.tarea.entidades import SubtareasSincronizadas
from gestor_tareas.dominio.tarea.repositorio import RepositorioTareas
from gestor_tareas.dominio.workflow.errores import workflow_no_encontrado
from gestor_tareas.dominio.workflow.repositorio import RepositorioWorkflows
from gestor_tareas.dominio.workflow.sincronizacion import CambiosDeTarea, cambios_pendientes


class VerCambiosDeLasTareas:
    """Los cambios que haría sincronizar las tareas abiertas del workflow, sin
    modificar nada. Lanza ``EntidadNoEncontradaError`` si el workflow no existe."""

    def __init__(self, workflows: RepositorioWorkflows, tareas: RepositorioTareas) -> None:
        self._workflows = workflows
        self._tareas = tareas

    def ejecutar(self, id_workflow: int) -> list[CambiosDeTarea]:
        workflow = next((w for w in self._workflows.listar() if w.id == id_workflow), None)
        if workflow is None:
            raise workflow_no_encontrado(id_workflow)
        return cambios_pendientes(workflow, self._tareas.listar_abiertas_de_workflow(id_workflow))


class SincronizarTareas:
    """Pone al día las tareas abiertas del workflow y devuelve lo que ha cambiado.

    Cada paso sin subtarea vinculada da una subtarea nueva como al asignar el
    workflow (ver ``subtareas_de_pasos``), y cada subtarea vinculada toma el nombre
    actual de su paso. Repetirlo no cambia nada. Lanza ``EntidadNoEncontradaError``
    si el workflow no existe.
    """

    def __init__(
        self,
        workflows: RepositorioWorkflows,
        tareas: RepositorioTareas,
        reloj: Callable[[], datetime] = ahora_en_utc,
    ) -> None:
        self._workflows = workflows
        self._tareas = tareas
        self._reloj = reloj

    def ejecutar(self, id_workflow: int) -> list[CambiosDeTarea]:
        def sincronizar() -> list[CambiosDeTarea]:
            # Primero el workflow (bloqueo compartido) y después las tareas, el mismo
            # orden que al asignar un workflow a una tarea (ver WorkflowPedido).
            workflow = self._workflows.leer_para_copiar(id_workflow)
            if workflow is None:
                raise workflow_no_encontrado(id_workflow)
            tareas = self._tareas.listar_abiertas_de_workflow(id_workflow, para_modificar=True)
            cambios = cambios_pendientes(workflow, tareas)
            copia = instante_de_comentario(self._reloj)
            self._tareas.sincronizar_subtareas(
                [
                    SubtareasSincronizadas(
                        id_tarea=c.id_tarea,
                        nuevas=subtareas_de_pasos(c.pasos_nuevos, copia),
                        nombres={r.id_subtarea: r.nombre_nuevo for r in c.renombres},
                    )
                    for c in cambios
                ]
            )
            return cambios

        return reintentar_si_hay_conflicto(sincronizar)
