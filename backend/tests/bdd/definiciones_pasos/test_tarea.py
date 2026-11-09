from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("tarea.feature")

_DATOS_VALIDOS = {
    "nombre": "Tarea",
    "prioridad": 3,
    "descripcion": "Descripción",
    "fecha_hora": "2026-11-09T10:30:00",
}

_AUSENTE = object()

_DATOS_INVALIDOS = {
    ("nombre", "vacío"): {"nombre": ""},
    ("nombre", "solo espacios"): {"nombre": "   "},
    ("nombre", "de 201 caracteres"): {"nombre": "n" * 201},
    ("descripción", "vacía"): {"descripcion": ""},
    ("descripción", "de 501 caracteres"): {"descripcion": "d" * 501},
    ("prioridad", "0"): {"prioridad": 0},
    ("prioridad", "6"): {"prioridad": 6},
    ("fecha y hora", "ausente"): {"fecha_hora": _AUSENTE},
    ("fecha y hora", "con zona horaria"): {"fecha_hora": "2026-11-09T10:30:00+01:00"},
    ("fecha y hora", "en formato dd/mm/aaaa"): {"fecha_hora": "09/11/2026 10:30:00"},
}


def _con_cambios(cambios: dict) -> dict:
    datos = {**_DATOS_VALIDOS, **cambios}
    return {clave: valor for clave, valor in datos.items() if valor is not _AUSENTE}


def _id_de(cliente: TestClient, nombre: str) -> int:
    return next(t["id"] for t in cliente.get("/api/v1/tareas").json() if t["nombre"] == nombre)


@given("que no existe ninguna tarea")
def no_existe_ninguna_tarea(cliente: TestClient) -> None:
    assert cliente.get("/api/v1/tareas").json() == []


@given(
    parsers.parse('que existen las tareas "{primera}" y "{segunda}"'),
    target_fixture="tareas_previas",
)
def existen_las_tareas(cliente: TestClient, primera: str, segunda: str) -> list[dict]:
    creadas = []
    for nombre in (primera, segunda):
        respuesta = cliente.post("/api/v1/tareas", json={**_DATOS_VALIDOS, "nombre": nombre})
        assert respuesta.status_code == 201
        creadas.append(respuesta.json())
    return creadas


@when(
    parsers.parse(
        'creo una tarea con nombre "{nombre}", prioridad {prioridad:d}, '
        'descripción "{descripcion}" y fecha y hora "{fecha_hora}"'
    ),
    target_fixture="peticion",
)
def crear_tarea_con_prioridad(
    cliente: TestClient, nombre: str, prioridad: int, descripcion: str, fecha_hora: str
) -> dict:
    datos = {
        "nombre": nombre,
        "prioridad": prioridad,
        "descripcion": descripcion,
        "fecha_hora": fecha_hora,
    }
    return {"datos": datos, "respuesta": cliente.post("/api/v1/tareas", json=datos)}


@when(
    parsers.parse(
        'creo una tarea con nombre "{nombre}", descripción "{descripcion}" '
        'y fecha y hora "{fecha_hora}" sin prioridad'
    ),
    target_fixture="peticion",
)
def crear_tarea_sin_prioridad(
    cliente: TestClient, nombre: str, descripcion: str, fecha_hora: str
) -> dict:
    datos = {
        "nombre": nombre,
        "prioridad": None,
        "descripcion": descripcion,
        "fecha_hora": fecha_hora,
    }
    return {"datos": datos, "respuesta": cliente.post("/api/v1/tareas", json=datos)}


@when(
    parsers.re(
        r"intento crear una tarea con (?P<campo>nombre|descripción|prioridad|fecha y hora) "
        r"(?P<valor>.+)"
    ),
    target_fixture="respuesta",
)
def crear_tarea_invalida(cliente: TestClient, campo: str, valor: str):
    return cliente.post("/api/v1/tareas", json=_con_cambios(_DATOS_INVALIDOS[(campo, valor)]))


@when(
    parsers.parse(
        'edito la tarea "{actual}" con nombre "{nombre}", descripción "{descripcion}" '
        'y fecha y hora "{fecha_hora}" sin prioridad'
    ),
    target_fixture="peticion",
)
def editar_tarea(
    cliente: TestClient, actual: str, nombre: str, descripcion: str, fecha_hora: str
) -> dict:
    id_tarea = _id_de(cliente, actual)
    datos = {
        "nombre": nombre,
        "prioridad": None,
        "descripcion": descripcion,
        "fecha_hora": fecha_hora,
    }
    respuesta = cliente.put(f"/api/v1/tareas/{id_tarea}", json=datos)
    return {"id": id_tarea, "datos": datos, "respuesta": respuesta}


@when(parsers.parse("intento editar la tarea con id {id_tarea:d}"), target_fixture="respuesta")
def editar_tarea_inexistente(cliente: TestClient, id_tarea: int):
    return cliente.put(f"/api/v1/tareas/{id_tarea}", json=_DATOS_VALIDOS)


@when(
    parsers.parse('intento editar la tarea "{actual}" sin fecha y hora'),
    target_fixture="respuesta",
)
def editar_tarea_sin_fecha_hora(cliente: TestClient, actual: str):
    datos = _con_cambios({"nombre": "No se guarda", "fecha_hora": _AUSENTE})
    return cliente.put(f"/api/v1/tareas/{_id_de(cliente, actual)}", json=datos)


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


@then("la API responde que la tarea se ha actualizado con esos datos")
def la_tarea_se_ha_actualizado(peticion: dict) -> None:
    respuesta = peticion["respuesta"]
    assert respuesta.status_code == 200
    assert respuesta.json() == {"id": peticion["id"], **peticion["datos"]}


@then("la tarea aparece en el listado de tareas")
def la_tarea_aparece_en_el_listado(cliente: TestClient, peticion: dict) -> None:
    respuesta = cliente.get("/api/v1/tareas")
    assert respuesta.status_code == 200
    assert respuesta.json() == [peticion["respuesta"].json()]


@then(parsers.parse('el listado muestra la tarea editada y "{segunda}" sin cambios'))
def el_listado_muestra_la_tarea_editada(
    cliente: TestClient, peticion: dict, tareas_previas: list[dict], segunda: str
) -> None:
    respuesta = cliente.get("/api/v1/tareas")
    assert respuesta.status_code == 200
    assert tareas_previas[1]["nombre"] == segunda
    assert respuesta.json() == [peticion["respuesta"].json(), tareas_previas[1]]


@then(parsers.parse('el listado contiene "{primera}" y "{segunda}" en ese orden'))
def el_listado_contiene_en_orden(respuesta, primera: str, segunda: str) -> None:
    assert respuesta.status_code == 200
    tareas = respuesta.json()
    assert [t["nombre"] for t in tareas] == [primera, segunda]
    assert tareas[0]["id"] < tareas[1]["id"]


@then(parsers.parse('el listado contiene "{primera}" y "{segunda}" sin cambios'))
def el_listado_sin_cambios(
    cliente: TestClient, tareas_previas: list[dict], primera: str, segunda: str
) -> None:
    assert [t["nombre"] for t in tareas_previas] == [primera, segunda]
    assert cliente.get("/api/v1/tareas").json() == tareas_previas


@then("la API rechaza la operación por datos inválidos")
def la_api_rechaza_por_datos_invalidos(respuesta) -> None:
    assert respuesta.status_code == 422


@then("la API responde que la tarea no existe")
def la_api_responde_no_existe(respuesta) -> None:
    # El cuerpo distingue el 404 de dominio del 404 de "ruta no encontrada".
    assert respuesta.status_code == 404
    assert respuesta.json() == {"detalle": "No existe la tarea con id 999999"}


@then("el listado de tareas sigue vacío")
def el_listado_sigue_vacio(cliente: TestClient) -> None:
    assert cliente.get("/api/v1/tareas").json() == []
