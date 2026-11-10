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
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    false,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

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


class PasoOportunidadModelo(Base):
    """Paso de una tarea de tipo oportunidad, copiado del workflow al crearla.

    Es una copia: no tiene clave ajena a ``pasos_workflow_oportunidades``, así que
    cambiar o borrar los pasos del workflow no altera los de las tareas.
    """

    __tablename__ = "pasos_tarea"
    __table_args__ = (UniqueConstraint("tarea_id", "numero", name="uq_pasos_tarea_numero"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    tarea_id: Mapped[int] = mapped_column(
        ForeignKey("tareas.id", ondelete="CASCADE"), nullable=False
    )
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    nombre: Mapped[str] = mapped_column(String(50), nullable=False)
    hecho: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )


class TareaModelo(Base):
    __tablename__ = "tareas"
    __table_args__ = (
        CheckConstraint(
            "prioridad IS NULL OR prioridad BETWEEN 1 AND 5", name="ck_tareas_prioridad_rango"
        ),
        CheckConstraint(f"tipo IS NULL OR tipo IN ({_TIPOS_TAREA})", name="ck_tareas_tipo_valido"),
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
    # Pasos de la oportunidad, por número. Vaciar la lista borra sus filas
    # ("delete-orphan"); al borrar la tarea las borra el ON DELETE CASCADE.
    pasos_oportunidad: Mapped[list[PasoOportunidadModelo]] = relationship(
        lazy="selectin",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by=PasoOportunidadModelo.numero,
    )


class PasoWorkflowOportunidadModelo(Base):
    """Paso del workflow estándar de las oportunidades (hay un único workflow)."""

    __tablename__ = "pasos_workflow_oportunidades"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50), nullable=False)
    # Posición del paso, 1..n sin huecos. La unicidad la garantiza la base de datos;
    # por eso el repositorio renumera en dos fases (ver su `_renumerar`).
    numero: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)


__all__ = [
    "Base",
    "EtiquetaModelo",
    "OportunidadModelo",
    "PasoOportunidadModelo",
    "PasoWorkflowOportunidadModelo",
    "PersonaModelo",
    "TareaModelo",
    "tarea_etiquetas",
    "tarea_personas",
]
