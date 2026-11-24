from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Foco:
    """La tarea, o la subtarea de una tarea, con la que se está trabajando ahora.

    Solo hay un foco a la vez: fijar otro sustituye al anterior. ``subtarea_id`` y
    ``subtarea_nombre`` son ``None`` cuando el foco es la tarea entera. Los nombres
    son los actuales de la tarea y la subtarea. ``desde`` es el instante (en UTC y
    sin fracción de segundo) en que se fijó el foco.

    Completar la tarea no quita el foco; borrar la tarea o la subtarea en foco, sí.
    """

    tarea_id: int
    tarea_nombre: str
    subtarea_id: int | None
    subtarea_nombre: str | None
    desde: datetime
