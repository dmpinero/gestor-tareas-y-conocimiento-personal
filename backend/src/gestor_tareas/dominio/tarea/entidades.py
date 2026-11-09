from dataclasses import dataclass
from datetime import datetime


@dataclass
class Tarea:
    """Tarea de la persona usuaria. La prioridad va de 1 (más prioritaria) a 5.

    ``fecha_hora`` es una fecha y hora local sin zona horaria, tal como la escribe
    la persona usuaria, con precisión de segundos.
    """

    nombre: str
    descripcion: str
    fecha_hora: datetime
    prioridad: int | None = None
    id: int | None = None
