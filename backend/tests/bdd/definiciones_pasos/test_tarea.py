import json

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


def _con_oportunidad(**campos) -> dict:
    """Cambios para una tarea de tipo oportunidad con los campos indicados."""
    oportunidad = {"codigo": "OP-1", "descripcion": None, "observaciones": None, **campos}
    return {"tipo": "oportunidad", "oportunidad": oportunidad}


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
    ("tipo", "desconocido"): {"tipo": "otro", "oportunidad": None},
    ("código de la oportunidad", "vacío"): _con_oportunidad(codigo=""),
    ("código de la oportunidad", "solo espacios"): _con_oportunidad(codigo="\u00a0 "),
    ("código de la oportunidad", "de 11 caracteres"): _con_oportunidad(codigo="c" * 11),
    ("descripción de la oportunidad", "de 201 caracteres"): _con_oportunidad(descripcion="d" * 201),
    ("observaciones de la oportunidad", "de 5001 caracteres"): _con_oportunidad(
        observaciones="o" * 5001
    ),
}

# Valores que la API devuelve cuando la petición no incluye los campos opcionales.
_OPCIONALES_POR_DEFECTO = {
    "fecha_vencimiento": None,
    "etiquetas": [],
    "asignados": [],
    "tipo": None,
    "oportunidad": None,
    "completada": False,
    "pasos_oportunidad": [],
    "subtareas": [],
}


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
        # Las alternativas largas van antes: "descripción" también es el principio
        # de "descripción de la oportunidad".
        r"(?P<campo>código de la oportunidad|descripción de la oportunidad"
        r"|observaciones de la oportunidad|nombre|descripción|prioridad"
        r"|fecha de creación|fecha de vencimiento|etiquetas|asignados|tipo) "
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


def _texto_o_nulo(texto: str) -> str | None:
    """En los pasos, "" significa que la API devuelve ``null``."""
    return texto or None


_OPORTUNIDAD = (
    r'código "(?P<codigo>[^"]*)", descripción "(?P<descripcion>[^"]*)" '
    r'y observaciones "(?P<observaciones>[^"]*)"'
)


@then("ninguna tarea del listado tiene tipo ni oportunidad")
def ninguna_tarea_tiene_tipo(respuesta) -> None:
    assert respuesta.status_code == 200
    tareas = respuesta.json()
    assert tareas
    assert all(t["tipo"] is None and t["oportunidad"] is None for t in tareas)


@when(
    parsers.re(f"creo una tarea de tipo oportunidad con {_OPORTUNIDAD}"),
    target_fixture="peticion",
)
def crear_tarea_oportunidad(
    cliente: TestClient, codigo: str, descripcion: str, observaciones: str
) -> dict:
    datos = {
        **_DATOS_VALIDOS,
        "tipo": "oportunidad",
        "oportunidad": {
            "codigo": codigo,
            "descripcion": descripcion,
            "observaciones": observaciones,
        },
    }
    return {"datos": datos, "respuesta": cliente.post("/api/v1/tareas", json=datos)}


def _comprobar_oportunidad(
    respuesta, codigo_estado: int, codigo: str, descripcion: str, observaciones: str
) -> dict:
    assert respuesta.status_code == codigo_estado
    cuerpo = respuesta.json()
    assert cuerpo["tipo"] == "oportunidad"
    assert cuerpo["oportunidad"] == {
        "codigo": codigo,
        "descripcion": _texto_o_nulo(descripcion),
        "observaciones": _texto_o_nulo(observaciones),
    }
    return cuerpo


@then(parsers.re(f"la API responde que la tarea se ha creado con la oportunidad de {_OPORTUNIDAD}"))
def la_tarea_se_ha_creado_con_oportunidad(
    peticion: dict, codigo: str, descripcion: str, observaciones: str
) -> None:
    cuerpo = _comprobar_oportunidad(peticion["respuesta"], 201, codigo, descripcion, observaciones)
    sin_tipo = {k: v for k, v in peticion["datos"].items() if k not in {"tipo", "oportunidad"}}
    assert {k: cuerpo[k] for k in sin_tipo} == sin_tipo


@then(
    parsers.re(
        f"la API responde que la tarea se ha actualizado con la oportunidad de {_OPORTUNIDAD}"
    )
)
def la_tarea_se_ha_actualizado_con_oportunidad(
    peticion: dict, codigo: str, descripcion: str, observaciones: str
) -> None:
    cuerpo = _comprobar_oportunidad(peticion["respuesta"], 200, codigo, descripcion, observaciones)
    assert cuerpo["id"] == peticion["id"]


@when("intento crear una tarea de tipo oportunidad sin sus datos", target_fixture="peticion")
def crear_oportunidad_sin_datos(cliente: TestClient) -> dict:
    datos = {**_DATOS_VALIDOS, "tipo": "oportunidad"}
    return {"datos": datos, "respuesta": cliente.post("/api/v1/tareas", json=datos)}


@when(
    "intento crear una tarea sin tipo con los datos de una oportunidad", target_fixture="peticion"
)
def crear_sin_tipo_con_oportunidad(cliente: TestClient) -> dict:
    datos = {**_DATOS_VALIDOS, **_con_oportunidad(), "tipo": None}
    return {"datos": datos, "respuesta": cliente.post("/api/v1/tareas", json=datos)}


@given(
    parsers.parse('que existe una tarea de tipo oportunidad con código "{codigo}"'),
    target_fixture="tarea_previa",
)
def existe_una_tarea_oportunidad(cliente: TestClient, codigo: str) -> dict:
    datos = {**_DATOS_VALIDOS, **_con_oportunidad(codigo=codigo, observaciones="Notas")}
    respuesta = cliente.post("/api/v1/tareas", json=datos)
    assert respuesta.status_code == 201
    return respuesta.json()


@when(
    parsers.re(f"edito esa tarea con la oportunidad de {_OPORTUNIDAD}"),
    target_fixture="peticion",
)
def editar_oportunidad(
    cliente: TestClient, tarea_previa: dict, codigo: str, descripcion: str, observaciones: str
) -> dict:
    datos = {
        **_DATOS_VALIDOS,
        **_con_oportunidad(codigo=codigo, descripcion=descripcion, observaciones=observaciones),
    }
    respuesta = cliente.put(f"/api/v1/tareas/{tarea_previa['id']}", json=datos)
    return {"id": tarea_previa["id"], "datos": datos, "respuesta": respuesta}


@when("edito esa tarea sin tipo", target_fixture="peticion")
def editar_sin_tipo(cliente: TestClient, tarea_previa: dict) -> dict:
    datos = {**_DATOS_VALIDOS, "tipo": None, "oportunidad": None}
    respuesta = cliente.put(f"/api/v1/tareas/{tarea_previa['id']}", json=datos)
    return {"id": tarea_previa["id"], "datos": datos, "respuesta": respuesta}


@when(
    "intento editar esa tarea sin tipo pero con los datos de una oportunidad",
    target_fixture="peticion",
)
def editar_sin_tipo_con_oportunidad(cliente: TestClient, tarea_previa: dict) -> dict:
    datos = {**_DATOS_VALIDOS, **_con_oportunidad(), "tipo": None}
    respuesta = cliente.put(f"/api/v1/tareas/{tarea_previa['id']}", json=datos)
    return {"id": tarea_previa["id"], "datos": datos, "respuesta": respuesta}


@then("la API responde que la tarea se ha actualizado sin tipo ni oportunidad")
def la_tarea_se_ha_actualizado_sin_tipo(peticion: dict) -> None:
    respuesta = peticion["respuesta"]
    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "id": peticion["id"],
        **_OPCIONALES_POR_DEFECTO,
        **peticion["datos"],
    }


@then("el listado muestra solo esa tarea")
def el_listado_muestra_solo_esa_tarea(cliente: TestClient, peticion: dict) -> None:
    respuesta = cliente.get("/api/v1/tareas")
    assert respuesta.status_code == 200
    assert respuesta.json() == [peticion["respuesta"].json()]


@then("el listado muestra la tarea de tipo oportunidad sin cambios")
def el_listado_muestra_la_oportunidad_sin_cambios(cliente: TestClient, tarea_previa: dict) -> None:
    assert cliente.get("/api/v1/tareas").json() == [tarea_previa]


_ESTADOS = {"completada": True, "pendiente": False}


def _cambiar_estado(cliente: TestClient, id_tarea: int, cuerpo: object):
    return cliente.patch(f"/api/v1/tareas/{id_tarea}/completada", json=cuerpo)


@then("ninguna tarea del listado está completada")
def ninguna_tarea_esta_completada(respuesta) -> None:
    assert respuesta.status_code == 200
    tareas = respuesta.json()
    assert tareas
    assert all(t["completada"] is False for t in tareas)


@given(parsers.parse('la tarea "{nombre}" está completada'))
def la_tarea_esta_completada(cliente: TestClient, tareas_previas: list[dict], nombre: str) -> None:
    respuesta = _cambiar_estado(cliente, _id_de(cliente, nombre), {"completada": True})
    assert respuesta.status_code == 200
    for tarea in tareas_previas:
        if tarea["nombre"] == nombre:
            tarea["completada"] = True


@when(
    parsers.re(r'marco la tarea "(?P<nombre>[^"]+)" como (?P<estado>completada|pendiente)'),
    target_fixture="respuesta",
)
def marcar_tarea(cliente: TestClient, nombre: str, estado: str):
    return _cambiar_estado(cliente, _id_de(cliente, nombre), {"completada": _ESTADOS[estado]})


@when(
    parsers.parse("intento marcar como completada la tarea con id {id_tarea:d}"),
    target_fixture="respuesta",
)
def marcar_tarea_inexistente(cliente: TestClient, id_tarea: int):
    return _cambiar_estado(cliente, id_tarea, {"completada": True})


@when(
    parsers.parse('intento cambiar el estado de la tarea "{nombre}" con el cuerpo {cuerpo}'),
    target_fixture="respuesta",
)
def cambiar_estado_invalido(cliente: TestClient, nombre: str, cuerpo: str):
    return _cambiar_estado(cliente, _id_de(cliente, nombre), json.loads(cuerpo))


@then(
    parsers.re(
        r'la API responde con la tarea "(?P<nombre>[^"]+)" (?P<estado>completada|pendiente) '
        r"y el resto de sus datos sin cambios"
    )
)
def la_api_responde_con_el_estado(
    respuesta, tareas_previas: list[dict], nombre: str, estado: str
) -> None:
    assert respuesta.status_code == 200
    previa = next(t for t in tareas_previas if t["nombre"] == nombre)
    assert respuesta.json() == {**previa, "completada": _ESTADOS[estado]}


@then(
    parsers.re(
        r'en el listado "(?P<primera>[^"]+)" está (?P<estado_primera>completada|pendiente) '
        r'y "(?P<segunda>[^"]+)" (?P<estado_segunda>completada|pendiente)'
    )
)
def el_listado_muestra_los_estados(
    cliente: TestClient,
    tareas_previas: list[dict],
    primera: str,
    estado_primera: str,
    segunda: str,
    estado_segunda: str,
) -> None:
    estados = {primera: _ESTADOS[estado_primera], segunda: _ESTADOS[estado_segunda]}
    esperado = [{**t, "completada": estados[t["nombre"]]} for t in tareas_previas]
    listado = cliente.get("/api/v1/tareas").json()
    # Si la tarea se editó, el resto de sus datos los comprueba el paso anterior.
    assert [t["completada"] for t in listado] == [t["completada"] for t in esperado]
    assert [t["id"] for t in listado] == [t["id"] for t in esperado]


@when("creo una tarea indicando que está completada", target_fixture="peticion")
def crear_tarea_completada(cliente: TestClient) -> dict:
    datos = {**_DATOS_VALIDOS, "completada": True}
    return {"datos": datos, "respuesta": cliente.post("/api/v1/tareas", json=datos)}


@then("la API responde que la tarea se ha creado pendiente")
def la_tarea_se_ha_creado_pendiente(peticion: dict) -> None:
    respuesta = peticion["respuesta"]
    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    sin_estado = {k: v for k, v in peticion["datos"].items() if k != "completada"}
    assert cuerpo == {"id": cuerpo["id"], **_OPCIONALES_POR_DEFECTO, **sin_estado}


@when(
    parsers.parse('edito la tarea "{nombre}" indicando que está pendiente'),
    target_fixture="peticion",
)
def editar_tarea_indicando_pendiente(cliente: TestClient, nombre: str) -> dict:
    id_tarea = _id_de(cliente, nombre)
    datos = {**_DATOS_VALIDOS, "nombre": nombre, "descripcion": "Editada", "completada": False}
    respuesta = cliente.put(f"/api/v1/tareas/{id_tarea}", json=datos)
    return {"id": id_tarea, "datos": datos, "respuesta": respuesta}


@then(parsers.parse('la API responde con la tarea "{nombre}" completada y los datos editados'))
def la_tarea_editada_sigue_completada(peticion: dict, nombre: str) -> None:
    respuesta = peticion["respuesta"]
    assert respuesta.status_code == 200
    sin_estado = {k: v for k, v in peticion["datos"].items() if k != "completada"}
    assert respuesta.json() == {
        "id": peticion["id"],
        **_OPCIONALES_POR_DEFECTO,
        **sin_estado,
        "completada": True,
    }
