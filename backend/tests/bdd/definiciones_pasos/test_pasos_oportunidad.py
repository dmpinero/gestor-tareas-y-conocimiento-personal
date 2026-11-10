import json

from fastapi.testclient import TestClient
from httpx import Response
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("pasos_oportunidad.feature")

_TAREAS = "/api/v1/tareas"
_WORKFLOW = "/api/v1/workflow-oportunidades/pasos"

_DATOS = {"descripcion": "d", "fecha_creacion": "2026-11-10T09:00:00"}


def _oportunidad(nombre: str, codigo: str = "OP-1") -> dict:
    return {
        **_DATOS,
        "nombre": nombre,
        "tipo": "oportunidad",
        "oportunidad": {"codigo": codigo},
    }


def _lista(texto: str) -> list[str]:
    return texto.split(", ") if texto else []


def _esperados(texto: str) -> list[tuple[int, str, bool]]:
    """Convierte "A: hecho, B: pendiente" en [(1, "A", True), (2, "B", False)]."""
    pasos = []
    for numero, elemento in enumerate(_lista(texto), start=1):
        nombre, estado = elemento.split(": ")
        pasos.append((numero, nombre, estado == "hecho"))
    return pasos


def _pendientes(texto: str) -> list[tuple[int, str, bool]]:
    return [(numero, nombre, False) for numero, nombre in enumerate(_lista(texto), start=1)]


def _pasos(tarea: dict) -> list[tuple[int, str, bool]]:
    pasos = tarea["pasos_oportunidad"]
    assert all(set(p) == {"id", "numero", "nombre", "hecho"} for p in pasos)
    assert len({p["id"] for p in pasos}) == len(pasos)
    return [(p["numero"], p["nombre"], p["hecho"]) for p in pasos]


def _tarea(cliente: TestClient, nombre: str) -> dict:
    respuesta = cliente.get(_TAREAS)
    assert respuesta.status_code == 200
    return next(t for t in respuesta.json() if t["nombre"] == nombre)


def _id_paso(cliente: TestClient, tarea: str, paso: str) -> int:
    return next(p["id"] for p in _tarea(cliente, tarea)["pasos_oportunidad"] if p["nombre"] == paso)


def _crear(cliente: TestClient, cuerpo: dict) -> Response:
    respuesta = cliente.post(_TAREAS, json=cuerpo)
    assert respuesta.status_code == 201
    return respuesta


def _ruta_paso(id_tarea: int, id_paso: int) -> str:
    return f"{_TAREAS}/{id_tarea}/pasos/{id_paso}"


def _poner_workflow(cliente: TestClient, nombres: list[str]) -> None:
    for paso in cliente.get(_WORKFLOW).json():
        assert cliente.delete(f"{_WORKFLOW}/{paso['id']}").status_code == 204
    for nombre in nombres:
        assert cliente.post(_WORKFLOW, json={"nombre": nombre}).status_code == 201


@given(parsers.parse('que el workflow de las oportunidades tiene los pasos "{pasos}"'))
def workflow_con_pasos(cliente: TestClient, pasos: str) -> None:
    _poner_workflow(cliente, _lista(pasos))


@given(parsers.parse('que existe la oportunidad "{nombre}"'))
def existe_la_oportunidad(cliente: TestClient, nombre: str) -> None:
    _crear(cliente, _oportunidad(nombre))


@given(parsers.parse('que existe la tarea sin tipo "{nombre}"'))
def existe_la_tarea_sin_tipo(cliente: TestClient, nombre: str) -> None:
    _crear(cliente, {**_DATOS, "nombre": nombre})


@given(parsers.parse('el paso "{paso}" de "{tarea}" está hecho'))
def el_paso_esta_hecho(cliente: TestClient, paso: str, tarea: str) -> None:
    ruta = _ruta_paso(_tarea(cliente, tarea)["id"], _id_paso(cliente, tarea, paso))
    assert cliente.patch(ruta, json={"hecho": True}).status_code == 200


@when(parsers.parse('creo una tarea de tipo oportunidad "{nombre}"'), target_fixture="respuesta")
def crear_oportunidad(cliente: TestClient, nombre: str) -> Response:
    return _crear(cliente, _oportunidad(nombre))


@when(parsers.parse('creo una tarea sin tipo "{nombre}"'), target_fixture="respuesta")
def crear_sin_tipo(cliente: TestClient, nombre: str) -> Response:
    return _crear(cliente, {**_DATOS, "nombre": nombre})


@when(parsers.parse('cambio el workflow a los pasos "{pasos}"'))
def cambiar_workflow(cliente: TestClient, pasos: str) -> None:
    """Reordena, renombra, borra y añade pasos del workflow."""
    actuales = {p["nombre"]: p["id"] for p in cliente.get(_WORKFLOW).json()}
    nuevos = _lista(pasos)
    orden = [actuales[n] for n in nuevos if n in actuales]
    orden += [i for n, i in actuales.items() if n not in nuevos]
    assert cliente.put(f"{_WORKFLOW}/orden", json={"ids": orden}).status_code == 200
    for nombre, id_paso in actuales.items():
        if nombre not in nuevos:
            assert cliente.delete(f"{_WORKFLOW}/{id_paso}").status_code == 204
    for nombre in nuevos:
        if nombre not in actuales:
            assert cliente.post(_WORKFLOW, json={"nombre": nombre}).status_code == 201
    assert [p["nombre"] for p in cliente.get(_WORKFLOW).json()] == nuevos


@when(
    parsers.re(
        r'marco el paso "(?P<paso>[^"]+)" de "(?P<tarea>[^"]+)" '
        r"como (?P<estado>hecho|pendiente)"
    ),
    target_fixture="respuesta",
)
def marcar_paso(cliente: TestClient, paso: str, tarea: str, estado: str) -> Response:
    ruta = _ruta_paso(_tarea(cliente, tarea)["id"], _id_paso(cliente, tarea, paso))
    return cliente.patch(ruta, json={"hecho": estado == "hecho"})


def _editar(cliente: TestClient, nombre: str, cuerpo: dict) -> Response:
    return cliente.put(f"{_TAREAS}/{_tarea(cliente, nombre)['id']}", json=cuerpo)


@when(
    parsers.parse('edito "{nombre}" como oportunidad con el código "{codigo}"'),
    target_fixture="respuesta",
)
def editar_como_oportunidad(cliente: TestClient, nombre: str, codigo: str) -> Response:
    return _editar(cliente, nombre, _oportunidad(nombre, codigo))


@when(parsers.parse('edito "{nombre}" sin tipo'), target_fixture="respuesta")
def editar_sin_tipo(cliente: TestClient, nombre: str) -> Response:
    return _editar(cliente, nombre, {**_DATOS, "nombre": nombre})


@when(
    parsers.parse('intento cambiar el paso "{paso}" de "{tarea}" con el cuerpo {cuerpo}'),
    target_fixture="respuesta",
)
def cambiar_paso_con_cuerpo(cliente: TestClient, paso: str, tarea: str, cuerpo: str) -> Response:
    ruta = _ruta_paso(_tarea(cliente, tarea)["id"], _id_paso(cliente, tarea, paso))
    return cliente.patch(ruta, json=json.loads(cuerpo))


@when(
    parsers.parse('intento marcar como hecho el paso "{paso}" de la tarea con id {id_tarea:d}'),
    target_fixture="respuesta",
)
def marcar_paso_de_tarea_inexistente(cliente: TestClient, paso: str, id_tarea: int) -> Response:
    id_paso = next(
        p["id"]
        for t in cliente.get(_TAREAS).json()
        for p in t["pasos_oportunidad"]
        if p["nombre"] == paso
    )
    return cliente.patch(_ruta_paso(id_tarea, id_paso), json={"hecho": True})


@when(
    parsers.parse('intento marcar como hecho el paso con id {id_paso:d} de "{tarea}"'),
    target_fixture="respuesta",
)
def marcar_paso_inexistente(cliente: TestClient, id_paso: int, tarea: str) -> Response:
    return cliente.patch(_ruta_paso(_tarea(cliente, tarea)["id"], id_paso), json={"hecho": True})


@when(
    parsers.parse('intento marcar como hecho el paso "{paso}" de "{otra}" a través de "{tarea}"'),
    target_fixture="respuesta",
)
def marcar_paso_de_otra_tarea(cliente: TestClient, paso: str, otra: str, tarea: str) -> Response:
    ruta = _ruta_paso(_tarea(cliente, tarea)["id"], _id_paso(cliente, otra, paso))
    return cliente.patch(ruta, json={"hecho": True})


@then(parsers.parse('la API responde que "{nombre}" tiene los pasos "{pasos}" pendientes'))
def la_api_responde_con_pasos_pendientes(respuesta: Response, nombre: str, pasos: str) -> None:
    assert respuesta.status_code == 201
    assert respuesta.json()["nombre"] == nombre
    assert _pasos(respuesta.json()) == _pendientes(pasos)


@then(parsers.parse('la API responde que "{nombre}" no tiene pasos'))
def la_api_responde_sin_pasos(respuesta: Response, nombre: str) -> None:
    assert respuesta.status_code in (200, 201)
    assert respuesta.json()["nombre"] == nombre
    assert respuesta.json()["pasos_oportunidad"] == []


@then(parsers.parse('la API responde con "{nombre}" y sus pasos "{pasos}"'))
def la_api_responde_con_pasos(respuesta: Response, nombre: str, pasos: str) -> None:
    assert respuesta.status_code == 200
    assert respuesta.json()["nombre"] == nombre
    assert _pasos(respuesta.json()) == _esperados(pasos)


@then(parsers.parse('al consultar las tareas "{nombre}" tiene los pasos "{pasos}" pendientes'))
def el_listado_tiene_pasos_pendientes(cliente: TestClient, nombre: str, pasos: str) -> None:
    assert _pasos(_tarea(cliente, nombre)) == _pendientes(pasos)


@then(parsers.parse('al consultar las tareas "{nombre}" tiene los pasos "{pasos}"'))
def el_listado_tiene_pasos(cliente: TestClient, nombre: str, pasos: str) -> None:
    assert _pasos(_tarea(cliente, nombre)) == _esperados(pasos)


@then(parsers.parse('al consultar las tareas "{nombre}" no tiene pasos'))
def el_listado_sin_pasos(cliente: TestClient, nombre: str) -> None:
    assert _tarea(cliente, nombre)["pasos_oportunidad"] == []


@then("la API rechaza el cambio del paso por datos inválidos")
def la_api_rechaza_por_datos_invalidos(respuesta: Response) -> None:
    assert respuesta.status_code == 422


@then(parsers.parse("la API responde que no existe la tarea con id {id_tarea:d}"))
def la_api_responde_tarea_inexistente(respuesta: Response, id_tarea: int) -> None:
    # El cuerpo distingue el 404 de dominio del 404 de "ruta no encontrada".
    assert respuesta.status_code == 404
    assert respuesta.json() == {"detalle": f"No existe la tarea con id {id_tarea}"}


@then(parsers.parse('la API responde que "{tarea}" no tiene el paso con id {id_paso:d}'))
def la_api_responde_paso_inexistente(
    cliente: TestClient, respuesta: Response, tarea: str, id_paso: int
) -> None:
    id_tarea = _tarea(cliente, tarea)["id"]
    assert respuesta.status_code == 404
    assert respuesta.json() == {
        "detalle": f"No existe el paso con id {id_paso} en la tarea con id {id_tarea}"
    }


@then(parsers.parse('la API responde que "{tarea}" no tiene el paso "{paso}" de "{otra}"'))
def la_api_responde_paso_de_otra(
    cliente: TestClient, respuesta: Response, tarea: str, paso: str, otra: str
) -> None:
    la_api_responde_paso_inexistente(cliente, respuesta, tarea, _id_paso(cliente, otra, paso))
