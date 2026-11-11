from gestor_tareas.dominio.comentario.repositorio import RepositorioComentarios
from gestor_tareas.dominio.excepciones import EntidadNoEncontradaError


def comentario_no_encontrado(
    repositorio: RepositorioComentarios, id_tarea: int, id_comentario: int
) -> EntidadNoEncontradaError:
    """Error de la tarea si no existe; si existe, el del comentario que no tiene."""
    if not repositorio.existe_tarea(id_tarea):
        return EntidadNoEncontradaError(f"No existe la tarea con id {id_tarea}")
    return EntidadNoEncontradaError(
        f"No existe el comentario con id {id_comentario} en la tarea con id {id_tarea}"
    )
