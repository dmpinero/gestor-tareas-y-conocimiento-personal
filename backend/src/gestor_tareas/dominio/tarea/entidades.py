from dataclasses import dataclass


@dataclass
class Tarea:
    """Tarea de la persona usuaria. La prioridad va de 1 (más prioritaria) a 5."""

    nombre: str
    descripcion: str
    prioridad: int | None = None
    id: int | None = None
