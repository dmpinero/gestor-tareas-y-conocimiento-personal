from gestor_tareas.aplicacion.comentario_subtarea.errores_comentario_subtarea import (
    subtarea_no_encontrada,
)
from gestor_tareas.dominio.comentario.entidades import ComentarioSubtarea
from gestor_tareas.dominio.comentario.repositorio import RepositorioComentariosSubtarea


class ListarComentariosSubtarea:
    """Devuelve el histórico de comentarios de una subtarea en orden cronológico."""

    def __init__(self, repositorio: RepositorioComentariosSubtarea) -> None:
        self._repositorio = repositorio

    def ejecutar(self, id_tarea: int, id_subtarea: int) -> list[ComentarioSubtarea]:
        comentarios = self._repositorio.listar_de_subtarea(id_tarea, id_subtarea)
        if comentarios is None:
            raise subtarea_no_encontrada(self._repositorio, id_tarea, id_subtarea)
        return comentarios
