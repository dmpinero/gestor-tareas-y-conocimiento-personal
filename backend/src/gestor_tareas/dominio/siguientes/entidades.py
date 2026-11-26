from dataclasses import dataclass
from enum import StrEnum


class Lista(StrEnum):
    """Las dos listas de tareas elegidas para después del foco. Una tarea está como
    mucho en una de ellas: añadirla a una la quita de la otra.

    ``SIGUIENTES`` es la cola «A continuación»; ``SUGERENCIAS``, las sugerencias
    elegidas por el usuario. El valor es el que se guarda."""

    SIGUIENTES = "siguientes"
    SUGERENCIAS = "sugerencias"


@dataclass(frozen=True)
class TareaSiguiente:
    """Una tarea de una de las listas (la cola de siguientes o las sugerencias
    elegidas), en su orden. ``tarea_nombre`` es el nombre actual de la tarea."""

    tarea_id: int
    tarea_nombre: str
