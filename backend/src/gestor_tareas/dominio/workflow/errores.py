"""Mensajes de los errores de los workflows, comunes a todas las capas."""

from gestor_tareas.dominio.excepciones import (
    AsignacionDeWorkflowInvalidaError,
    EntidadNoEncontradaError,
    NombreDuplicadoError,
)


def _texto_workflow_no_encontrado(id_workflow: int) -> str:
    return f"No existe el workflow con id {id_workflow}"


def workflow_no_encontrado(id_workflow: int) -> EntidadNoEncontradaError:
    return EntidadNoEncontradaError(_texto_workflow_no_encontrado(id_workflow))


def paso_no_encontrado(id_workflow: int, id_paso: int) -> EntidadNoEncontradaError:
    return EntidadNoEncontradaError(
        f"No existe el paso con id {id_paso} en el workflow con id {id_workflow}"
    )


def workflow_duplicado(nombre: str) -> NombreDuplicadoError:
    return NombreDuplicadoError(f"Ya existe un workflow llamado «{nombre}»")


def workflow_no_asignable(id_workflow: int) -> AsignacionDeWorkflowInvalidaError:
    """El workflow pedido para una tarea no existe."""
    return AsignacionDeWorkflowInvalidaError(_texto_workflow_no_encontrado(id_workflow))
