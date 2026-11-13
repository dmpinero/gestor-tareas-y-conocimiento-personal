import json

from fastapi.testclient import TestClient
from httpx import Response
from pytest_bdd import given, parsers, scenarios, then, when
from sqlalchemy import func, select

from gestor_tareas.infraestructura.persistencia.modelos import SubtareaModelo, TareaModelo
from gestor_tareas.infraestructura.persistencia.sesion import FabricaSesiones

scenarios("workflow_de_las_tareas.feature")

_TAREAS = "/api/v1/tareas"
_WORKFLOWS = "/api/v1/workflows"
_ID_INEXISTENTE = 999999

_DATOS = {"descripcion": "d", "fecha_creacion": "2026-11-10T09:00:00"}

_CLAVES_SUBTAREA = {"id", "nombre", "asignado", "prioridad", "resuelta", "comentarios"}

# (nombre, resuelta) de cada subtarea, en orden de alta.
Subtarea = tuple[str, bool]


def _lista(texto: str, separador: str = ", ") -> list[str]:
    return texto.split(separador) if texto else []


def _pendientes(texto: str) -> list[Subtarea]:
    return [(nombre, False) for nombre in _lista(texto)]


def _esperadas(texto: str) -> list[Subtarea]:
    """Convierte "A: resuelta; B: pendiente" en tuplas comparables."""
    subtareas = []
    for elemento in _lista(texto, "; "):
        nombre, estado = elemento.split(": ")
        subtareas.append((nombre, estado == "resuelta"))
    return subtareas


def _workflows(cliente: TestClient) -> list[dict]:
    respuesta = cliente.get(_WORKFLOWS)
    assert respuesta.status_code == 200
    return respuesta.json()


def _workflow(cliente: TestClient, nombre: str) -> dict:
    return next(w for w in _workflows(cliente) if w["nombre"] == nombre)


def _crear_workflow(cliente: TestClient, nombre: str, pasos: list[str]) -> None:
    respuesta = cliente.post(_WORKFLOWS, json={"nombre": nombre})
    assert respuesta.status_code == 201
    for paso in pasos:
        ruta = f"{_WORKFLOWS}/{respuesta.json()['id']}/pasos"
        assert cliente.post(ruta, json={"nombre": paso}).status_code == 201


def _subtareas(tarea: dict) -> list[Subtarea]:
    """Subtareas de la respuesta: sin persona ni prioridad, sin comentarios y por id."""
    subtareas = tarea["subtareas"]
    assert all(set(s) == _CLAVES_SUBTAREA for s in subtareas)
    assert all(s["comentarios"] == 0 for s in subtareas)
    assert all(s["asignado"] is None and s["prioridad"] is None for s in subtareas)
    ids = [s["id"] for s in subtareas]
    assert ids == sorted(set(ids))
    return [(s["nombre"], s["resuelta"]) for s in subtareas]


def _subtareas_guardadas(id_tarea: int) -> list[Subtarea]:
    sesion = FabricaSesiones()
    try:
        consulta = (
            select(SubtareaModelo.nombre, SubtareaModelo.resuelta)
            .where(SubtareaModelo.tarea_id == id_tarea)
            .order_by(SubtareaModelo.id)
        )
        return [(fila.nombre, fila.resuelta) for fila in sesion.execute(consulta)]
    finally:
        sesion.close()


def _workflow_guardado(id_tarea: int) -> int | None:
    sesion = FabricaSesiones()
    try:
        return sesion.scalars(
            select(TareaModelo.workflow_id).where(TareaModelo.id == id_tarea)
        ).one()
    finally:
        sesion.close()


def _tarea(cliente: TestClient, nombre: str) -> dict:
    respuesta = cliente.get(_TAREAS)
    assert respuesta.status_code == 200
    return next(t for t in respuesta.json() if t["nombre"] == nombre)


def _cuerpo(nombre: str, workflow_id: int | None = None, oportunidad: bool = False) -> dict:
    cuerpo: dict = {**_DATOS, "nombre": nombre, "workflow_id": workflow_id}
    if oportunidad:
        cuerpo |= {"tipo": "oportunidad", "oportunidad": {"codigo": "OP-1"}}
    return cuerpo


def _crear(cliente: TestClient, cuerpo: dict) -> Response:
    respuesta = cliente.post(_TAREAS, json=cuerpo)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta


def _editar(cliente: TestClient, nombre: str, cuerpo: dict) -> Response:
    respuesta = cliente.put(f"{_TAREAS}/{_tarea(cliente, nombre)['id']}", json=cuerpo)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta


def _ruta_subtarea(cliente: TestClient, tarea: str, subtarea: str) -> str:
    datos = _tarea(cliente, tarea)
    id_subtarea = next(s["id"] for s in datos["subtareas"] if s["nombre"] == subtarea)
    return f"{_TAREAS}/{datos['id']}/subtareas/{id_subtarea}"


def _resolver(cliente: TestClient, tarea: str, subtarea: str) -> None:
    ruta = f"{_ruta_subtarea(cliente, tarea, subtarea)}/resuelta"
    assert cliente.patch(ruta, json={"resuelta": True}).status_code == 200


def _comprobar_workflow(tarea: dict, nombre: str | None, cliente: TestClient) -> None:
    if nombre is None:
        assert tarea["workflow"] is None
        assert _workflow_guardado(tarea["id"]) is None
        return
    workflow = _workflow(cliente, nombre)
    assert tarea["workflow"] == {"id": workflow["id"], "nombre": nombre}
    assert _workflow_guardado(tarea["id"]) == workflow["id"]


# --- Dado -------------------------------------------------------------------


@given(parsers.parse('que el workflow "{nombre}" tiene los pasos "{pasos}"'))
def workflow_con_pasos(cliente: TestClient, nombre: str, pasos: str) -> None:
    _crear_workflow(cliente, nombre, _lista(pasos))


@given(parsers.parse('que existe el workflow "{nombre}" con los pasos "{pasos}"'))
def existe_el_workflow(cliente: TestClient, nombre: str, pasos: str) -> None:
    _crear_workflow(cliente, nombre, _lista(pasos))


@given(parsers.parse('que existe el workflow "{nombre}" sin pasos'))
def existe_el_workflow_sin_pasos(cliente: TestClient, nombre: str) -> None:
    _crear_workflow(cliente, nombre, [])


@given(parsers.parse('que reordeno los pasos del workflow "{nombre}" como "{pasos}"'))
def reordenar_workflow(cliente: TestClient, nombre: str, pasos: str) -> None:
    workflow = _workflow(cliente, nombre)
    por_nombre = {p["nombre"]: p["id"] for p in workflow["pasos"]}
    ids = [por_nombre[p] for p in _lista(pasos)]
    ruta = f"{_WORKFLOWS}/{workflow['id']}/orden"
    assert cliente.put(ruta, json={"ids": ids}).status_code == 200


@given(parsers.parse('que existe la tarea "{nombre}" sin workflow'))
def existe_la_tarea_sin_workflow(cliente: TestClient, nombre: str) -> None:
    _crear(cliente, _cuerpo(nombre))


@given(parsers.parse('que existe la tarea "{nombre}" con el workflow "{workflow}"'))
def existe_la_tarea_con_workflow(cliente: TestClient, nombre: str, workflow: str) -> None:
    _crear(cliente, _cuerpo(nombre, _workflow(cliente, workflow)["id"]))


@given(parsers.parse('la tarea "{tarea}" tiene la subtarea "{subtarea}" resuelta'))
def la_tarea_tiene_una_subtarea_resuelta(cliente: TestClient, tarea: str, subtarea: str) -> None:
    ruta = f"{_TAREAS}/{_tarea(cliente, tarea)['id']}/subtareas"
    assert cliente.post(ruta, json={"nombre": subtarea}).status_code == 201
    _resolver(cliente, tarea, subtarea)


@given(parsers.parse('la subtarea "{subtarea}" de "{tarea}" está resuelta'))
def la_subtarea_esta_resuelta(cliente: TestClient, subtarea: str, tarea: str) -> None:
    _resolver(cliente, tarea, subtarea)


@given(parsers.parse('borro la subtarea "{subtarea}" de "{tarea}"'))
def borrar_subtarea(cliente: TestClient, subtarea: str, tarea: str) -> None:
    assert cliente.delete(_ruta_subtarea(cliente, tarea, subtarea)).status_code == 200


# --- Cuando -----------------------------------------------------------------


@when(
    parsers.parse('creo la tarea "{nombre}" con el workflow "{workflow}"'),
    target_fixture="respuesta",
)
def crear_con_workflow(cliente: TestClient, nombre: str, workflow: str) -> Response:
    return _crear(cliente, _cuerpo(nombre, _workflow(cliente, workflow)["id"]))


@when(parsers.parse('creo la tarea "{nombre}" sin workflow'), target_fixture="respuesta")
def crear_sin_workflow(cliente: TestClient, nombre: str) -> Response:
    return _crear(cliente, _cuerpo(nombre))


@when(parsers.parse('creo una oportunidad "{nombre}" sin workflow'), target_fixture="respuesta")
def crear_oportunidad_sin_workflow(cliente: TestClient, nombre: str) -> Response:
    return _crear(cliente, _cuerpo(nombre, oportunidad=True))


@when(
    parsers.parse('creo una oportunidad "{nombre}" con el workflow "{workflow}"'),
    target_fixture="respuesta",
)
def crear_oportunidad_con_workflow(cliente: TestClient, nombre: str, workflow: str) -> Response:
    return _crear(cliente, _cuerpo(nombre, _workflow(cliente, workflow)["id"], oportunidad=True))


@when(parsers.parse('edito "{nombre}" con el workflow "{workflow}"'), target_fixture="respuesta")
def editar_con_workflow(cliente: TestClient, nombre: str, workflow: str) -> Response:
    return _editar(cliente, nombre, _cuerpo(nombre, _workflow(cliente, workflow)["id"]))


@when(parsers.parse('edito "{nombre}" sin workflow'), target_fixture="respuesta")
def editar_sin_workflow(cliente: TestClient, nombre: str) -> Response:
    return _editar(cliente, nombre, _cuerpo(nombre))


@when(parsers.parse('edito "{nombre}" sin el campo workflow_id'), target_fixture="respuesta")
def editar_sin_campo(cliente: TestClient, nombre: str) -> Response:
    return _editar(cliente, nombre, {**_DATOS, "nombre": nombre})


@when(parsers.parse('edito "{nombre}" como oportunidad sin workflow'), target_fixture="respuesta")
def editar_como_oportunidad(cliente: TestClient, nombre: str) -> Response:
    return _editar(cliente, nombre, _cuerpo(nombre, oportunidad=True))


@when(
    parsers.parse("intento {operacion} con un workflow que no existe"), target_fixture="respuesta"
)
def operar_con_workflow_inexistente(cliente: TestClient, operacion: str) -> Response:
    if operacion == "crear una tarea":
        return cliente.post(_TAREAS, json=_cuerpo("Otra", _ID_INEXISTENTE))
    nombre = operacion.removeprefix("editar ").strip('"')
    ruta = f"{_TAREAS}/{_tarea(cliente, nombre)['id']}"
    return cliente.put(ruta, json=_cuerpo(nombre, _ID_INEXISTENTE))


@when(
    parsers.parse("intento crear una tarea con el workflow_id {valor}"),
    target_fixture="respuesta",
)
def crear_con_workflow_id_invalido(cliente: TestClient, valor: str) -> Response:
    return cliente.post(
        _TAREAS, json={**_DATOS, "nombre": "Otra", "workflow_id": json.loads(valor)}
    )


@when(parsers.parse('elimino el workflow "{nombre}"'))
def eliminar_workflow(cliente: TestClient, nombre: str) -> None:
    ruta = f"{_WORKFLOWS}/{_workflow(cliente, nombre)['id']}"
    assert cliente.delete(ruta).status_code == 204


@when(parsers.parse('renombro el workflow "{actual}" a "{nuevo}"'))
def renombrar_workflow(cliente: TestClient, actual: str, nuevo: str) -> None:
    ruta = f"{_WORKFLOWS}/{_workflow(cliente, actual)['id']}"
    assert cliente.put(ruta, json={"nombre": nuevo}).status_code == 200


@when(parsers.parse('añado el paso "{paso}" al workflow "{nombre}"'))
def anadir_paso(cliente: TestClient, paso: str, nombre: str) -> None:
    ruta = f"{_WORKFLOWS}/{_workflow(cliente, nombre)['id']}/pasos"
    assert cliente.post(ruta, json={"nombre": paso}).status_code == 201


# --- Entonces ---------------------------------------------------------------


@then(
    parsers.parse(
        'la API responde {codigo:d} con la tarea "{nombre}", el workflow "{workflow}" y las '
        'subtareas "{subtareas}" pendientes'
    )
)
def responde_con_workflow_y_pendientes(
    cliente: TestClient,
    respuesta: Response,
    codigo: int,
    nombre: str,
    workflow: str,
    subtareas: str,
) -> None:
    assert respuesta.status_code == codigo
    tarea = respuesta.json()
    assert tarea["nombre"] == nombre
    _comprobar_workflow(tarea, workflow, cliente)
    assert _subtareas(tarea) == _pendientes(subtareas)
    assert _subtareas_guardadas(tarea["id"]) == _pendientes(subtareas)


@then(
    parsers.parse(
        'la API responde {codigo:d} con la tarea "{nombre}", el workflow "{workflow}" y las '
        'subtareas "{subtareas}"'
    )
)
def responde_con_workflow_y_subtareas(
    cliente: TestClient,
    respuesta: Response,
    codigo: int,
    nombre: str,
    workflow: str,
    subtareas: str,
) -> None:
    assert respuesta.status_code == codigo
    tarea = respuesta.json()
    assert tarea["nombre"] == nombre
    _comprobar_workflow(tarea, workflow, cliente)
    assert _subtareas(tarea) == _esperadas(subtareas)
    assert _subtareas_guardadas(tarea["id"]) == _esperadas(subtareas)


@then(
    parsers.parse(
        'la API responde {codigo:d} con la tarea "{nombre}", sin workflow y sin subtareas'
    )
)
def responde_sin_workflow_ni_subtareas(
    cliente: TestClient, respuesta: Response, codigo: int, nombre: str
) -> None:
    assert respuesta.status_code == codigo
    tarea = respuesta.json()
    assert tarea["nombre"] == nombre
    _comprobar_workflow(tarea, None, cliente)
    assert tarea["subtareas"] == []
    assert _subtareas_guardadas(tarea["id"]) == []


@then(
    parsers.parse(
        'la API responde {codigo:d} con la tarea "{nombre}", sin workflow y las subtareas '
        '"{subtareas}"'
    )
)
def responde_sin_workflow_con_subtareas(
    cliente: TestClient, respuesta: Response, codigo: int, nombre: str, subtareas: str
) -> None:
    assert respuesta.status_code == codigo
    tarea = respuesta.json()
    assert tarea["nombre"] == nombre
    _comprobar_workflow(tarea, None, cliente)
    assert _subtareas(tarea) == _esperadas(subtareas)


@then(
    parsers.parse(
        'al consultar las tareas "{nombre}" tiene el workflow "{workflow}" y las subtareas '
        '"{subtareas}" pendientes'
    )
)
def listado_con_workflow_y_pendientes(
    cliente: TestClient, nombre: str, workflow: str, subtareas: str
) -> None:
    tarea = _tarea(cliente, nombre)
    _comprobar_workflow(tarea, workflow, cliente)
    assert _subtareas(tarea) == _pendientes(subtareas)
    assert _subtareas_guardadas(tarea["id"]) == _pendientes(subtareas)


@then(
    parsers.parse(
        'al consultar las tareas "{nombre}" tiene el workflow "{workflow}" y las subtareas '
        '"{subtareas}"'
    )
)
def listado_con_workflow_y_subtareas(
    cliente: TestClient, nombre: str, workflow: str, subtareas: str
) -> None:
    tarea = _tarea(cliente, nombre)
    _comprobar_workflow(tarea, workflow, cliente)
    assert _subtareas(tarea) == _esperadas(subtareas)
    assert _subtareas_guardadas(tarea["id"]) == _esperadas(subtareas)


@then(
    parsers.parse(
        'al consultar las tareas "{nombre}" tiene el workflow "{workflow}" y ninguna subtarea'
    )
)
def listado_con_workflow_sin_subtareas(cliente: TestClient, nombre: str, workflow: str) -> None:
    tarea = _tarea(cliente, nombre)
    _comprobar_workflow(tarea, workflow, cliente)
    assert tarea["subtareas"] == []
    assert _subtareas_guardadas(tarea["id"]) == []


@then(parsers.parse('al consultar las tareas "{nombre}" no tiene workflow ni subtareas'))
def listado_sin_workflow_ni_subtareas(cliente: TestClient, nombre: str) -> None:
    tarea = _tarea(cliente, nombre)
    _comprobar_workflow(tarea, None, cliente)
    assert tarea["subtareas"] == []
    assert _subtareas_guardadas(tarea["id"]) == []


@then(
    parsers.parse(
        'al consultar las tareas "{nombre}" no tiene workflow y tiene las subtareas '
        '"{subtareas}" pendientes'
    )
)
def listado_sin_workflow_con_pendientes(cliente: TestClient, nombre: str, subtareas: str) -> None:
    tarea = _tarea(cliente, nombre)
    _comprobar_workflow(tarea, None, cliente)
    assert _subtareas(tarea) == _pendientes(subtareas)
    assert _subtareas_guardadas(tarea["id"]) == _pendientes(subtareas)


@then("la API responde 422 porque el workflow no existe")
def responde_422_workflow_inexistente(respuesta: Response) -> None:
    assert respuesta.status_code == 422
    assert respuesta.json() == {
        "detail": [
            {
                "type": "value_error",
                "loc": ["body", "workflow_id"],
                "msg": f"No existe el workflow con id {_ID_INEXISTENTE}",
                "input": _ID_INEXISTENTE,
            }
        ]
    }


@then("la API rechaza la operación por datos inválidos")
def la_api_rechaza_por_datos_invalidos(respuesta: Response) -> None:
    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]


@then(parsers.parse("hay {total:d} tareas"))
def hay_tareas(total: int) -> None:
    sesion = FabricaSesiones()
    try:
        assert sesion.scalar(select(func.count()).select_from(TareaModelo)) == total
    finally:
        sesion.close()
