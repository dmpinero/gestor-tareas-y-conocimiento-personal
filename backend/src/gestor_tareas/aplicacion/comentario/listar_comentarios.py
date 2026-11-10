from gestor_tareas.dominio.comentario.entidades import Comentario
from gestor_tareas.dominio.comentario.repositorio import RepositorioComentarios
from gestor_tareas.dominio.excepciones import EntidadNoEncontradaError


class ListarComentarios:
    """Devuelve el histórico de comentarios de una tarea en orden cronológico."""

    def __init__(self, repositorio: RepositorioComentarios) -> None:
        self._repositorio = repositorio

    def ejecutar(self, id_tarea: int) -> list[Comentario]:
        comentarios = self._repositorio.listar_de_tarea(id_tarea)
        if comentarios is None:
            raise EntidadNoEncontradaError(f"No existe la tarea con id {id_tarea}")
        return comentarios
