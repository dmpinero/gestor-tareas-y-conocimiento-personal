from collections.abc import Callable
from datetime import datetime

from gestor_tareas.aplicacion.comentario.anadir_comentario import (
    ahora_en_utc,
    instante_de_comentario,
)
from gestor_tareas.aplicacion.comentario.errores_comentario import comentario_no_encontrado
from gestor_tareas.aplicacion.reintentos import reintentar_si_hay_conflicto
from gestor_tareas.dominio.comentario.entidades import Comentario
from gestor_tareas.dominio.comentario.repositorio import RepositorioComentarios


class EditarComentario:
    """Sustituye el texto de un comentario y lo marca como editado.

    El instante de edición lo pone la aplicación, en UTC y sin fracción de segundo;
    el de alta no cambia.
    """

    def __init__(
        self,
        repositorio: RepositorioComentarios,
        reloj: Callable[[], datetime] = ahora_en_utc,
    ) -> None:
        self._repositorio = repositorio
        self._reloj = reloj

    def ejecutar(self, id_tarea: int, id_comentario: int, texto: str) -> Comentario:
        def guardar() -> Comentario:
            editado = instante_de_comentario(self._reloj)
            comentario = self._repositorio.editar(id_tarea, id_comentario, texto, editado)
            if comentario is None:
                raise comentario_no_encontrado(self._repositorio, id_tarea, id_comentario)
            return comentario

        # Si choca con otra petición simultánea sobre el mismo comentario, se repite.
        return reintentar_si_hay_conflicto(guardar)
