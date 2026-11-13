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
class ReferenciaGrupoEstados:
    """Grupo de estados asignado a una tarea: la tarea apunta al grupo."""

    id: int
    nombre: str


@dataclass
class ReferenciaEstado:
    """Estado de su grupo en el que está una tarea."""

    id: int
    nombre: str


@dataclass
class ReferenciaWorkflow:
    """Workflow asignado a una tarea: la tarea apunta al workflow."""

    id: int
    nombre: str


@dataclass
class ComentarioInicial:
    """Comentario con el que nace una subtarea: la copia de uno del paso del workflow
    del que nace. ``creado`` es el instante de la copia (en UTC, sin fracción de
    segundo); nace sin editar."""

    texto: str
    creado: datetime


@dataclass
class Subtarea:
    """Parte de una tarea, que solo existe dentro de ella.

    ``nombre`` es obligatorio (hasta 200 caracteres). ``asignado`` es el nombre de
    una persona del catálogo (como mucho una) y ``prioridad`` va de 1 a 5; ambos
    son opcionales. ``resuelta`` indica si está hecha; una subtarea nueva está
    pendiente.

    ``comentarios`` es el número de comentarios de la subtarea; solo se lee (lo
    calcula el repositorio y se ignora al guardarla). ``comentarios_iniciales`` son
    los comentarios que recibe al darla de alta, en ese orden; solo se usan al
    guardar una subtarea nueva (al leerla va vacío).
    """

    nombre: str
    asignado: str | None = None
    prioridad: int | None = None
    resuelta: bool = False
    comentarios: int = 0
    id: int | None = None
    comentarios_iniciales: list[ComentarioInicial] = field(default_factory=list)


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

    ``subtareas`` son las subtareas de la tarea por orden de alta. Solo cambian con
    sus propias operaciones y al asignar a la tarea un workflow distinto del que
    tenía, que le añade al final una subtarea por cada paso del workflow, en su
    orden. El tipo de la tarea no añade subtareas.

    ``workflow`` es el workflow de la tarea (opcional).

    ``grupo_estados`` es el grupo de estados de la tarea (opcional) y ``estado`` el
    estado del grupo en el que está: los dos son ``None`` o el estado es de ese
    grupo.
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
    subtareas: list[Subtarea] = field(default_factory=list)
    grupo_estados: ReferenciaGrupoEstados | None = None
    estado: ReferenciaEstado | None = None
    workflow: ReferenciaWorkflow | None = None
    id: int | None = None
