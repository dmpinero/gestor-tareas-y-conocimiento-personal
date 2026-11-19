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
    LargeBinary,
    String,
    Table,
    Text,
    UniqueConstraint,
    false,
    func,
    select,
)
from sqlalchemy.dialects.mysql import MEDIUMBLOB, MEDIUMTEXT
from sqlalchemy.orm import (
    Mapped,
    WriteOnlyMapped,
    column_property,
    mapped_column,
    relationship,
)

from gestor_tareas.dominio.tarea.entidades import TipoTarea
from gestor_tareas.infraestructura.persistencia.sesion import Base

# Intercalación de los nombres de los catálogos: sin distinguir mayúsculas pero sí
# tildes ("Urgente" = "URGENTE", "Cafe" ≠ "Café"). La de MySQL por defecto
# (utf8mb4_0900_ai_ci) tampoco distingue tildes, y el spec solo pide lo primero.
# El índice único y las búsquedas por nombre usan esta intercalación.
INTERCALACION_NOMBRES_CATALOGO = "utf8mb4_0900_as_ci"

# Tipo de la columna `texto` de los comentarios (de tareas, subtareas y pasos).
_TEXTO_COMENTARIO = Text().with_variant(MEDIUMTEXT(), "mysql")


class ImagenModelo(Base):
    """Imagen subida para los comentarios. No tiene claves ajenas: los comentarios
    la usan por su URL dentro de su HTML, y varios pueden usar la misma."""

    __tablename__ = "imagenes"

    # UUID4 en hexadecimal: la URL de la imagen no se puede adivinar.
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    tamano: Mapped[int] = mapped_column(Integer, nullable=False)
    # MEDIUMBLOB admite hasta 16 MB; la API limita cada imagen a 5 MB. Así las
    # copias de seguridad de la base de datos incluyen las imágenes.
    contenido: Mapped[bytes] = mapped_column(
        LargeBinary().with_variant(MEDIUMBLOB(), "mysql"), nullable=False
    )
    # DATETIME sin zona horaria con el instante en UTC.
    creada: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)


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


class SubestadoModelo(Base):
    """Subestado del catálogo. Una tarea tiene como mucho uno; borrarlo deja sus
    tareas sin subestado (ON DELETE SET NULL de ``tareas.subestado_id``)."""

    __tablename__ = "subestados"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(
        String(50, collation=INTERCALACION_NOMBRES_CATALOGO), nullable=False, unique=True
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
    # HTML saneado: MEDIUMTEXT admite 16 MB y la API limita el HTML a 50000
    # caracteres (de hasta 4 bytes), así que cabe de sobra.
    texto: Mapped[str] = mapped_column(_TEXTO_COMENTARIO, nullable=False)
    # DATETIME sin zona horaria con el instante en UTC (la columna no guarda la zona).
    creado: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    editado: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)


class SubtareaModelo(Base):
    """Subtarea de una tarea. Borrar la tarea borra sus subtareas; borrar una persona
    asignada a alguna lo impide la clave ajena (RESTRICT por defecto).

    ``paso_id`` es el paso del workflow del que nace, o NULL si se añadió a mano:
    borrar el paso (o su workflow) conserva la subtarea y la deja sin paso.
    """

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
    paso_id: Mapped[int | None] = mapped_column(
        ForeignKey("pasos_workflow.id", name="fk_subtareas_paso", ondelete="SET NULL"),
        nullable=True,
    )
    # Solo para leer el workflow y el número del paso, que deciden el orden de la
    # subtarea en su tarea; "selectin" los carga para todo un listado en una consulta.
    paso: Mapped["PasoWorkflowModelo | None"] = relationship(
        lazy="selectin", viewonly=True, foreign_keys=[paso_id]
    )
    # Solo para dar de alta los comentarios con los que nace la subtarea en la misma
    # transacción ("write_only": nunca se cargan). Al borrar la subtarea los borra el
    # ON DELETE CASCADE.
    comentarios: WriteOnlyMapped[ComentarioSubtareaModelo] = relationship(passive_deletes=True)
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
    # HTML saneado: MEDIUMTEXT admite 16 MB y la API limita el HTML a 50000
    # caracteres (de hasta 4 bytes), así que cabe de sobra.
    texto: Mapped[str] = mapped_column(_TEXTO_COMENTARIO, nullable=False)
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


class ComentarioPasoModelo(Base):
    """Comentario del histórico de un paso de un workflow; borrar el paso (o su
    workflow) borra sus comentarios.

    ``editado`` es el instante de su última edición, o NULL si nunca se editó.
    """

    __tablename__ = "comentarios_paso_workflow"

    id: Mapped[int] = mapped_column(primary_key=True)
    paso_id: Mapped[int] = mapped_column(
        ForeignKey(
            "pasos_workflow.id", name="fk_comentarios_paso_workflow_paso", ondelete="CASCADE"
        ),
        nullable=False,
    )
    # HTML saneado: MEDIUMTEXT admite 16 MB y la API limita el HTML a 50000
    # caracteres (de hasta 4 bytes), así que cabe de sobra.
    texto: Mapped[str] = mapped_column(_TEXTO_COMENTARIO, nullable=False)
    # DATETIME sin zona horaria con el instante en UTC (la columna no guarda la zona).
    creado: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    editado: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)


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
    # Número de comentarios, calculado en la misma consulta que carga el paso
    # (subconsulta correlacionada, sin bloqueo): no es una columna de la tabla.
    numero_comentarios: Mapped[int] = column_property(
        select(func.count(ComentarioPasoModelo.id))
        .where(ComentarioPasoModelo.paso_id == id)
        .correlate_except(ComentarioPasoModelo)
        .scalar_subquery()
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
    # Subtareas por orden de alta (el repositorio las ordena después por los pasos de
    # su workflow). Al borrar la tarea las borra el ON DELETE CASCADE, y con ellas sus
    # comentarios.
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
    # Instante desde el que su contador de vencimiento está congelado (completada o en
    # el estado DONE), o NULL si no lo está. DATETIME sin zona horaria con el instante
    # en UTC (la columna no guarda la zona).
    congelada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    # Subestado opcional del catálogo. Borrar el subestado deja la tarea sin él (lo
    # hace la base de datos con ON DELETE SET NULL).
    subestado_id: Mapped[int | None] = mapped_column(
        ForeignKey("subestados.id", name="fk_tareas_subestado", ondelete="SET NULL"),
        nullable=True,
    )
    subestado: Mapped[SubestadoModelo | None] = relationship(
        lazy="selectin", foreign_keys=[subestado_id]
    )


__all__ = [
    "Base",
    "ComentarioModelo",
    "ComentarioPasoModelo",
    "ComentarioSubtareaModelo",
    "EstadoGrupoModelo",
    "EtiquetaModelo",
    "GrupoEstadosModelo",
    "OportunidadModelo",
    "PasoWorkflowModelo",
    "PersonaModelo",
    "SubestadoModelo",
    "SubtareaModelo",
    "TareaModelo",
    "WorkflowModelo",
    "tarea_etiquetas",
    "tarea_personas",
]
