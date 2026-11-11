from gestor_tareas.aplicacion.comentario_subtarea.errores_comentario_subtarea import (
    comentario_no_encontrado,
)
from gestor_tareas.aplicacion.reintentos import reintentar_si_hay_conflicto
from gestor_tareas.dominio.comentario.repositorio import RepositorioComentariosSubtarea


class EliminarComentarioSubtarea:
    """Borra un comentario del histórico de una subtarea."""

    def __init__(self, repositorio: RepositorioComentariosSubtarea) -> None:
        self._repositorio = repositorio

    def ejecutar(self, id_tarea: int, id_subtarea: int, id_comentario: int) -> None:
        def borrar() -> None:
            if not self._repositorio.eliminar(id_tarea, id_subtarea, id_comentario):
                raise comentario_no_encontrado(
                    self._repositorio, id_tarea, id_subtarea, id_comentario
                )

        # Si choca con otra petición simultánea sobre el mismo comentario, se repite.
        reintentar_si_hay_conflicto(borrar)
