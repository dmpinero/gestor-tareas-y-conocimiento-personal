from collections.abc import Callable
from datetime import datetime

from gestor_tareas.aplicacion.comentario.anadir_comentario import (
    ahora_en_utc,
    instante_de_comentario,
)
from gestor_tareas.aplicacion.reintentos import reintentar_si_hay_conflicto
from gestor_tareas.dominio.excepciones import EntidadNoEncontradaError
from gestor_tareas.dominio.tarea.entidades import Tarea
from gestor_tareas.dominio.tarea.repositorio import RepositorioTareas


class HibernarTarea:
    """Hiberna una tarea existente: su contador de vencimiento deja de correr desde
    este instante (en UTC, sin fracción de segundo).

    Con ``comentario`` (HTML ya saneado), lo añade al histórico de la tarea como un
    comentario normal con ese mismo instante, en la misma transacción. Lanza
    ``EstadoDeHibernacionInvalidoError`` si ya estaba hibernada. El resto de datos de
    la tarea se conserva.
    """

    def __init__(
        self,
        repositorio: RepositorioTareas,
        reloj: Callable[[], datetime] = ahora_en_utc,
    ) -> None:
        self._repositorio = repositorio
        self._reloj = reloj

    def ejecutar(self, id_tarea: int, comentario: str | None = None) -> Tarea:
        def guardar() -> Tarea:
            tarea = self._repositorio.hibernar(
                id_tarea, instante_de_comentario(self._reloj), comentario
            )
            if tarea is None:
                raise EntidadNoEncontradaError(f"No existe la tarea con id {id_tarea}")
            return tarea

        # Si choca con otra petición simultánea sobre la misma tarea, se repite.
        return reintentar_si_hay_conflicto(guardar)
