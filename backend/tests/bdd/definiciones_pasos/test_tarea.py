from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("tarea.feature")

_DATOS_VALIDOS = {"nombre": "Tarea", "prioridad": 3, "descripcion": "Descripción"}

_DATOS_INVALIDOS = {
    ("nombre", "vacío"): {"nombre": ""},
    ("nombre", "solo espacios"): {"nombre": "   "},
    ("nombre", "de 201 caracteres"): {"nombre": "n" * 201},
    ("descripción", "vacía"): {"descripcion": ""},
    ("descripción", "de 501 caracteres"): {"descripcion": "d" * 501},
    ("prioridad", "0"): {"prioridad": 0},
    ("prioridad", "6"): {"prioridad": 6},
}


@given("que no existe ninguna tarea")
def no_existe_ninguna_tarea(cliente: TestClient) -> None:
    assert cliente.get("/api/v1/tareas").json() == []


@given(parsers.parse('que existen las tareas "{primera}" y "{segunda}"'))
def existen_las_tareas(cliente: TestClient, primera: str, segunda: str) -> None:
    for nombre in (primera, segunda):
        respuesta = cliente.post("/api/v1/tareas", json={**_DATOS_VALIDOS, "nombre": nombre})
        assert respuesta.status_code == 201


@when(
    parsers.parse(
        'creo una tarea con nombre "{nombre}", prioridad {prioridad:d} '
        'y descripción "{descripcion}"'
    ),
    target_fixture="peticion",
)
def crear_tarea_con_prioridad(
    cliente: TestClient, nombre: str, prioridad: int, descripcion: str
) -> dict:
    datos = {"nombre": nombre, "prioridad": prioridad, "descripcion": descripcion}
    return {"datos": datos, "respuesta": cliente.post("/api/v1/tareas", json=datos)}


@when(
    parsers.parse(
        'creo una tarea con nombre "{nombre}" y descripción "{descripcion}" sin prioridad'
    ),
    target_fixture="peticion",
)
def crear_tarea_sin_prioridad(cliente: TestClient, nombre: str, descripcion: str) -> dict:
    datos = {"nombre": nombre, "prioridad": None, "descripcion": descripcion}
    return {"datos": datos, "respuesta": cliente.post("/api/v1/tareas", json=datos)}


@when(parsers.parse("intento crear una tarea con {campo} {valor}"), target_fixture="respuesta")
def crear_tarea_invalida(cliente: TestClient, campo: str, valor: str):
    datos = {**_DATOS_VALIDOS, **_DATOS_INVALIDOS[(campo, valor)]}
    return cliente.post("/api/v1/tareas", json=datos)


@when("consulto el listado de tareas", target_fixture="respuesta")
def consultar_listado(cliente: TestClient):
    return cliente.get("/api/v1/tareas")


@then("la API responde que la tarea se ha creado con esos datos")
def la_tarea_se_ha_creado(peticion: dict) -> None:
    respuesta = peticion["respuesta"]
    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert isinstance(cuerpo["id"], int)
    assert cuerpo == {"id": cuerpo["id"], **peticion["datos"]}


@then("la tarea aparece en el listado de tareas")
def la_tarea_aparece_en_el_listado(cliente: TestClient, peticion: dict) -> None:
    respuesta = cliente.get("/api/v1/tareas")
    assert respuesta.status_code == 200
    assert respuesta.json() == [peticion["respuesta"].json()]


@then(parsers.parse('el listado contiene "{primera}" y "{segunda}" en ese orden'))
def el_listado_contiene_en_orden(respuesta, primera: str, segunda: str) -> None:
    assert respuesta.status_code == 200
    tareas = respuesta.json()
    assert [t["nombre"] for t in tareas] == [primera, segunda]
    assert tareas[0]["id"] < tareas[1]["id"]


@then("la API rechaza la operación por datos inválidos")
def la_api_rechaza_por_datos_invalidos(respuesta) -> None:
    assert respuesta.status_code == 422


@then("el listado de tareas sigue vacío")
def el_listado_sigue_vacio(cliente: TestClient) -> None:
    assert cliente.get("/api/v1/tareas").json() == []
