from collections.abc import Callable
from datetime import datetime

from gestor_tareas.aplicacion.comentario.anadir_comentario import (
    ahora_en_utc,
    instante_de_comentario,
)
from gestor_tareas.aplicacion.reintentos import reintentar_si_hay_conflicto
from gestor_tareas.dominio.foco.entidades import Foco
from gestor_tareas.dominio.foco.errores import subtarea_no_encontrada, tarea_no_encontrada
from gestor_tareas.dominio.foco.repositorio import RepositorioFoco
from gestor_tareas.dominio.tarea.repositorio import RepositorioTareas


class ObtenerFoco:
    """Devuelve el foco de trabajo actual, o ``None`` si no hay."""

    def __init__(self, repositorio: RepositorioFoco) -> None:
        self._repositorio = repositorio

    def ejecutar(self) -> Foco | None:
        return self._repositorio.obtener()


class FijarFoco:
    """Pone en foco una tarea, o una subtarea de esa tarea, desde ahora.

    Sustituye en silencio al foco anterior (también si era el mismo: ``desde``
    vuelve a empezar). El instante lo pone la aplicación, en UTC y sin fracción de
    segundo. ``EntidadNoEncontradaError`` si la tarea no existe o la subtarea no es
    de ella; entonces el foco no cambia.
    """

    def __init__(
        self,
        repositorio: RepositorioFoco,
        repositorio_tareas: RepositorioTareas,
        reloj: Callable[[], datetime] = ahora_en_utc,
    ) -> None:
        self._repositorio = repositorio
        self._tareas = repositorio_tareas
        self._reloj = reloj

    def ejecutar(self, id_tarea: int, id_subtarea: int | None) -> Foco:
        def fijar() -> Foco:
            tarea = self._tareas.obtener_por_id(id_tarea)
            if tarea is None:
                raise tarea_no_encontrada(id_tarea)
            if id_subtarea is not None and all(s.id != id_subtarea for s in tarea.subtareas):
                raise subtarea_no_encontrada(id_tarea, id_subtarea)
            return self._repositorio.fijar(
                id_tarea, id_subtarea, instante_de_comentario(self._reloj)
            )

        return reintentar_si_hay_conflicto(fijar)


class QuitarFoco:
    """Deja sin foco; no hace nada si no había."""

    def __init__(self, repositorio: RepositorioFoco) -> None:
        self._repositorio = repositorio

    def ejecutar(self) -> None:
        reintentar_si_hay_conflicto(self._repositorio.quitar)
