from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from gestor_tareas.configuracion import obtener_configuracion

configuracion = obtener_configuracion()

motor = create_engine(configuracion.url_base_datos, pool_pre_ping=True)

FabricaSesiones = sessionmaker(bind=motor, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Clase base declarativa para los modelos ORM de SQLAlchemy."""


def obtener_sesion() -> Generator[Session, None, None]:
    """Dependencia de FastAPI que entrega una sesión de base de datos por petición."""
    sesion = FabricaSesiones()
    try:
        yield sesion
    finally:
        sesion.close()
