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
class PasoOportunidad:
    """Paso de una tarea de tipo ``TipoTarea.OPORTUNIDAD``, con su avance.

    Es una copia del paso del workflow de las oportunidades vigente al crear la
    tarea (mismo ``numero`` y ``nombre``), sin relación con él: cambiar el workflow
    después no altera las tareas ya creadas. ``hecho`` indica si el paso está
    hecho; al copiarlo está pendiente.
    """

    numero: int
    nombre: str
    hecho: bool = False
    id: int | None = None


@dataclass
class Subtarea:
    """Parte de una tarea, que solo existe dentro de ella.

    ``nombre`` es obligatorio (hasta 200 caracteres). ``asignado`` es el nombre de
    una persona del catálogo (como mucho una) y ``prioridad`` va de 1 a 5; ambos
    son opcionales. ``resuelta`` indica si está hecha; una subtarea nueva está
    pendiente.
    """

    nombre: str
    asignado: str | None = None
    prioridad: int | None = None
    resuelta: bool = False
    id: int | None = None


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

    ``pasos_oportunidad`` son los pasos de una oportunidad, ordenados por número.
    Solo los tiene una tarea creada como oportunidad (se copian del workflow al
    darla de alta), y los pierde si deja de serlo.

    ``subtareas`` son las subtareas de la tarea por orden de alta. Solo cambian con
    sus propias operaciones: editar la tarea o cambiar su tipo no las altera.
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
    pasos_oportunidad: list[PasoOportunidad] = field(default_factory=list)
    subtareas: list[Subtarea] = field(default_factory=list)
    id: int | None = None
