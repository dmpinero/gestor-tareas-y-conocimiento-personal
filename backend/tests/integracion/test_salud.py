from fastapi.testclient import TestClient

from gestor_tareas.main import crear_aplicacion


def test_el_endpoint_de_salud_responde_ok() -> None:
    cliente = TestClient(crear_aplicacion())

    respuesta = cliente.get("/api/v1/salud")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"estado": "ok"}
