"""Modelos ORM de SQLAlchemy.

Cada modelo hereda de ``Base`` (ver ``sesion.py``) para registrarse en
``Base.metadata``, que es lo que Alembic compara con la base de datos al
generar migraciones con ``--autogenerate``. Ejemplo de uso::

    from sqlalchemy import String
    from sqlalchemy.orm import Mapped, mapped_column

    class TareaModelo(Base):
        __tablename__ = "tareas"

        id: Mapped[int] = mapped_column(primary_key=True)
        titulo: Mapped[str] = mapped_column(String(200))

Todavía no hay modelos de dominio: se añadirán con las features de tareas y
conocimiento.
"""

from gestor_tareas.infraestructura.persistencia.sesion import Base

__all__ = ["Base"]
