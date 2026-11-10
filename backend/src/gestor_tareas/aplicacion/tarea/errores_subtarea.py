from gestor_tareas.dominio.excepciones import EntidadNoEncontradaError
from gestor_tareas.dominio.tarea.repositorio import RepositorioTareas


def subtarea_no_encontrada(
    repositorio: RepositorioTareas, id_tarea: int, id_subtarea: int
) -> EntidadNoEncontradaError:
    """Error de la tarea si no existe; si existe, el de la subtarea que no tiene."""
    if repositorio.obtener_por_id(id_tarea) is None:
        return EntidadNoEncontradaError(f"No existe la tarea con id {id_tarea}")
    return EntidadNoEncontradaError(
        f"No existe la subtarea con id {id_subtarea} en la tarea con id {id_tarea}"
    )
