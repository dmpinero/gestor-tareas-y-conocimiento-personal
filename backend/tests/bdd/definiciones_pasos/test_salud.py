from fastapi.testclient import TestClient
from pytest_bdd import given, scenarios, then, when
from pytest_bdd.parsers import parse

from gestor_tareas.main import crear_aplicacion

scenarios("salud.feature")


@given("que el servicio está en marcha", target_fixture="cliente_api")
def cliente_api() -> TestClient:
    return TestClient(crear_aplicacion())


@when("consulto el endpoint de salud", target_fixture="respuesta")
def consultar_endpoint_de_salud(cliente_api: TestClient):
    return cliente_api.get("/api/v1/salud")


@then(parse("la respuesta indica que el estado es correcto"))
def la_respuesta_indica_estado_correcto(respuesta) -> None:
    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "ok"
