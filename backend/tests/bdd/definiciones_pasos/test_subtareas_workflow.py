from fastapi.testclient import TestClient
from httpx import Response
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("subtareas_workflow.feature")

_TAREAS = "/api/v1/tareas"
_WORKFLOW = "/api/v1/workflow-oportunidades/pasos"

_DATOS = {"descripcion": "d", "fecha_creacion": "2026-11-10T09:00:00"}

_CLAVES_SUBTAREA = {"id", "nombre", "asignado", "prioridad", "resuelta", "comentarios"}

Subtarea = tuple[str, str | None, int | None, bool]


def _oportunidad(nombre: str, codigo: str = "OP-1") -> dict:
    return {
        **_DATOS,
        "nombre": nombre,
        "tipo": "oportunidad",
        "oportunidad": {"codigo": codigo},
    }


def _lista(texto: str, separador: str = ", ") -> list[str]:
    return texto.split(separador) if texto else []


def _pendientes(texto: str) -> list[Subtarea]:
    """Convierte "A, B" en subtareas pendientes sin persona ni prioridad."""
    return [(nombre, None, None, False) for nombre in _lista(texto)]


def _esperadas(texto: str) -> list[Subtarea]:
    """Convierte "A: Ana, 2, resuelta; B: -, -, pendiente" en tuplas comparables."""
    subtareas = []
    for elemento in _lista(texto, "; "):
        nombre, resto = elemento.split(": ")
        asignado, prioridad, estado = resto.split(", ")
        subtareas.append(
            (
                nombre,
                None if asignado == "-" else asignado,
                None if prioridad == "-" else int(prioridad),
                estado == "resuelta",
            )
        )
    return subtareas


def _subtareas(tarea: dict) -> list[Subtarea]:
    subtareas = tarea["subtareas"]
    assert all(set(s) == _CLAVES_SUBTAREA for s in subtareas)
    assert all(s["comentarios"] == 0 for s in subtareas)
    ids = [s["id"] for s in subtareas]
    assert ids == sorted(set(ids))  # Ids únicos y en el orden del workflow.
    return [(s["nombre"], s["asignado"], s["prioridad"], s["resuelta"]) for s in subtareas]


def _tarea(cliente: TestClient, nombre: str) -> dict:
    respuesta = cliente.get(_TAREAS)
    assert respuesta.status_code == 200
    return next(t for t in respuesta.json() if t["nombre"] == nombre)


def _id_subtarea(cliente: TestClient, tarea: str, subtarea: str) -> int:
    return next(s["id"] for s in _tarea(cliente, tarea)["subtareas"] if s["nombre"] == subtarea)


def _ruta_subtarea(cliente: TestClient, tarea: str, subtarea: str) -> str:
    id_tarea = _tarea(cliente, tarea)["id"]
    return f"{_TAREAS}/{id_tarea}/subtareas/{_id_subtarea(cliente, tarea, subtarea)}"


def _crear(cliente: TestClient, cuerpo: dict) -> Response:
    respuesta = cliente.post(_TAREAS, json=cuerpo)
    assert respuesta.status_code == 201
    return respuesta


def _poner_workflow(cliente: TestClient, nombres: list[str]) -> None:
    for paso in cliente.get(_WORKFLOW).json():
        assert cliente.delete(f"{_WORKFLOW}/{paso['id']}").status_code == 204
    for nombre in nombres:
        assert cliente.post(_WORKFLOW, json={"nombre": nombre}).status_code == 201


def _resolver(cliente: TestClient, tarea: str, subtarea: str) -> None:
    ruta = f"{_ruta_subtarea(cliente, tarea, subtarea)}/resuelta"
    assert cliente.patch(ruta, json={"resuelta": True}).status_code == 200


@given(parsers.parse('que el workflow de las oportunidades tiene los pasos "{pasos}"'))
def workflow_con_pasos(cliente: TestClient, pasos: str) -> None:
    _poner_workflow(cliente, _lista(pasos))


@given("que el workflow de las oportunidades no tiene pasos")
def workflow_vacio(cliente: TestClient) -> None:
    _poner_workflow(cliente, [])


@given(parsers.parse('que existe la oportunidad "{nombre}"'))
def existe_la_oportunidad(cliente: TestClient, nombre: str) -> None:
    _crear(cliente, _oportunidad(nombre))


@given(parsers.parse('que existe la tarea sin tipo "{nombre}"'))
def existe_la_tarea_sin_tipo(cliente: TestClient, nombre: str) -> None:
    _crear(cliente, {**_DATOS, "nombre": nombre})


@given(parsers.parse('la subtarea "{subtarea}" de "{tarea}" está resuelta'))
def la_subtarea_esta_resuelta(cliente: TestClient, subtarea: str, tarea: str) -> None:
    _resolver(cliente, tarea, subtarea)


@when(parsers.parse('creo una tarea de tipo oportunidad "{nombre}"'), target_fixture="respuesta")
def crear_oportunidad(cliente: TestClient, nombre: str) -> Response:
    return _crear(cliente, _oportunidad(nombre))


@when(parsers.parse('creo una tarea sin tipo "{nombre}"'), target_fixture="respuesta")
def crear_sin_tipo(cliente: TestClient, nombre: str) -> Response:
    return _crear(cliente, {**_DATOS, "nombre": nombre})


@when(parsers.parse('cambio el workflow a los pasos "{pasos}"'))
def cambiar_workflow(cliente: TestClient, pasos: str) -> None:
    """Reordena, borra y añade pasos del workflow."""
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


@when(parsers.parse('resuelvo la subtarea "{subtarea}" de "{tarea}"'))
def resolver_subtarea(cliente: TestClient, subtarea: str, tarea: str) -> None:
    _resolver(cliente, tarea, subtarea)


@when(
    parsers.parse(
        'renombro la subtarea "{subtarea}" de "{tarea}" a "{nombre}" con la persona '
        '"{persona}" y la prioridad {prioridad:d}'
    )
)
def renombrar_subtarea(
    cliente: TestClient, subtarea: str, tarea: str, nombre: str, persona: str, prioridad: int
) -> None:
    cuerpo = {"nombre": nombre, "asignado": persona, "prioridad": prioridad}
    assert cliente.put(_ruta_subtarea(cliente, tarea, subtarea), json=cuerpo).status_code == 200


@when(parsers.parse('borro la subtarea "{subtarea}" de "{tarea}"'))
def borrar_subtarea(cliente: TestClient, subtarea: str, tarea: str) -> None:
    assert cliente.delete(_ruta_subtarea(cliente, tarea, subtarea)).status_code == 200


@when(parsers.parse('añado la subtarea "{subtarea}" a "{tarea}"'))
def anadir_subtarea(cliente: TestClient, subtarea: str, tarea: str) -> None:
    ruta = f"{_TAREAS}/{_tarea(cliente, tarea)['id']}/subtareas"
    assert cliente.post(ruta, json={"nombre": subtarea}).status_code == 201


def _editar(cliente: TestClient, nombre: str, cuerpo: dict) -> Response:
    respuesta = cliente.put(f"{_TAREAS}/{_tarea(cliente, nombre)['id']}", json=cuerpo)
    assert respuesta.status_code == 200
    return respuesta


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
    parsers.parse('intento marcar como hecho el paso {id_paso:d} de "{tarea}" por la ruta antigua'),
    target_fixture="respuesta",
)
def marcar_paso_por_la_ruta_antigua(cliente: TestClient, id_paso: int, tarea: str) -> Response:
    ruta = f"{_TAREAS}/{_tarea(cliente, tarea)['id']}/pasos/{id_paso}"
    return cliente.patch(ruta, json={"hecho": True})


@then(parsers.parse('la API responde que "{nombre}" tiene las subtareas "{subtareas}" pendientes'))
def la_api_responde_con_subtareas_pendientes(
    respuesta: Response, nombre: str, subtareas: str
) -> None:
    assert respuesta.status_code == 201
    assert respuesta.json()["nombre"] == nombre
    assert _subtareas(respuesta.json()) == _pendientes(subtareas)


@then("la respuesta de la tarea no incluye pasos de la oportunidad")
def sin_pasos_de_la_oportunidad(respuesta: Response) -> None:
    assert "pasos_oportunidad" not in respuesta.json()


@then(parsers.parse('la API responde que "{nombre}" no tiene subtareas'))
def la_api_responde_sin_subtareas(respuesta: Response, nombre: str) -> None:
    assert respuesta.status_code == 201
    assert respuesta.json()["nombre"] == nombre
    assert respuesta.json()["subtareas"] == []


@then(
    parsers.parse('al consultar las tareas "{nombre}" tiene las subtareas "{subtareas}" pendientes')
)
def el_listado_tiene_subtareas_pendientes(cliente: TestClient, nombre: str, subtareas: str) -> None:
    assert _subtareas(_tarea(cliente, nombre)) == _pendientes(subtareas)


@then(parsers.parse('al consultar las tareas "{nombre}" tiene las subtareas "{subtareas}"'))
def el_listado_tiene_subtareas(cliente: TestClient, nombre: str, subtareas: str) -> None:
    assert _subtareas(_tarea(cliente, nombre)) == _esperadas(subtareas)


@then(parsers.parse('al consultar las tareas "{nombre}" no tiene subtareas'))
def el_listado_sin_subtareas(cliente: TestClient, nombre: str) -> None:
    assert _tarea(cliente, nombre)["subtareas"] == []


@then("la API responde que la ruta no existe")
def la_ruta_no_existe(respuesta: Response) -> None:
    assert respuesta.status_code == 404
    assert respuesta.json() == {"detail": "Not Found"}
