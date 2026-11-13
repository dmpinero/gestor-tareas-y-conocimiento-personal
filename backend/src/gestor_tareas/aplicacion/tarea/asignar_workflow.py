from gestor_tareas.dominio.tarea.entidades import ReferenciaWorkflow, Subtarea, Tarea
from gestor_tareas.dominio.workflow.errores import workflow_no_asignable
from gestor_tareas.dominio.workflow.repositorio import RepositorioWorkflows


class WorkflowPedido:
    """Workflow pedido para una tarea, leído al principio de la transacción.

    Se lee lo primero, antes que el grupo de estados y la tarea, para tomar los
    bloqueos siempre en el mismo orden (workflow, grupo y tarea), y se valida
    después, para que una tarea que no existe responda que no existe aunque el
    workflow tampoco valga.
    """

    def __init__(self, repositorio: RepositorioWorkflows, id_workflow: int | None) -> None:
        self._id_workflow = id_workflow
        self._workflow = (
            repositorio.leer_para_copiar(id_workflow) if id_workflow is not None else None
        )

    def asignar(self, tarea: Tarea) -> list[Subtarea]:
        """Deja la tarea con el workflow pedido y devuelve las subtareas que recibe.

        Si el workflow es distinto del que tenía la tarea (también si no tenía
        ninguno), recibe una subtarea pendiente, sin persona ni prioridad, por cada
        paso del workflow en su orden; con el mismo workflow o sin workflow, no
        recibe ninguna. Es una copia fija: las subtareas no guardan relación con los
        pasos, así que cambiar el workflow después no las altera. Lanza
        ``AsignacionDeWorkflowInvalidaError`` si el workflow no existe.
        """
        if self._id_workflow is None:
            tarea.workflow = None
            return []
        if self._workflow is None:
            raise workflow_no_asignable(self._id_workflow)
        anterior = tarea.workflow.id if tarea.workflow is not None else None
        tarea.workflow = ReferenciaWorkflow(id=self._workflow.id, nombre=self._workflow.nombre)
        if anterior == self._workflow.id:
            return []
        pasos = sorted(self._workflow.pasos, key=lambda paso: paso.numero or 0)
        return [Subtarea(nombre=paso.nombre) for paso in pasos]
