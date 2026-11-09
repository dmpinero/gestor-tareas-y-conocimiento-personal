"""Modelos ORM de SQLAlchemy.

Cada modelo hereda de ``Base`` (ver ``sesion.py``) para registrarse en
``Base.metadata``, que es lo que Alembic compara con la base de datos al
generar migraciones con ``--autogenerate``.
"""

from datetime import datetime

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

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


class TareaModelo(Base):
    __tablename__ = "tareas"
    __table_args__ = (
        CheckConstraint(
            "prioridad IS NULL OR prioridad BETWEEN 1 AND 5", name="ck_tareas_prioridad_rango"
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


__all__ = [
    "Base",
    "EtiquetaModelo",
    "PersonaModelo",
    "TareaModelo",
    "tarea_etiquetas",
    "tarea_personas",
]
