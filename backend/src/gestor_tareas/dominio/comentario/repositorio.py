from typing import Protocol

from gestor_tareas.dominio.comentario.entidades import Comentario


class RepositorioComentarios(Protocol):
    """Puerto de persistencia para los comentarios de las tareas."""

    def crear(self, comentario: Comentario) -> Comentario | None:
        """Guarda un comentario nuevo de la tarea ``comentario.id_tarea`` y lo
        devuelve con su id, o ``None`` si la tarea no existe."""
        ...

    def listar_de_tarea(self, id_tarea: int) -> list[Comentario] | None:
        """Devuelve los comentarios de la tarea en orden cronológico (``creado`` y,
        a igual instante, por orden de alta), o ``None`` si la tarea no existe."""
        ...
