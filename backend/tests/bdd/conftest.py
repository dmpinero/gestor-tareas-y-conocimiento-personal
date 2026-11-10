import pytest
from fastapi.testclient import TestClient

from gestor_tareas.infraestructura.persistencia.sesion import FabricaSesiones
from gestor_tareas.main import crear_aplicacion
from tests.integracion.tablas import vaciar_tablas


@pytest.fixture
def cliente() -> TestClient:
    """Cliente HTTP contra la aplicación real, con las tablas relevantes vacías."""
    sesion = FabricaSesiones()
    vaciar_tablas(sesion)
    sesion.close()

    return TestClient(crear_aplicacion())
