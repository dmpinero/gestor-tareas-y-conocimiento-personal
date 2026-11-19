from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from gestor_tareas.dominio.tarea.congelacion import instante_de_congelacion


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

    ``paso_id`` es el id del paso del workflow del que nace la subtarea, o ``None``
    si se añadió a mano o su paso ya no existe. Se fija al darla de alta y no cambia
    al renombrar el paso ni la subtarea.
    """

    nombre: str
    asignado: str | None = None
    prioridad: int | None = None
    resuelta: bool = False
    comentarios: int = 0
    id: int | None = None
    comentarios_iniciales: list[ComentarioInicial] = field(default_factory=list)
    paso_id: int | None = None


@dataclass
class SubtareasSincronizadas:
    """Cambios en las subtareas de una tarea al sincronizarla con su workflow.

    ``nuevas`` se añaden, pendientes y en ese orden, después de las que ya tiene, con
    sus ``comentarios_iniciales``; ``nombres`` da el nombre nuevo de cada subtarea
    que se renombra, por id.
    """

    id_tarea: int
    nuevas: list[Subtarea] = field(default_factory=list)
    nombres: dict[int, str] = field(default_factory=dict)


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

    ``subtareas`` son las subtareas de la tarea: primero las que nacen de un paso
    de su workflow, en el orden actual de esos pasos, y después las demás (añadidas
    a mano, de un paso eliminado o de otro workflow) por orden de alta. Solo cambian
    con sus propias operaciones y al asignar a la tarea un workflow distinto del que
    tenía, que le añade una subtarea por cada paso del workflow; reordenar o
    eliminar los pasos del workflow cambia su orden. El tipo de la tarea no añade
    subtareas.

    ``workflow`` es el workflow de la tarea (opcional).

    ``grupo_estados`` es el grupo de estados de la tarea (opcional) y ``estado`` el
    estado del grupo en el que está: los dos son ``None`` o el estado es de ese
    grupo.

    ``subestado`` es el nombre del subestado del catálogo de la tarea (como mucho
    uno; opcional).

    ``congelada_en`` es el instante (en UTC, sin fracción de segundo) desde el que
    su contador de vencimiento está congelado, o ``None`` si no lo está (ver
    ``gestor_tareas.dominio.tarea.congelacion``). Lo mantiene ``ajustar_congelacion``
    tras cada cambio de ``completada`` o de ``estado``.
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
    congelada_en: datetime | None = None
    subestado: str | None = None
    id: int | None = None

    def ajustar_congelacion(self, ahora: datetime) -> None:
        """Congela, conserva o descongela el contador según cómo ha quedado la tarea
        (``completada`` y ``estado``); ``ahora`` es el instante del cambio."""
        self.congelada_en = instante_de_congelacion(
            self.congelada_en,
            self.completada,
            self.estado.nombre if self.estado is not None else None,
            ahora,
        )
