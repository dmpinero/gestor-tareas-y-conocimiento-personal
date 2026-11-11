from collections.abc import Callable
from datetime import UTC, datetime

from gestor_tareas.aplicacion.comentario.anadir_comentario import ahora_en_utc
from gestor_tareas.aplicacion.comentario_subtarea.errores_comentario_subtarea import (
    comentario_no_encontrado,
)
from gestor_tareas.aplicacion.reintentos import reintentar_si_hay_conflicto
from gestor_tareas.dominio.comentario.entidades import ComentarioSubtarea
from gestor_tareas.dominio.comentario.repositorio import RepositorioComentariosSubtarea


class EditarComentarioSubtarea:
    """Sustituye el texto de un comentario de una subtarea y lo marca como editado.

    El instante de edición lo pone la aplicación, en UTC y sin fracción de segundo;
    el de alta no cambia.
    """

    def __init__(
        self,
        repositorio: RepositorioComentariosSubtarea,
        reloj: Callable[[], datetime] = ahora_en_utc,
    ) -> None:
        self._repositorio = repositorio
        self._reloj = reloj

    def ejecutar(
        self, id_tarea: int, id_subtarea: int, id_comentario: int, texto: str
    ) -> ComentarioSubtarea:
        def guardar() -> ComentarioSubtarea:
            editado = self._reloj().astimezone(UTC).replace(microsecond=0)
            comentario = self._repositorio.editar(
                id_tarea, id_subtarea, id_comentario, texto, editado
            )
            if comentario is None:
                raise comentario_no_encontrado(
                    self._repositorio, id_tarea, id_subtarea, id_comentario
                )
            return comentario

        # Si choca con otra petición simultánea sobre el mismo comentario, se repite.
        return reintentar_si_hay_conflicto(guardar)
