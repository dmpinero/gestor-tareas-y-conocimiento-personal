from collections.abc import Callable
from datetime import UTC, datetime

from gestor_tareas.aplicacion.comentario.anadir_comentario import (
    ahora_en_utc,
    instante_de_comentario,
)
from gestor_tareas.aplicacion.reintentos import reintentar_si_hay_conflicto
from gestor_tareas.dominio.excepciones import FiltroDeListadoInvalidoError
from gestor_tareas.dominio.foco.entidades import Foco, PeriodoDeFoco
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

    En el historial cierra el periodo anterior (si lo había) y abre otro.
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
    """Deja sin foco y cierra ahora su periodo del historial; no hace nada si no
    había foco."""

    def __init__(
        self, repositorio: RepositorioFoco, reloj: Callable[[], datetime] = ahora_en_utc
    ) -> None:
        self._repositorio = repositorio
        self._reloj = reloj

    def ejecutar(self) -> None:
        reintentar_si_hay_conflicto(
            lambda: self._repositorio.quitar(instante_de_comentario(self._reloj))
        )


class ListarHistorialFoco:
    """Periodos del historial del foco cuyo inicio cae en ``[desde, hasta)``, del
    más reciente al más antiguo. Cada límite es opcional y se pasa a UTC.

    ``FiltroDeListadoInvalidoError`` si se dan los dos y ``desde`` no es anterior a
    ``hasta``.
    """

    def __init__(self, repositorio: RepositorioFoco) -> None:
        self._repositorio = repositorio

    def ejecutar(self, desde: datetime | None, hasta: datetime | None) -> list[PeriodoDeFoco]:
        desde_utc = desde.astimezone(UTC) if desde is not None else None
        hasta_utc = hasta.astimezone(UTC) if hasta is not None else None
        if desde_utc is not None and hasta_utc is not None and desde_utc >= hasta_utc:
            raise FiltroDeListadoInvalidoError("desde debe ser anterior a hasta")
        return self._repositorio.listar_historial(desde_utc, hasta_utc)
