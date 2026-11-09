from fastapi.testclient import TestClient

from gestor_tareas.main import crear_aplicacion

cliente = TestClient(crear_aplicacion())


def test_la_api_expone_salud_y_tareas_bajo_api_v1() -> None:
    rutas = set(cliente.get("/openapi.json").json()["paths"])

    assert rutas == {"/api/v1/salud", "/api/v1/tareas"}


def test_ninguna_ruta_exige_autenticacion() -> None:
    esquema = cliente.get("/openapi.json").json()

    assert "securitySchemes" not in esquema.get("components", {})
    for operaciones in esquema["paths"].values():
        for operacion in operaciones.values():
            assert "security" not in operacion


def test_las_metricas_de_prometheus_se_exponen_fuera_del_esquema() -> None:
    respuesta = cliente.get("/metricas")

    assert respuesta.status_code == 200
    assert "http_request" in respuesta.text or "python_info" in respuesta.text


def test_el_titulo_de_la_api_corresponde_al_proyecto() -> None:
    assert cliente.get("/openapi.json").json()["info"]["title"] == (
        "Gestor de Tareas y Conocimiento Personal"
    )
