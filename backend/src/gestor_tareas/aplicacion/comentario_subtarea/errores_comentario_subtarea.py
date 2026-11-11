from gestor_tareas.dominio.comentario.repositorio import RepositorioComentariosSubtarea
from gestor_tareas.dominio.excepciones import EntidadNoEncontradaError


def subtarea_no_encontrada(
    repositorio: RepositorioComentariosSubtarea, id_tarea: int, id_subtarea: int
) -> EntidadNoEncontradaError:
    """Error de la tarea si no existe; si existe, el de la subtarea que no tiene."""
    if not repositorio.existe_tarea(id_tarea):
        return EntidadNoEncontradaError(f"No existe la tarea con id {id_tarea}")
    return EntidadNoEncontradaError(
        f"No existe la subtarea con id {id_subtarea} en la tarea con id {id_tarea}"
    )


def comentario_no_encontrado(
    repositorio: RepositorioComentariosSubtarea,
    id_tarea: int,
    id_subtarea: int,
    id_comentario: int,
) -> EntidadNoEncontradaError:
    """Error de la tarea o de la subtarea si no existen; si existen, el del
    comentario que no tiene la subtarea."""
    if not repositorio.existe_subtarea(id_tarea, id_subtarea):
        return subtarea_no_encontrada(repositorio, id_tarea, id_subtarea)
    return EntidadNoEncontradaError(
        f"No existe el comentario con id {id_comentario} en la subtarea con id {id_subtarea}"
    )
