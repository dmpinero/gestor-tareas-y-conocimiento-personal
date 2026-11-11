from datetime import datetime
from typing import Protocol

from gestor_tareas.dominio.comentario.entidades import Comentario, ComentarioSubtarea


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

    def existe_tarea(self, id_tarea: int) -> bool:
        """Indica si existe la tarea con ese id."""
        ...

    def editar(
        self, id_tarea: int, id_comentario: int, texto: str, editado: datetime
    ) -> Comentario | None:
        """Sustituye el texto del comentario, guarda el instante ``editado`` y lo
        devuelve; ``creado`` no cambia. Devuelve ``None`` si la tarea no tiene un
        comentario con ese id (porque la tarea no existe, el comentario no existe o
        es de otra tarea)."""
        ...

    def eliminar(self, id_tarea: int, id_comentario: int) -> bool:
        """Borra el comentario. Devuelve ``False`` si la tarea no tiene un
        comentario con ese id (como en ``editar``)."""
        ...


class RepositorioComentariosSubtarea(Protocol):
    """Puerto de persistencia para los comentarios de las subtareas.

    Cada operación recibe la tarea y la subtarea: una subtarea de otra tarea se
    trata como si no existiera, y un comentario de otra subtarea también.
    """

    def crear(self, comentario: ComentarioSubtarea) -> ComentarioSubtarea | None:
        """Guarda un comentario nuevo de la subtarea ``comentario.id_subtarea`` y lo
        devuelve con su id, o ``None`` si la tarea ``comentario.id_tarea`` no tiene
        esa subtarea."""
        ...

    def listar_de_subtarea(
        self, id_tarea: int, id_subtarea: int
    ) -> list[ComentarioSubtarea] | None:
        """Devuelve los comentarios de la subtarea en orden cronológico (``creado``
        y, a igual instante, por orden de alta), o ``None`` si la tarea no tiene esa
        subtarea."""
        ...

    def existe_tarea(self, id_tarea: int) -> bool:
        """Indica si existe la tarea con ese id."""
        ...

    def existe_subtarea(self, id_tarea: int, id_subtarea: int) -> bool:
        """Indica si la tarea tiene una subtarea con ese id."""
        ...

    def editar(
        self, id_tarea: int, id_subtarea: int, id_comentario: int, texto: str, editado: datetime
    ) -> ComentarioSubtarea | None:
        """Sustituye el texto del comentario, guarda el instante ``editado`` y lo
        devuelve; ``creado`` no cambia. Devuelve ``None`` si la subtarea de esa tarea
        no tiene un comentario con ese id."""
        ...

    def eliminar(self, id_tarea: int, id_subtarea: int, id_comentario: int) -> bool:
        """Borra el comentario. Devuelve ``False`` si la subtarea de esa tarea no
        tiene un comentario con ese id (como en ``editar``)."""
        ...
