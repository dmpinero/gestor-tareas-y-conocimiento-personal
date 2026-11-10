from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class TipoTarea(StrEnum):
    """Tipos de tarea. Una tarea puede no tener tipo.

    Cada tipo tiene sus propios datos, en un campo de ``Tarea`` con el nombre del
    tipo (``Tarea.oportunidad`` para ``OPORTUNIDAD``). Añadir un tipo es añadir
    aquí su valor, su entidad de datos y su campo en ``Tarea``, y guardarlos en
    su propia tabla.
    """

    OPORTUNIDAD = "oportunidad"


@dataclass
class Oportunidad:
    """Datos de una tarea de tipo ``TipoTarea.OPORTUNIDAD``.

    ``codigo`` es obligatorio (hasta 10 caracteres, no tiene por qué ser único);
    ``descripcion`` (hasta 200) y ``observaciones`` (hasta 5000) son opcionales.
    """

    codigo: str
    descripcion: str | None = None
    observaciones: str | None = None


@dataclass
class Tarea:
    """Tarea de la persona usuaria. La prioridad va de 1 (más prioritaria) a 5.

    ``fecha_creacion`` y ``fecha_vencimiento`` son fechas y horas locales sin zona
    horaria, tal como las escribe la persona usuaria, con precisión de segundos.
    ``etiquetas`` y ``asignados`` son los nombres del catálogo enlazados con la
    tarea, en orden alfabético sin distinguir mayúsculas.

    ``tipo`` es opcional. Los datos del tipo van en el campo con su nombre
    (``oportunidad``), que solo tiene valor cuando la tarea es de ese tipo.

    ``completada`` indica si la tarea está hecha; una tarea nueva está pendiente.
    """

    nombre: str
    descripcion: str
    fecha_creacion: datetime
    prioridad: int | None = None
    fecha_vencimiento: datetime | None = None
    etiquetas: list[str] = field(default_factory=list)
    asignados: list[str] = field(default_factory=list)
    tipo: TipoTarea | None = None
    oportunidad: Oportunidad | None = None
    completada: bool = False
    id: int | None = None
