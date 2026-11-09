from fastapi.testclient import TestClient

from gestor_tareas.main import crear_aplicacion

cliente = TestClient(crear_aplicacion())


def test_una_respuesta_json_de_la_api_incluye_content_security_policy_estricto() -> None:
    respuesta = cliente.get("/api/v1/salud")

    assert (
        respuesta.headers["content-security-policy"] == "default-src 'none'; frame-ancestors 'none'"
    )


def test_la_documentacion_interactiva_no_incluye_content_security_policy() -> None:
    respuesta = cliente.get("/docs")

    assert "content-security-policy" not in respuesta.headers


def test_el_esquema_openapi_no_incluye_content_security_policy() -> None:
    respuesta = cliente.get("/openapi.json")

    assert "content-security-policy" not in respuesta.headers


def test_la_documentacion_interactiva_conserva_el_resto_de_cabeceras_de_seguridad() -> None:
    respuesta = cliente.get("/docs")

    assert respuesta.headers["x-content-type-options"] == "nosniff"
    assert respuesta.headers["x-frame-options"] == "DENY"
