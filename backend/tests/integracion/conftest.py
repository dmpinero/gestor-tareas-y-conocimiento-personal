from collections.abc import Generator

import pytest
from sqlalchemy.orm import Session

from gestor_tareas.infraestructura.persistencia.sesion import FabricaSesiones
from tests.integracion.tablas import vaciar_tablas


@pytest.fixture
def sesion_bd() -> Generator[Session, None, None]:
    """Sesión de base de datos real, con las tablas relevantes vacías al empezar."""
    sesion = FabricaSesiones()
    vaciar_tablas(sesion)
    try:
        yield sesion
    finally:
        sesion.close()
