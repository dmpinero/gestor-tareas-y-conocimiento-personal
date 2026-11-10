from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("tarea.feature")

_DATOS_VALIDOS = {
    "nombre": "Tarea",
    "prioridad": 3,
    "descripcion": "Descripción",
    "fecha_creacion": "2026-11-09T10:30:00",
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
    ("fecha de creación", "ausente"): {"fecha_creacion": _AUSENTE},
    ("fecha de creación", "con zona horaria"): {"fecha_creacion": "2026-11-09T10:30:00+01:00"},
    ("fecha de creación", "en formato dd/mm/aaaa"): {"fecha_creacion": "09/11/2026 10:30:00"},
    ("fecha de vencimiento", "en formato dd/mm/aaaa"): {"fecha_vencimiento": "20/11/2026 18:00:00"},
    ("etiquetas", "con un nombre vacío"): {"etiquetas": ["casa", ""]},
    ("etiquetas", "con un nombre de 51 caracteres"): {"etiquetas": ["e" * 51]},
    ("asignados", "con un nombre solo de espacios"): {"asignados": ["\u00a0 "]},
    ("asignados", "con un nombre de 101 caracteres"): {"asignados": ["p" * 101]},
}

# Valores que la API devuelve cuando la petición no incluye los campos opcionales.
_OPCIONALES_POR_DEFECTO = {"fecha_vencimiento": None, "etiquetas": [], "asignados": []}


def _lista(texto: str) -> list[str]:
    """Convierte "a, b" en ["a", "b"]; el texto vacío es la lista vacía."""
    return texto.split(", ") if texto else []


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
        'descripción "{descripcion}" y fecha de creación "{fecha_creacion}"'
    ),
    target_fixture="peticion",
)
def crear_tarea_con_prioridad(
    cliente: TestClient, nombre: str, prioridad: int, descripcion: str, fecha_creacion: str
) -> dict:
    datos = {
        "nombre": nombre,
        "prioridad": prioridad,
        "descripcion": descripcion,
        "fecha_creacion": fecha_creacion,
    }
    return {"datos": datos, "respuesta": cliente.post("/api/v1/tareas", json=datos)}


@when(
    parsers.parse(
        'creo una tarea con nombre "{nombre}", descripción "{descripcion}" '
        'y fecha de creación "{fecha_creacion}" sin prioridad'
    ),
    target_fixture="peticion",
)
def crear_tarea_sin_prioridad(
    cliente: TestClient, nombre: str, descripcion: str, fecha_creacion: str
) -> dict:
    datos = {
        "nombre": nombre,
        "prioridad": None,
        "descripcion": descripcion,
        "fecha_creacion": fecha_creacion,
    }
    return {"datos": datos, "respuesta": cliente.post("/api/v1/tareas", json=datos)}


@when(
    parsers.re(
        r"intento crear una tarea con "
        r"(?P<campo>nombre|descripción|prioridad|fecha de creación|fecha de vencimiento"
        r"|etiquetas|asignados) "
        r"(?P<valor>.+)"
    ),
    target_fixture="respuesta",
)
def crear_tarea_invalida(cliente: TestClient, campo: str, valor: str):
    return cliente.post("/api/v1/tareas", json=_con_cambios(_DATOS_INVALIDOS[(campo, valor)]))


@when(
    parsers.parse(
        'edito la tarea "{actual}" con nombre "{nombre}", descripción "{descripcion}" '
        'y fecha de creación "{fecha_creacion}" sin prioridad'
    ),
    target_fixture="peticion",
)
def editar_tarea(
    cliente: TestClient, actual: str, nombre: str, descripcion: str, fecha_creacion: str
) -> dict:
    id_tarea = _id_de(cliente, actual)
    datos = {
        "nombre": nombre,
        "prioridad": None,
        "descripcion": descripcion,
        "fecha_creacion": fecha_creacion,
    }
    respuesta = cliente.put(f"/api/v1/tareas/{id_tarea}", json=datos)
    return {"id": id_tarea, "datos": datos, "respuesta": respuesta}


@when(parsers.parse("intento editar la tarea con id {id_tarea:d}"), target_fixture="respuesta")
def editar_tarea_inexistente(cliente: TestClient, id_tarea: int):
    return cliente.put(f"/api/v1/tareas/{id_tarea}", json=_DATOS_VALIDOS)


@when(
    parsers.parse('intento editar la tarea "{actual}" sin fecha de creación'),
    target_fixture="respuesta",
)
def editar_tarea_sin_fecha_creacion(cliente: TestClient, actual: str):
    datos = _con_cambios({"nombre": "No se guarda", "fecha_creacion": _AUSENTE})
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
    assert cuerpo == {"id": cuerpo["id"], **_OPCIONALES_POR_DEFECTO, **peticion["datos"]}


@then("la API responde que la tarea se ha actualizado con esos datos")
def la_tarea_se_ha_actualizado(peticion: dict) -> None:
    respuesta = peticion["respuesta"]
    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "id": peticion["id"],
        **_OPCIONALES_POR_DEFECTO,
        **peticion["datos"],
    }


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


# Listas entre comillas que pueden estar vacías ("" es la lista vacía).
_ETIQUETAS = r'"(?P<etiquetas>[^"]*)"'
_ASIGNADOS = r'"(?P<asignados>[^"]*)"'


@given(
    parsers.re(f"que existe una tarea con etiquetas {_ETIQUETAS} y asignados {_ASIGNADOS}"),
    target_fixture="tarea_previa",
)
def existe_una_tarea_con_catalogos(cliente: TestClient, etiquetas: str, asignados: str) -> dict:
    datos = {**_DATOS_VALIDOS, "etiquetas": _lista(etiquetas), "asignados": _lista(asignados)}
    respuesta = cliente.post("/api/v1/tareas", json=datos)
    assert respuesta.status_code == 201
    return respuesta.json()


@when(
    parsers.re(f"creo una tarea con etiquetas {_ETIQUETAS} y asignados {_ASIGNADOS}"),
    target_fixture="peticion",
)
def crear_tarea_con_catalogos(cliente: TestClient, etiquetas: str, asignados: str) -> dict:
    datos = {**_DATOS_VALIDOS, "etiquetas": _lista(etiquetas), "asignados": _lista(asignados)}
    return {"datos": datos, "respuesta": cliente.post("/api/v1/tareas", json=datos)}


@when(
    parsers.re(f"edito esa tarea con etiquetas {_ETIQUETAS} y asignados {_ASIGNADOS}"),
    target_fixture="peticion",
)
def editar_tarea_con_catalogos(
    cliente: TestClient, tarea_previa: dict, etiquetas: str, asignados: str
) -> dict:
    datos = {**_DATOS_VALIDOS, "etiquetas": _lista(etiquetas), "asignados": _lista(asignados)}
    respuesta = cliente.put(f"/api/v1/tareas/{tarea_previa['id']}", json=datos)
    return {"id": tarea_previa["id"], "datos": datos, "respuesta": respuesta}


@when(
    parsers.parse(
        'creo una tarea con fecha de creación "{fecha_creacion}" '
        'y fecha de vencimiento "{fecha_vencimiento}"'
    ),
    target_fixture="peticion",
)
def crear_tarea_con_vencimiento(
    cliente: TestClient, fecha_creacion: str, fecha_vencimiento: str
) -> dict:
    datos = {
        **_DATOS_VALIDOS,
        "fecha_creacion": fecha_creacion,
        "fecha_vencimiento": fecha_vencimiento,
    }
    respuesta = cliente.post("/api/v1/tareas", json=datos)
    return {"datos": datos, "respuesta": respuesta}


def _comprobar_catalogos(cuerpo: dict, etiquetas: str, asignados: str) -> None:
    assert cuerpo["etiquetas"] == _lista(etiquetas)
    assert cuerpo["asignados"] == _lista(asignados)


@then(
    parsers.re(
        f"la API responde que la tarea se ha creado con etiquetas {_ETIQUETAS} "
        f"y asignados {_ASIGNADOS}"
    )
)
def la_tarea_se_ha_creado_con_catalogos(peticion: dict, etiquetas: str, asignados: str) -> None:
    respuesta = peticion["respuesta"]
    assert respuesta.status_code == 201
    _comprobar_catalogos(respuesta.json(), etiquetas, asignados)


@then(
    parsers.re(
        f"la API responde que la tarea se ha actualizado con etiquetas {_ETIQUETAS} "
        f"y asignados {_ASIGNADOS}"
    )
)
def la_tarea_se_ha_actualizado_con_catalogos(
    peticion: dict, etiquetas: str, asignados: str
) -> None:
    respuesta = peticion["respuesta"]
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["id"] == peticion["id"]
    _comprobar_catalogos(cuerpo, etiquetas, asignados)


@then(
    parsers.re(
        f"el listado muestra solo esa tarea con etiquetas {_ETIQUETAS} y asignados {_ASIGNADOS}"
    )
)
def el_listado_muestra_la_tarea_con_catalogos(
    cliente: TestClient, peticion: dict, etiquetas: str, asignados: str
) -> None:
    [tarea] = cliente.get("/api/v1/tareas").json()
    assert tarea == peticion["respuesta"].json()
    _comprobar_catalogos(tarea, etiquetas, asignados)


@then(parsers.re(r'el catálogo de (?P<catalogo>etiquetas|personas) contiene "(?P<nombres>[^"]*)"'))
def el_catalogo_contiene(cliente: TestClient, catalogo: str, nombres: str) -> None:
    respuesta = cliente.get(f"/api/v1/{catalogo}")
    assert respuesta.status_code == 200
    elementos = respuesta.json()
    assert [e["nombre"] for e in elementos] == _lista(nombres)
    assert all(isinstance(e["id"], int) and set(e) == {"id", "nombre"} for e in elementos)


@then(parsers.parse('la API rechaza la operación con el mensaje "{mensaje}"'))
def la_api_rechaza_con_mensaje(peticion: dict, mensaje: str) -> None:
    respuesta = peticion["respuesta"]
    assert respuesta.status_code == 422
    assert mensaje in respuesta.text
