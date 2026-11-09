from collections.abc import Generator

import pytest
from sqlalchemy.orm import Session

from gestor_tareas.infraestructura.persistencia import modelos  # noqa: F401
from gestor_tareas.infraestructura.persistencia.sesion import FabricaSesiones


@pytest.fixture
def sesion_bd() -> Generator[Session, None, None]:
    """Sesión de base de datos real.

    Cuando existan modelos, vacía aquí sus tablas antes de cada test (en orden
    inverso a sus claves foráneas), como hace el proyecto de referencia.
    """
    sesion = FabricaSesiones()
    try:
        yield sesion
    finally:
        sesion.close()
