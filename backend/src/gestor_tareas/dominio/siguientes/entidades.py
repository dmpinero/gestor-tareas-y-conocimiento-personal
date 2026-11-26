from dataclasses import dataclass


@dataclass(frozen=True)
class TareaSiguiente:
    """Una tarea de la cola de siguientes: las elegidas para trabajar en ellas después
    del foco actual, en orden. ``tarea_nombre`` es el nombre actual de la tarea."""

    tarea_id: int
    tarea_nombre: str
