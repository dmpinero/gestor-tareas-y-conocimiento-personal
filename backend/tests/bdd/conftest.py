import pytest
from fastapi.testclient import TestClient

from gestor_tareas.infraestructura.persistencia import modelos
from gestor_tareas.infraestructura.persistencia.sesion import FabricaSesiones
from gestor_tareas.main import crear_aplicacion


@pytest.fixture
def cliente() -> TestClient:
    """Cliente HTTP contra la aplicación real, con las tablas relevantes vacías."""
    sesion = FabricaSesiones()
    sesion.execute(modelos.TareaModelo.__table__.delete())
    sesion.commit()
    sesion.close()

    return TestClient(crear_aplicacion())
