"""API del catálogo de códigos de servicio (p. ej. «AXAS0024»): como el de
subestados, con alta, cambio de nombre y borrado. El nombre se recorta, tiene de 2 a
20 caracteres, no tiene espacios y es único sin distinguir mayúsculas."""

import pytest
from fastapi.testclient import TestClient

from gestor_tareas.infraestructura.persistencia.sesion import FabricaSesiones
from gestor_tareas.main import crear_aplicacion
from tests.integracion.tablas import vaciar_tablas

_CODIGOS = "/api/v1/codigos-servicio"


@pytest.fixture
def cliente() -> TestClient:
    sesion = FabricaSesiones()
    try:
        vaciar_tablas(sesion)
    finally:
        sesion.close()
    return TestClient(crear_aplicacion())


def _nombres(cliente: TestClient) -> list[str]:
    respuesta = cliente.get(_CODIGOS)
    assert respuesta.status_code == 200
    return [c["nombre"] for c in respuesta.json()]


def _crear(cliente: TestClient, nombre: str) -> dict:
    respuesta = cliente.post(_CODIGOS, json={"nombre": nombre})
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _mensaje_422(respuesta) -> str:
    assert respuesta.status_code == 422
    (error,) = respuesta.json()["detail"]
    return error["msg"]


def test_el_catalogo_empieza_vacio(cliente: TestClient) -> None:
    assert cliente.get(_CODIGOS).json() == []


def test_alta_recorta_el_nombre_y_lista_por_nombre(cliente: TestClient) -> None:
    creado = _crear(cliente, "  AXAS0025 ")
    _crear(cliente, "axas0024")

    assert set(creado) == {"id", "nombre"}
    assert creado["nombre"] == "AXAS0025"
    assert cliente.get(_CODIGOS).json()[1] == creado
    assert _nombres(cliente) == ["axas0024", "AXAS0025"]


@pytest.mark.parametrize("nombre", ["AXAS0024", "axas0024", " Axas0024 "])
def test_alta_de_un_nombre_repetido_sin_distinguir_mayusculas_responde_409(
    cliente: TestClient, nombre: str
) -> None:
    _crear(cliente, "AXAS0024")

    respuesta = cliente.post(_CODIGOS, json={"nombre": nombre})

    assert respuesta.status_code == 409
    assert respuesta.json() == {
        "detalle": f"Ya existe un código de servicio llamado «{nombre.strip()}»"
    }
    assert _nombres(cliente) == ["AXAS0024"]


@pytest.mark.parametrize(
    ("nombre", "mensaje"),
    [
        ("", "El código de servicio debe tener al menos 2 caracteres."),
        ("   ", "El código de servicio debe tener al menos 2 caracteres."),
        (" A ", "El código de servicio debe tener al menos 2 caracteres."),
        ("A" * 21, "El código de servicio no puede superar los 20 caracteres."),
        ("AX AS", "El código de servicio no puede contener espacios."),
        ("AX AS", "El código de servicio no puede contener espacios."),
    ],
)
def test_alta_con_un_nombre_invalido_responde_422_con_el_motivo(
    cliente: TestClient, nombre: str, mensaje: str
) -> None:
    respuesta = cliente.post(_CODIGOS, json={"nombre": nombre})

    assert _mensaje_422(respuesta) == f"Value error, {mensaje}"
    assert _nombres(cliente) == []


@pytest.mark.parametrize("cuerpo", [{}, {"nombre": 5}, {"nombre": None}])
def test_alta_con_un_cuerpo_invalido_responde_422(cliente: TestClient, cuerpo: dict) -> None:
    assert cliente.post(_CODIGOS, json=cuerpo).status_code == 422
    assert _nombres(cliente) == []


@pytest.mark.parametrize("nombre", ["24", "A" * 20])
def test_admite_los_nombres_de_2_y_de_20_caracteres(cliente: TestClient, nombre: str) -> None:
    assert _crear(cliente, nombre)["nombre"] == nombre
    assert _nombres(cliente) == [nombre]


def test_cambiar_el_nombre_lo_recorta_y_lo_guarda(cliente: TestClient) -> None:
    codigo = _crear(cliente, "AXAS0024")

    respuesta = cliente.put(f"{_CODIGOS}/{codigo['id']}", json={"nombre": " AXAS0026 "})

    assert respuesta.status_code == 200
    assert respuesta.json() == {"id": codigo["id"], "nombre": "AXAS0026"}
    assert cliente.get(_CODIGOS).json() == [{"id": codigo["id"], "nombre": "AXAS0026"}]


def test_cambiar_el_nombre_a_su_misma_grafia_en_mayusculas_se_admite(cliente: TestClient) -> None:
    codigo = _crear(cliente, "axas0024")

    respuesta = cliente.put(f"{_CODIGOS}/{codigo['id']}", json={"nombre": "AXAS0024"})

    assert respuesta.status_code == 200
    assert _nombres(cliente) == ["AXAS0024"]


def test_cambiar_el_nombre_al_de_otro_codigo_responde_409(cliente: TestClient) -> None:
    _crear(cliente, "AXAS0024")
    otro = _crear(cliente, "AXAS0025")

    respuesta = cliente.put(f"{_CODIGOS}/{otro['id']}", json={"nombre": "axas0024"})

    assert respuesta.status_code == 409
    assert respuesta.json() == {"detalle": "Ya existe un código de servicio llamado «axas0024»"}
    assert _nombres(cliente) == ["AXAS0024", "AXAS0025"]


def test_cambiar_el_nombre_a_uno_invalido_responde_422_sin_cambiarlo(cliente: TestClient) -> None:
    codigo = _crear(cliente, "AXAS0024")

    respuesta = cliente.put(f"{_CODIGOS}/{codigo['id']}", json={"nombre": "AX AS"})

    assert (
        _mensaje_422(respuesta) == "Value error, El código de servicio no puede contener espacios."
    )
    assert _nombres(cliente) == ["AXAS0024"]


def test_cambiar_el_nombre_de_un_codigo_que_no_existe_responde_404(cliente: TestClient) -> None:
    respuesta = cliente.put(f"{_CODIGOS}/999999", json={"nombre": "AXAS0024"})

    assert respuesta.status_code == 404
    assert respuesta.json() == {"detalle": "No existe el código de servicio con id 999999"}
    assert _nombres(cliente) == []


def test_eliminar_un_codigo_lo_quita_del_catalogo(cliente: TestClient) -> None:
    codigo = _crear(cliente, "AXAS0024")
    _crear(cliente, "AXAS0025")

    respuesta = cliente.delete(f"{_CODIGOS}/{codigo['id']}")

    assert respuesta.status_code == 204
    assert respuesta.content == b""
    assert _nombres(cliente) == ["AXAS0025"]


def test_eliminar_un_codigo_que_no_existe_responde_404(cliente: TestClient) -> None:
    _crear(cliente, "AXAS0024")

    respuesta = cliente.delete(f"{_CODIGOS}/999999")

    assert respuesta.status_code == 404
    assert respuesta.json() == {"detalle": "No existe el código de servicio con id 999999"}
    assert _nombres(cliente) == ["AXAS0024"]


def test_el_contrato_publica_los_limites_del_nombre(cliente: TestClient) -> None:
    esquemas = cliente.get("/openapi.json").json()["components"]["schemas"]

    nombre = esquemas["CodigoServicioEsquema"]["properties"]["nombre"]
    # Los límites van en el `pattern`, que admite los espacios de los extremos
    # porque la API los recorta antes de validar.
    assert nombre["pattern"] == r"^\s*\S{2,20}\s*$"
    assert "minLength" not in nombre
    assert "maxLength" not in nombre
