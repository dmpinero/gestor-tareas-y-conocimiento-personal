from collections.abc import Callable
from datetime import UTC, datetime

from gestor_tareas.aplicacion.reintentos import reintentar_si_hay_conflicto
from gestor_tareas.dominio.comentario.entidades import Comentario
from gestor_tareas.dominio.comentario.repositorio import RepositorioComentarios
from gestor_tareas.dominio.excepciones import EntidadNoEncontradaError


def ahora_en_utc() -> datetime:
    return datetime.now(UTC)


def instante_de_comentario(reloj: Callable[[], datetime]) -> datetime:
    """El instante actual del reloj como lo guardan los comentarios (de tareas,
    subtareas y pasos): en UTC y sin fracción de segundo."""
    return reloj().astimezone(UTC).replace(microsecond=0)


class AnadirComentario:
    """Añade un comentario al histórico de una tarea existente.

    El instante de alta lo pone la aplicación, en UTC y sin fracción de segundo.
    """

    def __init__(
        self,
        repositorio: RepositorioComentarios,
        reloj: Callable[[], datetime] = ahora_en_utc,
    ) -> None:
        self._repositorio = repositorio
        self._reloj = reloj

    def ejecutar(self, id_tarea: int, texto: str) -> Comentario:
        def guardar() -> Comentario:
            creado = instante_de_comentario(self._reloj)
            comentario = self._repositorio.crear(
                Comentario(id_tarea=id_tarea, texto=texto, creado=creado)
            )
            if comentario is None:
                raise EntidadNoEncontradaError(f"No existe la tarea con id {id_tarea}")
            return comentario

        # Si choca con otra petición simultánea sobre la misma tarea, se repite.
        return reintentar_si_hay_conflicto(guardar)
