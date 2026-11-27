from collections.abc import Sequence

from gestor_tareas.aplicacion.reintentos import reintentar_si_hay_conflicto
from gestor_tareas.dominio.siguientes.entidades import ClaveDeEntrada, Lista, TareaSiguiente
from gestor_tareas.dominio.siguientes.repositorio import RepositorioSiguientes


class _CasoDeUsoSiguientes:
    """Base de los casos de uso; ``_LISTA`` es la lista sobre la que actúan. Cada
    entrada es una tarea entera (``id_subtarea`` ``None``) o una subtarea suya."""

    _LISTA = Lista.SIGUIENTES

    def __init__(self, repositorio: RepositorioSiguientes) -> None:
        self._repositorio = repositorio


class ListarSiguientes(_CasoDeUsoSiguientes):
    """La cola de siguientes en su orden, sin las entradas de tareas completadas ni de
    subtareas resueltas."""

    def ejecutar(self) -> list[TareaSiguiente]:
        return self._repositorio.listar(self._LISTA)


class AnadirASiguientes(_CasoDeUsoSiguientes):
    """Añade una entrada (una tarea, o una subtarea suya) al final de la cola (si
    estaba en sugerencias, la saca de ellas; si ya estaba en la cola, no cambia nada)
    y devuelve la cola. ``EntidadNoEncontradaError`` si la tarea no existe o la
    subtarea no es suya, ``TareaCompletadaEnLaColaError`` si la tarea está completada
    y ``SubtareaResueltaEnLaColaError`` si la subtarea está resuelta."""

    def ejecutar(self, id_tarea: int, id_subtarea: int | None = None) -> list[TareaSiguiente]:
        return reintentar_si_hay_conflicto(
            lambda: self._repositorio.anadir(id_tarea, self._LISTA, id_subtarea)
        )


class ReordenarSiguientes(_CasoDeUsoSiguientes):
    """Reordena la cola visible como dice ``claves`` (las que no se ven quedan detrás)
    y la devuelve. ``OrdenDeLaColaInvalidoError`` si ``claves`` no es exactamente la
    cola visible; entonces no cambia nada."""

    def ejecutar(self, claves: Sequence[ClaveDeEntrada]) -> list[TareaSiguiente]:
        return reintentar_si_hay_conflicto(lambda: self._repositorio.reordenar(claves, self._LISTA))


class QuitarDeSiguientes(_CasoDeUsoSiguientes):
    """Saca una entrada de la cola y la devuelve; si no estaba, no cambia nada (si
    está en sugerencias, sigue en ellas). Quitar la tarea entera no quita las
    entradas de sus subtareas."""

    def ejecutar(self, id_tarea: int, id_subtarea: int | None = None) -> list[TareaSiguiente]:
        return reintentar_si_hay_conflicto(
            lambda: self._repositorio.quitar(id_tarea, self._LISTA, id_subtarea)
        )


class ListarSugerencias(ListarSiguientes):
    """Las sugerencias elegidas en su orden, sin las entradas de tareas completadas ni
    de subtareas resueltas."""

    _LISTA = Lista.SUGERENCIAS


class AnadirASugerencias(AnadirASiguientes):
    """Añade una entrada al final de las sugerencias elegidas (si estaba en la cola,
    la saca de ella; si ya estaba en sugerencias, no cambia nada) y las devuelve.
    Mismos errores que ``AnadirASiguientes``."""

    _LISTA = Lista.SUGERENCIAS


class QuitarDeSugerencias(QuitarDeSiguientes):
    """Saca una entrada de las sugerencias elegidas y las devuelve; si no estaba, no
    cambia nada (si está en la cola, sigue en ella)."""

    _LISTA = Lista.SUGERENCIAS
