from collections.abc import Generator

import pytest
from sqlalchemy.orm import Session

from gestor_tareas.infraestructura.persistencia import modelos
from gestor_tareas.infraestructura.persistencia.sesion import FabricaSesiones


@pytest.fixture
def sesion_bd() -> Generator[Session, None, None]:
    """Sesión de base de datos real, con las tablas relevantes vacías al empezar."""
    sesion = FabricaSesiones()
    sesion.execute(modelos.TareaModelo.__table__.delete())
    sesion.commit()
    try:
        yield sesion
    finally:
        sesion.close()
