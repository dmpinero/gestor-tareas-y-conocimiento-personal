from dataclasses import dataclass
from enum import StrEnum
from typing import NamedTuple


class Lista(StrEnum):
    """Las dos listas de entradas elegidas para después del foco. Una entrada está
    como mucho en una de ellas: añadirla a una la quita de la otra.

    ``SIGUIENTES`` es la cola «A continuación»; ``SUGERENCIAS``, las sugerencias
    elegidas por el usuario. El valor es el que se guarda."""

    SIGUIENTES = "siguientes"
    SUGERENCIAS = "sugerencias"


class ClaveDeEntrada(NamedTuple):
    """Lo que identifica una entrada de las listas: una tarea entera
    (``subtarea_id`` ``None``) o una subtarea suya. Una tarea y sus subtareas son
    entradas distintas y pueden estar a la vez."""

    tarea_id: int
    subtarea_id: int | None = None


@dataclass(frozen=True)
class TareaSiguiente:
    """Una entrada de una de las listas (la cola de siguientes o las sugerencias
    elegidas), en su orden: una tarea entera o una subtarea suya. Los nombres son los
    actuales; ``subtarea_id`` y ``subtarea_nombre`` son ``None`` en una tarea
    entera."""

    tarea_id: int
    tarea_nombre: str
    subtarea_id: int | None = None
    subtarea_nombre: str | None = None
