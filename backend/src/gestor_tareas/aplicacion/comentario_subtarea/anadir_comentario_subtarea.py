from collections.abc import Callable
from datetime import datetime

from gestor_tareas.aplicacion.comentario.anadir_comentario import (
    ahora_en_utc,
    instante_de_comentario,
)
from gestor_tareas.aplicacion.comentario_subtarea.errores_comentario_subtarea import (
    subtarea_no_encontrada,
)
from gestor_tareas.aplicacion.reintentos import reintentar_si_hay_conflicto
from gestor_tareas.dominio.comentario.entidades import ComentarioSubtarea
from gestor_tareas.dominio.comentario.repositorio import RepositorioComentariosSubtarea


class AnadirComentarioSubtarea:
    """Añade un comentario al histórico de una subtarea existente.

    El instante de alta lo pone la aplicación, en UTC y sin fracción de segundo,
    como en los comentarios de las tareas.
    """

    def __init__(
        self,
        repositorio: RepositorioComentariosSubtarea,
        reloj: Callable[[], datetime] = ahora_en_utc,
    ) -> None:
        self._repositorio = repositorio
        self._reloj = reloj

    def ejecutar(self, id_tarea: int, id_subtarea: int, texto: str) -> ComentarioSubtarea:
        def guardar() -> ComentarioSubtarea:
            creado = instante_de_comentario(self._reloj)
            comentario = self._repositorio.crear(
                ComentarioSubtarea(
                    id_tarea=id_tarea, id_subtarea=id_subtarea, texto=texto, creado=creado
                )
            )
            if comentario is None:
                raise subtarea_no_encontrada(self._repositorio, id_tarea, id_subtarea)
            return comentario

        # Si choca con otra petición simultánea sobre la misma subtarea, se repite.
        return reintentar_si_hay_conflicto(guardar)
