"""Mensajes de los errores del foco de trabajo, comunes a todas las capas."""

from gestor_tareas.dominio.excepciones import EntidadNoEncontradaError


def tarea_no_encontrada(id_tarea: int) -> EntidadNoEncontradaError:
    return EntidadNoEncontradaError(f"No existe la tarea con id {id_tarea}")


def subtarea_no_encontrada(id_tarea: int, id_subtarea: int) -> EntidadNoEncontradaError:
    return EntidadNoEncontradaError(
        f"No existe la subtarea con id {id_subtarea} en la tarea con id {id_tarea}"
    )
