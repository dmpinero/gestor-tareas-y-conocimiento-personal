from collections.abc import Sequence

from gestor_tareas.aplicacion.reintentos import reintentar_si_hay_conflicto
from gestor_tareas.dominio.siguientes.entidades import TareaSiguiente
from gestor_tareas.dominio.siguientes.repositorio import RepositorioSiguientes


class _CasoDeUsoSiguientes:
    def __init__(self, repositorio: RepositorioSiguientes) -> None:
        self._repositorio = repositorio


class ListarSiguientes(_CasoDeUsoSiguientes):
    """La cola de siguientes en su orden, sin las tareas completadas."""

    def ejecutar(self) -> list[TareaSiguiente]:
        return self._repositorio.listar()


class AnadirASiguientes(_CasoDeUsoSiguientes):
    """Añade una tarea al final de la cola (si ya estaba, no cambia nada) y devuelve
    la cola. ``EntidadNoEncontradaError`` si la tarea no existe y
    ``TareaCompletadaEnLaColaError`` si está completada."""

    def ejecutar(self, id_tarea: int) -> list[TareaSiguiente]:
        return reintentar_si_hay_conflicto(lambda: self._repositorio.anadir(id_tarea))


class ReordenarSiguientes(_CasoDeUsoSiguientes):
    """Reordena la cola visible como dice ``ids`` (las completadas quedan detrás) y la
    devuelve. ``OrdenDeLaColaInvalidoError`` si ``ids`` no es exactamente la cola
    visible; entonces no cambia nada."""

    def ejecutar(self, ids: Sequence[int]) -> list[TareaSiguiente]:
        return reintentar_si_hay_conflicto(lambda: self._repositorio.reordenar(ids))


class QuitarDeSiguientes(_CasoDeUsoSiguientes):
    """Saca una tarea de la cola y la devuelve; si no estaba, no cambia nada."""

    def ejecutar(self, id_tarea: int) -> list[TareaSiguiente]:
        return reintentar_si_hay_conflicto(lambda: self._repositorio.quitar(id_tarea))
