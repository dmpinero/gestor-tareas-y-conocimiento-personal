from datetime import datetime
from typing import Protocol

from gestor_tareas.dominio.foco.entidades import Foco, PeriodoDeFoco


class RepositorioFoco(Protocol):
    """Puerto de persistencia del foco de trabajo (como mucho uno) y de su historial.

    El historial guarda un periodo por cada vez que se fija el foco; el periodo del
    foco actual es el único en curso (sin ``hasta``), y solo existe si hay foco.
    """

    def obtener(self) -> Foco | None:
        """Devuelve el foco actual con los nombres actuales de su tarea y su subtarea,
        o ``None`` si no hay foco."""
        ...

    def fijar(self, id_tarea: int, id_subtarea: int | None, desde: datetime) -> Foco:
        """Pone en foco la tarea (o su subtarea) desde ese instante, sustituyendo al
        foco anterior si lo había, y confirma. La subtarea debe ser de la tarea.

        En la misma transacción cierra el periodo en curso del historial (``hasta =
        desde``), si lo había, y abre otro con los nombres actuales; y saca de la cola
        de siguientes (o de las sugerencias elegidas) la entrada de la tarea entera,
        si estaba, y si el foco es una subtarea, también la de esa subtarea. Las
        entradas de otras subtareas de la tarea se quedan.

        Lanza ``EntidadNoEncontradaError`` si la tarea o la subtarea ya no existen
        (p. ej. otra petición las ha borrado); el foco anterior no cambia."""
        ...

    def quitar(self, hasta: datetime) -> None:
        """Deja sin foco, cierra el periodo en curso del historial en ``hasta`` y
        confirma. No hace nada si no había foco."""
        ...

    def cerrar_periodo_de_tarea(self, id_tarea: int, hasta: datetime) -> None:
        """Cierra en ``hasta`` el periodo en curso si es de esa tarea (o de una
        subtarea suya); si no, no hace nada. Además guarda en todos los periodos de
        la tarea sus nombres actuales, para conservarlos al borrarla.

        No confirma: va en la transacción de quien borra la tarea (la misma sesión),
        para que el periodo se cierre solo si el borrado se confirma."""
        ...

    def cerrar_periodo_de_subtarea(self, id_tarea: int, id_subtarea: int, hasta: datetime) -> None:
        """Cierra en ``hasta`` el periodo en curso si es de esa subtarea de esa tarea;
        si no, no hace nada. Además guarda en los periodos de la subtarea sus nombres
        actuales. No confirma, como ``cerrar_periodo_de_tarea``."""
        ...

    def listar_historial(
        self, desde: datetime | None, hasta: datetime | None
    ) -> list[PeriodoDeFoco]:
        """Periodos cuyo ``desde`` cae en ``[desde, hasta)`` (cada límite, si se da),
        del más reciente al más antiguo."""
        ...
