"""Modelos ORM de SQLAlchemy.

Cada modelo hereda de ``Base`` (ver ``sesion.py``) para registrarse en
``Base.metadata``, que es lo que Alembic compara con la base de datos al
generar migraciones con ``--autogenerate``.
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    false,
    func,
    select,
)
from sqlalchemy.orm import Mapped, column_property, mapped_column, relationship

from gestor_tareas.dominio.tarea.entidades import TipoTarea
from gestor_tareas.infraestructura.persistencia.sesion import Base

# Intercalación de los nombres de los catálogos: sin distinguir mayúsculas pero sí
# tildes ("Urgente" = "URGENTE", "Cafe" ≠ "Café"). La de MySQL por defecto
# (utf8mb4_0900_ai_ci) tampoco distingue tildes, y el spec solo pide lo primero.
# El índice único y las búsquedas por nombre usan esta intercalación.
INTERCALACION_NOMBRES_CATALOGO = "utf8mb4_0900_as_ci"


class EtiquetaModelo(Base):
    __tablename__ = "etiquetas"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(
        String(50, collation=INTERCALACION_NOMBRES_CATALOGO), nullable=False, unique=True
    )


class PersonaModelo(Base):
    __tablename__ = "personas"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(
        String(100, collation=INTERCALACION_NOMBRES_CATALOGO), nullable=False, unique=True
    )


# Relaciones N:M. Borrar una tarea borra sus enlaces; borrar una etiqueta o una
# persona en uso lo impide la clave ajena (RESTRICT por defecto).
tarea_etiquetas = Table(
    "tarea_etiquetas",
    Base.metadata,
    Column("tarea_id", ForeignKey("tareas.id", ondelete="CASCADE"), primary_key=True),
    Column("etiqueta_id", ForeignKey("etiquetas.id"), primary_key=True),
)

tarea_personas = Table(
    "tarea_personas",
    Base.metadata,
    Column("tarea_id", ForeignKey("tareas.id", ondelete="CASCADE"), primary_key=True),
    Column("persona_id", ForeignKey("personas.id"), primary_key=True),
)


# Valores admitidos en `tareas.tipo`. Al añadir un tipo en `TipoTarea`, la
# migración que lo añada debe rehacer el CHECK con la nueva lista.
_TIPOS_TAREA = ", ".join(f"'{tipo.value}'" for tipo in TipoTarea)


class OportunidadModelo(Base):
    """Datos de una tarea de tipo oportunidad: como mucho una fila por tarea."""

    __tablename__ = "oportunidades"

    tarea_id: Mapped[int] = mapped_column(
        ForeignKey("tareas.id", ondelete="CASCADE"), primary_key=True
    )
    codigo: Mapped[str] = mapped_column(String(10), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # TEXT admite 65 535 bytes: 5000 caracteres de hasta 4 bytes caben de sobra. El
    # límite de 5000 caracteres lo valida la API.
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)


class ComentarioSubtareaModelo(Base):
    """Comentario del histórico de una subtarea; borrar la subtarea (o su tarea)
    borra sus comentarios.

    ``editado`` es el instante de su última edición, o NULL si nunca se editó.
    """

    __tablename__ = "comentarios_subtarea"

    id: Mapped[int] = mapped_column(primary_key=True)
    subtarea_id: Mapped[int] = mapped_column(
        ForeignKey("subtareas.id", ondelete="CASCADE"), nullable=False
    )
    texto: Mapped[str] = mapped_column(String(500), nullable=False)
    # DATETIME sin zona horaria con el instante en UTC (la columna no guarda la zona).
    creado: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    editado: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)


class SubtareaModelo(Base):
    """Subtarea de una tarea. Borrar la tarea borra sus subtareas; borrar una persona
    asignada a alguna lo impide la clave ajena (RESTRICT por defecto)."""

    __tablename__ = "subtareas"
    __table_args__ = (
        CheckConstraint(
            "prioridad IS NULL OR prioridad BETWEEN 1 AND 5", name="ck_subtareas_prioridad_rango"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tarea_id: Mapped[int] = mapped_column(
        ForeignKey("tareas.id", ondelete="CASCADE"), nullable=False
    )
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    persona_id: Mapped[int | None] = mapped_column(ForeignKey("personas.id"), nullable=True)
    prioridad: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resuelta: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    asignado: Mapped[PersonaModelo | None] = relationship(lazy="selectin")
    # Número de comentarios, calculado en la misma consulta que carga la subtarea
    # (subconsulta correlacionada): no es una columna de la tabla. Los comentarios
    # no se cargan con la subtarea.
    numero_comentarios: Mapped[int] = column_property(
        select(func.count(ComentarioSubtareaModelo.id))
        .where(ComentarioSubtareaModelo.subtarea_id == id)
        .correlate_except(ComentarioSubtareaModelo)
        .scalar_subquery()
    )


class ComentarioModelo(Base):
    """Comentario del histórico de una tarea; borrar la tarea borra sus comentarios.

    ``editado`` es el instante de su última edición, o NULL si nunca se editó.

    No hay relación desde ``TareaModelo``: los comentarios no se cargan con la tarea.
    """

    __tablename__ = "comentarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    tarea_id: Mapped[int] = mapped_column(
        ForeignKey("tareas.id", ondelete="CASCADE"), nullable=False
    )
    texto: Mapped[str] = mapped_column(String(500), nullable=False)
    # DATETIME sin zona horaria con el instante en UTC (la columna no guarda la zona).
    creado: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    editado: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)


class GrupoEstadosModelo(Base):
    """Grupo de estados que se asigna a las tareas. Su nombre es único sin distinguir
    mayúsculas (misma intercalación que los catálogos)."""

    __tablename__ = "grupos_estados"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(
        String(50, collation=INTERCALACION_NOMBRES_CATALOGO), nullable=False, unique=True
    )


class EstadoGrupoModelo(Base):
    """Estado de un grupo; borrar el grupo borra sus estados.

    La posición (1..n sin huecos) y el nombre son únicos dentro del grupo; por la
    unicidad de la posición el repositorio renumera en dos fases. La restricción
    única de (grupo_id, id) es la que permite a las tareas apuntar a la pareja
    grupo-estado con una clave ajena compuesta.
    """

    __tablename__ = "estados_grupo"
    __table_args__ = (
        UniqueConstraint("grupo_id", "posicion", name="uq_estados_grupo_posicion"),
        UniqueConstraint("grupo_id", "nombre", name="uq_estados_grupo_nombre"),
        UniqueConstraint("grupo_id", "id", name="uq_estados_grupo_grupo_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    grupo_id: Mapped[int] = mapped_column(
        ForeignKey("grupos_estados.id", ondelete="CASCADE"), nullable=False
    )
    nombre: Mapped[str] = mapped_column(
        String(50, collation=INTERCALACION_NOMBRES_CATALOGO), nullable=False
    )
    posicion: Mapped[int] = mapped_column(Integer, nullable=False)


class WorkflowModelo(Base):
    """Workflow con nombre cuyos pasos se añaden como subtareas a las tareas. Su
    nombre es único sin distinguir mayúsculas (misma intercalación que los
    catálogos)."""

    __tablename__ = "workflows"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(
        String(50, collation=INTERCALACION_NOMBRES_CATALOGO), nullable=False, unique=True
    )


class PasoWorkflowModelo(Base):
    """Paso de un workflow; borrar el workflow borra sus pasos.

    El número (posición del paso, 1..n sin huecos) es único dentro del workflow; por
    esa unicidad el repositorio renumera en dos fases. La restricción única empieza
    por ``workflow_id``, así que también sirve de índice de la clave ajena.
    """

    __tablename__ = "pasos_workflow"
    __table_args__ = (UniqueConstraint("workflow_id", "numero", name="uq_pasos_workflow_numero"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50), nullable=False)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    workflow_id: Mapped[int] = mapped_column(
        ForeignKey("workflows.id", name="fk_pasos_workflow_workflow", ondelete="CASCADE"),
        nullable=False,
    )


class TareaModelo(Base):
    """Tarea.

    El grupo de estados y el estado son los dos NULL o el estado es del grupo: lo
    garantizan el CHECK y la clave ajena compuesta (grupo_estados_id, estado_id) a
    (grupo_id, id) de ``estados_grupo``, que MySQL no comprueba si alguna de las dos
    es NULL. Las claves ajenas no tienen acción: borrar un grupo o un estado con
    tareas lo impide la base de datos, y el repositorio mueve o desasigna antes sus
    tareas en la misma transacción.

    El workflow es opcional y tampoco tiene acción: al borrar un workflow, el
    repositorio deja antes sus tareas sin workflow en la misma transacción.
    """

    __tablename__ = "tareas"
    __table_args__ = (
        CheckConstraint(
            "prioridad IS NULL OR prioridad BETWEEN 1 AND 5", name="ck_tareas_prioridad_rango"
        ),
        CheckConstraint(f"tipo IS NULL OR tipo IN ({_TIPOS_TAREA})", name="ck_tareas_tipo_valido"),
        CheckConstraint(
            "(grupo_estados_id IS NULL) = (estado_id IS NULL)",
            name="ck_tareas_grupo_y_estado",
        ),
        ForeignKeyConstraint(
            ["grupo_estados_id", "estado_id"],
            ["estados_grupo.grupo_id", "estados_grupo.id"],
            name="fk_tareas_estado_del_grupo",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    prioridad: Mapped[int | None] = mapped_column(Integer, nullable=True)
    descripcion: Mapped[str] = mapped_column(String(500), nullable=False)
    # DATETIME sin zona horaria: hora local tal como la escribe la persona usuaria.
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    fecha_vencimiento: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True
    )
    # "selectin" carga los enlaces de todas las tareas de un listado en una sola
    # consulta por relación, sin N+1.
    etiquetas: Mapped[list[EtiquetaModelo]] = relationship(
        secondary=tarea_etiquetas, lazy="selectin"
    )
    asignados: Mapped[list[PersonaModelo]] = relationship(secondary=tarea_personas, lazy="selectin")
    # Valor de `TipoTarea`, o NULL si la tarea no tiene tipo.
    tipo: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # Quitar la oportunidad (asignar None) borra su fila ("delete-orphan"); al borrar
    # la tarea la borra el ON DELETE CASCADE de la base de datos.
    oportunidad: Mapped[OportunidadModelo | None] = relationship(
        lazy="selectin", cascade="all, delete-orphan", passive_deletes=True
    )
    # El valor por defecto de la base de datos deja pendientes las filas que no lo
    # indican, como las que ya existían al añadir la columna.
    completada: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    # Subtareas por orden de alta. Al borrar la tarea las borra el ON DELETE CASCADE,
    # y con ellas sus comentarios.
    subtareas: Mapped[list[SubtareaModelo]] = relationship(
        lazy="selectin",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by=SubtareaModelo.id,
    )
    # Se guardan los ids; las relaciones solo sirven para leer los nombres.
    grupo_estados_id: Mapped[int | None] = mapped_column(
        ForeignKey("grupos_estados.id", name="fk_tareas_grupo_estados"), nullable=True
    )
    estado_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    grupo_estados: Mapped[GrupoEstadosModelo | None] = relationship(
        lazy="selectin", viewonly=True, foreign_keys=[grupo_estados_id]
    )
    estado: Mapped[EstadoGrupoModelo | None] = relationship(
        lazy="selectin",
        viewonly=True,
        primaryjoin=lambda: TareaModelo.estado_id == EstadoGrupoModelo.id,
        foreign_keys=[estado_id],
    )
    # Se guarda el id; la relación solo sirve para leer el nombre.
    workflow_id: Mapped[int | None] = mapped_column(
        ForeignKey("workflows.id", name="fk_tareas_workflow"), nullable=True
    )
    workflow: Mapped[WorkflowModelo | None] = relationship(
        lazy="selectin", viewonly=True, foreign_keys=[workflow_id]
    )


__all__ = [
    "Base",
    "ComentarioModelo",
    "ComentarioSubtareaModelo",
    "EstadoGrupoModelo",
    "EtiquetaModelo",
    "GrupoEstadosModelo",
    "OportunidadModelo",
    "PasoWorkflowModelo",
    "PersonaModelo",
    "SubtareaModelo",
    "TareaModelo",
    "WorkflowModelo",
    "tarea_etiquetas",
    "tarea_personas",
]
