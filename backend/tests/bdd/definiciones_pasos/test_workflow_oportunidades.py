from fastapi.testclient import TestClient
from httpx import Response
from pytest_bdd import given, parsers, scenarios, then, when
from sqlalchemy import select

from gestor_tareas.infraestructura.persistencia.modelos import PasoWorkflowOportunidadModelo
from gestor_tareas.infraestructura.persistencia.sesion import FabricaSesiones

scenarios("workflow_oportunidades.feature")

_RUTA = "/api/v1/workflow-oportunidades/pasos"
_ID_INEXISTENTE = 999999

_NOMBRES_INVALIDOS = {
    "vacío": {"nombre": ""},
    "solo de espacios": {"nombre": "   "},
    "con espacio duro": {"nombre": "  "},
    "de 51 caracteres": {"nombre": "n" * 51},
    "ausente": {},
    "que no es texto": {"nombre": 5},
}


def _lista(texto: str) -> list[str]:
    """Convierte "a, b" en ["a", "b"]; el texto vacío es la lista vacía."""
    return texto.split(", ") if texto else []


def _pasos(cliente: TestClient) -> list[dict]:
    respuesta = cliente.get(_RUTA)
    assert respuesta.status_code == 200
    return respuesta.json()


def _id_de(cliente: TestClient, nombre: str) -> int:
    return next(p["id"] for p in _pasos(cliente) if p["nombre"] == nombre)


def _filas_guardadas() -> list[tuple[int, str]]:
    """(numero, nombre) de las filas de la base de datos, en orden de número."""
    sesion = FabricaSesiones()
    try:
        modelo = PasoWorkflowOportunidadModelo
        consulta = select(modelo.numero, modelo.nombre).order_by(modelo.numero)
        return [(fila.numero, fila.nombre) for fila in sesion.execute(consulta)]
    finally:
        sesion.close()


def _comprobar_pasos(pasos: list[dict], nombres: list[str]) -> None:
    assert [(p["numero"], p["nombre"]) for p in pasos] == list(enumerate(nombres, start=1))
    assert all(set(p) == {"id", "numero", "nombre"} for p in pasos)
    assert len({p["id"] for p in pasos}) == len(pasos)


@given("que el workflow no tiene pasos")
def workflow_sin_pasos(cliente: TestClient) -> None:
    assert _pasos(cliente) == []


@given(parsers.parse('que el workflow tiene los pasos "{nombres}"'))
def workflow_con_pasos(cliente: TestClient, nombres: str) -> None:
    for nombre in _lista(nombres):
        assert cliente.post(_RUTA, json={"nombre": nombre}).status_code == 201


@when("consulto los pasos del workflow", target_fixture="respuesta")
def consultar_pasos(cliente: TestClient) -> Response:
    return cliente.get(_RUTA)


@when(parsers.parse('añado el paso "{nombre}"'), target_fixture="respuesta")
def anadir_paso(cliente: TestClient, nombre: str) -> Response:
    return cliente.post(_RUTA, json={"nombre": nombre})


@when("añado un paso con un nombre de 50 caracteres", target_fixture="respuesta")
def anadir_paso_de_50(cliente: TestClient) -> Response:
    return cliente.post(_RUTA, json={"nombre": "n" * 50})


@when(parsers.parse("intento añadir un paso con un nombre {nombre}"), target_fixture="respuesta")
def anadir_paso_invalido(cliente: TestClient, nombre: str) -> Response:
    return cliente.post(_RUTA, json=_NOMBRES_INVALIDOS[nombre])


@when(parsers.parse('renombro el paso "{actual}" a "{nuevo}"'), target_fixture="respuesta")
def renombrar_paso(cliente: TestClient, actual: str, nuevo: str) -> Response:
    return cliente.put(f"{_RUTA}/{_id_de(cliente, actual)}", json={"nombre": nuevo})


@when(
    parsers.parse('intento renombrar el paso "{actual}" con un nombre {nombre}'),
    target_fixture="respuesta",
)
def renombrar_paso_invalido(cliente: TestClient, actual: str, nombre: str) -> Response:
    return cliente.put(f"{_RUTA}/{_id_de(cliente, actual)}", json=_NOMBRES_INVALIDOS[nombre])


@when(parsers.parse('elimino el paso "{nombre}"'), target_fixture="respuesta")
def eliminar_paso(cliente: TestClient, nombre: str) -> Response:
    return cliente.delete(f"{_RUTA}/{_id_de(cliente, nombre)}")


@when(parsers.parse('reordeno los pasos como "{nombres}"'), target_fixture="respuesta")
def reordenar_pasos(cliente: TestClient, nombres: str) -> Response:
    ids = [_id_de(cliente, nombre) for nombre in _lista(nombres)]
    return cliente.put(f"{_RUTA}/orden", json={"ids": ids})


@when(parsers.parse("intento reordenar los pasos con un orden {orden}"), target_fixture="respuesta")
def reordenar_pasos_invalido(cliente: TestClient, orden: str) -> Response:
    ids = [p["id"] for p in _pasos(cliente)]
    cuerpos = {
        "con un paso repetido": {"ids": [*ids, ids[0]]},
        "al que le falta un paso": {"ids": ids[1:]},
        "con un paso que no existe": {"ids": [*ids, max(ids) + 1]},
        "vacío": {"ids": []},
        "con ids que no son enteros": {"ids": [str(i) for i in ids]},
        "ausente": {},
    }
    return cliente.put(f"{_RUTA}/orden", json=cuerpos[orden])


@when(
    parsers.parse("intento {operacion} el paso con un id que no existe"),
    target_fixture="respuesta",
)
def operar_paso_inexistente(cliente: TestClient, operacion: str) -> Response:
    ruta = f"{_RUTA}/{_ID_INEXISTENTE}"
    if operacion == "renombrar":
        return cliente.put(ruta, json={"nombre": "Otro"})
    return cliente.delete(ruta)


@then("la API devuelve una lista de pasos vacía")
def la_api_devuelve_una_lista_vacia(respuesta: Response) -> None:
    assert respuesta.status_code == 200
    assert respuesta.json() == []


@then(parsers.parse('la API devuelve los pasos "{nombres}"'))
def la_api_devuelve_los_pasos(respuesta: Response, nombres: str) -> None:
    assert respuesta.status_code == 200
    _comprobar_pasos(respuesta.json(), _lista(nombres))


@then(parsers.parse('la API responde que el paso "{nombre}" se ha creado con el número {numero:d}'))
def el_paso_se_ha_creado(respuesta: Response, nombre: str, numero: int) -> None:
    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert set(cuerpo) == {"id", "numero", "nombre"}
    assert (cuerpo["numero"], cuerpo["nombre"]) == (numero, nombre)
    assert isinstance(cuerpo["id"], int)


@then(
    parsers.parse("la API responde que el paso se ha creado con ese nombre y el número {numero:d}")
)
def el_paso_de_50_se_ha_creado(respuesta: Response, numero: int) -> None:
    el_paso_se_ha_creado(respuesta, "n" * 50, numero)
    assert _filas_guardadas() == [(numero, "n" * 50)]


@then(parsers.parse('la API responde con el paso "{nombre}" y el número {numero:d}'))
def la_api_responde_con_el_paso(respuesta: Response, nombre: str, numero: int) -> None:
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert set(cuerpo) == {"id", "numero", "nombre"}
    assert (cuerpo["numero"], cuerpo["nombre"]) == (numero, nombre)


@then("la API responde que el paso se ha eliminado")
def el_paso_se_ha_eliminado(respuesta: Response) -> None:
    assert respuesta.status_code == 204
    assert respuesta.content == b""


@then("la API rechaza la operación por datos inválidos")
def la_api_rechaza_por_datos_invalidos(respuesta: Response) -> None:
    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]


@then("la API responde que el paso no existe")
def la_api_responde_que_el_paso_no_existe(respuesta: Response) -> None:
    # El cuerpo distingue el 404 de dominio del 404 de "ruta no encontrada".
    assert respuesta.status_code == 404
    assert respuesta.json() == {
        "detalle": f"No existe el paso del workflow con id {_ID_INEXISTENTE}"
    }


@then(parsers.parse('el workflow guarda los pasos "{nombres}"'))
def el_workflow_guarda_los_pasos(cliente: TestClient, nombres: str) -> None:
    esperados = _lista(nombres)
    assert _filas_guardadas() == list(enumerate(esperados, start=1))
    _comprobar_pasos(_pasos(cliente), esperados)
