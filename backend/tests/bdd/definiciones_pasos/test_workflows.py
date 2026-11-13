from fastapi.testclient import TestClient
from httpx import Response
from pytest_bdd import given, parsers, scenarios, then, when
from sqlalchemy import select

from gestor_tareas.infraestructura.persistencia.modelos import PasoWorkflowModelo, WorkflowModelo
from gestor_tareas.infraestructura.persistencia.sesion import FabricaSesiones

scenarios("workflows.feature")

_RUTA = "/api/v1/workflows"
_ID_INEXISTENTE = 999999

_NOMBRES_INVALIDOS = {
    "vacío": {"nombre": ""},
    "solo de espacios": {"nombre": "   "},
    "con espacio duro": {"nombre": "  "},
    "de 51 caracteres": {"nombre": "n" * 51},
    "ausente": {},
    "que no es texto": {"nombre": 5},
}

_NOMBRE_DE_50_CON_TILDES = "Ñandú camión " + "á" * 37


def _lista(texto: str) -> list[str]:
    """Convierte "a, b" en ["a", "b"]; el texto vacío es la lista vacía."""
    return texto.split(", ") if texto else []


def _workflows(cliente: TestClient) -> list[dict]:
    respuesta = cliente.get(_RUTA)
    assert respuesta.status_code == 200
    return respuesta.json()


def _workflow(cliente: TestClient, nombre: str) -> dict:
    return next(w for w in _workflows(cliente) if w["nombre"] == nombre)


def _id_workflow(cliente: TestClient, nombre: str) -> int:
    return _workflow(cliente, nombre)["id"]


def _id_paso(cliente: TestClient, workflow: str, paso: str) -> int:
    return next(p["id"] for p in _workflow(cliente, workflow)["pasos"] if p["nombre"] == paso)


def _ruta_pasos(cliente: TestClient, workflow: str) -> str:
    return f"{_RUTA}/{_id_workflow(cliente, workflow)}/pasos"


def _workflows_guardados() -> list[str]:
    sesion = FabricaSesiones()
    try:
        return sorted(sesion.scalars(select(WorkflowModelo.nombre)), key=str.casefold)
    finally:
        sesion.close()


def _pasos_guardados(id_workflow: int) -> list[tuple[int, str]]:
    """(numero, nombre) de los pasos guardados del workflow, en orden de número."""
    sesion = FabricaSesiones()
    try:
        modelo = PasoWorkflowModelo
        consulta = (
            select(modelo.numero, modelo.nombre)
            .where(modelo.workflow_id == id_workflow)
            .order_by(modelo.numero)
        )
        return [(fila.numero, fila.nombre) for fila in sesion.execute(consulta)]
    finally:
        sesion.close()


def _comprobar_pasos(pasos: list[dict], nombres: list[str]) -> None:
    assert [(p["numero"], p["nombre"]) for p in pasos] == list(enumerate(nombres, start=1))
    assert all(set(p) == {"id", "numero", "nombre", "comentarios"} for p in pasos)
    assert len({p["id"] for p in pasos}) == len(pasos)


def _comprobar_workflow(cuerpo: dict, nombre: str, pasos: list[str]) -> None:
    assert set(cuerpo) == {"id", "nombre", "pasos"}
    assert isinstance(cuerpo["id"], int)
    assert cuerpo["nombre"] == nombre
    _comprobar_pasos(cuerpo["pasos"], pasos)


def _crear_workflow(cliente: TestClient, nombre: str) -> dict:
    respuesta = cliente.post(_RUTA, json={"nombre": nombre})
    assert respuesta.status_code == 201
    return respuesta.json()


@given(parsers.parse('que existen los workflows "{nombres}"'))
def existen_los_workflows(cliente: TestClient, nombres: str) -> None:
    for nombre in _lista(nombres):
        _crear_workflow(cliente, nombre)


@given(parsers.parse('que el workflow "{nombre}" tiene los pasos "{pasos}"'))
def workflow_con_pasos(cliente: TestClient, nombre: str, pasos: str) -> None:
    id_workflow = _crear_workflow(cliente, nombre)["id"]
    for paso in _lista(pasos):
        respuesta = cliente.post(f"{_RUTA}/{id_workflow}/pasos", json={"nombre": paso})
        assert respuesta.status_code == 201


@when("consulto los workflows", target_fixture="respuesta")
def consultar_workflows(cliente: TestClient) -> Response:
    return cliente.get(_RUTA)


@when(parsers.parse('creo el workflow "{nombre}"'), target_fixture="respuesta")
def crear_workflow(cliente: TestClient, nombre: str) -> Response:
    return cliente.post(_RUTA, json={"nombre": nombre})


@when(parsers.parse("intento crear un workflow con un nombre {nombre}"), target_fixture="respuesta")
def crear_workflow_invalido(cliente: TestClient, nombre: str) -> Response:
    return cliente.post(_RUTA, json=_NOMBRES_INVALIDOS[nombre])


@when("creo un workflow con un nombre de 50 caracteres con tildes", target_fixture="respuesta")
def crear_workflow_de_50(cliente: TestClient) -> Response:
    return cliente.post(_RUTA, json={"nombre": _NOMBRE_DE_50_CON_TILDES})


@when(parsers.parse('renombro el workflow "{actual}" a "{nuevo}"'), target_fixture="respuesta")
def renombrar_workflow(cliente: TestClient, actual: str, nuevo: str) -> Response:
    return cliente.put(f"{_RUTA}/{_id_workflow(cliente, actual)}", json={"nombre": nuevo})


@when(parsers.parse('elimino el workflow "{nombre}"'), target_fixture="respuesta")
def eliminar_workflow(cliente: TestClient, nombre: str) -> Response:
    workflow = _workflow(cliente, nombre)
    ids_pasos = [p["id"] for p in workflow["pasos"]]
    respuesta = cliente.delete(f"{_RUTA}/{workflow['id']}")
    respuesta.ids_pasos_eliminados = ids_pasos  # type: ignore[attr-defined]
    return respuesta


@when(parsers.parse("intento {operacion} un workflow que no existe"), target_fixture="respuesta")
def operar_workflow_inexistente(cliente: TestClient, operacion: str) -> Response:
    ruta = f"{_RUTA}/{_ID_INEXISTENTE}"
    if operacion == "renombrar":
        return cliente.put(ruta, json={"nombre": "Otro"})
    if operacion == "eliminar":
        return cliente.delete(ruta)
    if operacion == "añadir un paso a":
        return cliente.post(f"{ruta}/pasos", json={"nombre": "Paso"})
    return cliente.put(f"{ruta}/orden", json={"ids": []})


@when(
    parsers.parse('añado el paso "{nombre}" al workflow "{workflow}"'), target_fixture="respuesta"
)
def anadir_paso(cliente: TestClient, nombre: str, workflow: str) -> Response:
    return cliente.post(_ruta_pasos(cliente, workflow), json={"nombre": nombre})


@when(
    parsers.parse('añado al workflow "{workflow}" un paso con un nombre de 50 caracteres'),
    target_fixture="respuesta",
)
def anadir_paso_de_50(cliente: TestClient, workflow: str) -> Response:
    return cliente.post(_ruta_pasos(cliente, workflow), json={"nombre": "n" * 50})


@when(
    parsers.parse('intento añadir al workflow "{workflow}" un paso con un nombre {nombre}'),
    target_fixture="respuesta",
)
def anadir_paso_invalido(cliente: TestClient, workflow: str, nombre: str) -> Response:
    return cliente.post(_ruta_pasos(cliente, workflow), json=_NOMBRES_INVALIDOS[nombre])


@when(
    parsers.parse('renombro el paso "{actual}" del workflow "{workflow}" a "{nuevo}"'),
    target_fixture="respuesta",
)
def renombrar_paso(cliente: TestClient, actual: str, workflow: str, nuevo: str) -> Response:
    ruta = f"{_ruta_pasos(cliente, workflow)}/{_id_paso(cliente, workflow, actual)}"
    return cliente.put(ruta, json={"nombre": nuevo})


@when(
    parsers.parse(
        'intento renombrar el paso "{actual}" del workflow "{workflow}" con un nombre {nombre}'
    ),
    target_fixture="respuesta",
)
def renombrar_paso_invalido(
    cliente: TestClient, actual: str, workflow: str, nombre: str
) -> Response:
    ruta = f"{_ruta_pasos(cliente, workflow)}/{_id_paso(cliente, workflow, actual)}"
    return cliente.put(ruta, json=_NOMBRES_INVALIDOS[nombre])


@when(
    parsers.parse('elimino el paso "{nombre}" del workflow "{workflow}"'),
    target_fixture="respuesta",
)
def eliminar_paso(cliente: TestClient, nombre: str, workflow: str) -> Response:
    return cliente.delete(f"{_ruta_pasos(cliente, workflow)}/{_id_paso(cliente, workflow, nombre)}")


@when(
    parsers.parse('reordeno los pasos del workflow "{workflow}" como "{nombres}"'),
    target_fixture="respuesta",
)
def reordenar_pasos(cliente: TestClient, workflow: str, nombres: str) -> Response:
    ids = [_id_paso(cliente, workflow, nombre) for nombre in _lista(nombres)]
    return cliente.put(f"{_RUTA}/{_id_workflow(cliente, workflow)}/orden", json={"ids": ids})


@when(
    parsers.parse('reordeno los pasos del workflow "{workflow}" con un orden vacío'),
    target_fixture="respuesta",
)
def reordenar_sin_pasos(cliente: TestClient, workflow: str) -> Response:
    return cliente.put(f"{_RUTA}/{_id_workflow(cliente, workflow)}/orden", json={"ids": []})


@when(
    parsers.parse('intento reordenar los pasos del workflow "{workflow}" con un orden {orden}'),
    target_fixture="respuesta",
)
def reordenar_pasos_invalido(cliente: TestClient, workflow: str, orden: str) -> Response:
    ids = [p["id"] for p in _workflow(cliente, workflow)["pasos"]]
    otros = [p["id"] for w in _workflows(cliente) if w["nombre"] != workflow for p in w["pasos"]]
    cuerpos = {
        "con un paso repetido": {"ids": [*ids, ids[0]]},
        "al que le falta un paso": {"ids": ids[1:]},
        "con un paso que no existe": {"ids": [*ids, _ID_INEXISTENTE]},
        "con un paso de otro workflow": {"ids": [*ids, otros[0]]},
        "vacío": {"ids": []},
        "con ids que no son enteros": {"ids": [str(i) for i in ids]},
        "ausente": {},
    }
    return cliente.put(f"{_RUTA}/{_id_workflow(cliente, workflow)}/orden", json=cuerpos[orden])


@when(
    parsers.parse('intento {operacion} el paso "{paso}" en el workflow "{workflow}"'),
    target_fixture="respuesta",
)
def operar_paso_ajeno(cliente: TestClient, operacion: str, paso: str, workflow: str) -> Response:
    if paso == "inexistente":
        id_paso = _ID_INEXISTENTE
    else:
        id_paso = next(
            p["id"] for w in _workflows(cliente) for p in w["pasos"] if p["nombre"] == paso
        )
    ruta = f"{_ruta_pasos(cliente, workflow)}/{id_paso}"
    respuesta = (
        cliente.put(ruta, json={"nombre": "Otro"})
        if operacion == "renombrar"
        else cliente.delete(ruta)
    )
    respuesta.id_paso = id_paso  # type: ignore[attr-defined]
    return respuesta


@when(
    "consulto la ruta antigua de los pasos del workflow de las oportunidades",
    target_fixture="respuesta",
)
def consultar_ruta_antigua(cliente: TestClient) -> Response:
    return cliente.get("/api/v1/workflow-oportunidades/pasos")


@then(parsers.parse('la API devuelve los workflows "{nombres}"'))
def la_api_devuelve_los_workflows(respuesta: Response, nombres: str) -> None:
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert [w["nombre"] for w in cuerpo] == _lista(nombres)
    for workflow in cuerpo:
        _comprobar_workflow(workflow, workflow["nombre"], [])


@then(parsers.parse('la API responde que el workflow "{nombre}" se ha creado sin pasos'))
def el_workflow_se_ha_creado(respuesta: Response, nombre: str) -> None:
    assert respuesta.status_code == 201
    _comprobar_workflow(respuesta.json(), nombre, [])


@then("la API responde que el workflow se ha creado con ese nombre")
def el_workflow_de_50_se_ha_creado(respuesta: Response) -> None:
    el_workflow_se_ha_creado(respuesta, _NOMBRE_DE_50_CON_TILDES)
    assert _workflows_guardados() == [_NOMBRE_DE_50_CON_TILDES]


@then(parsers.parse('se guardan los workflows "{nombres}"'))
def se_guardan_los_workflows(nombres: str) -> None:
    assert _workflows_guardados() == _lista(nombres)


@then("no se guarda ningún workflow")
def no_se_guarda_ningun_workflow() -> None:
    assert _workflows_guardados() == []


@then(parsers.parse('la API responde que ya existe un workflow llamado "{nombre}"'))
def ya_existe_el_workflow(respuesta: Response, nombre: str) -> None:
    assert respuesta.status_code == 409
    assert respuesta.json() == {"detalle": f"Ya existe un workflow llamado «{nombre}»"}


@then(parsers.parse('la API responde con el workflow "{nombre}" y los pasos "{pasos}"'))
def la_api_responde_con_el_workflow(respuesta: Response, nombre: str, pasos: str) -> None:
    assert respuesta.status_code == 200
    _comprobar_workflow(respuesta.json(), nombre, _lista(pasos))


@then(parsers.parse('la API responde con el workflow "{nombre}" sin pasos'))
def la_api_responde_con_el_workflow_sin_pasos(respuesta: Response, nombre: str) -> None:
    la_api_responde_con_el_workflow(respuesta, nombre, "")


@then("la API responde que se ha eliminado")
def se_ha_eliminado(respuesta: Response) -> None:
    assert respuesta.status_code == 204
    assert respuesta.content == b""


@then("no queda ningún paso del workflow eliminado")
def no_quedan_pasos_del_eliminado(respuesta: Response) -> None:
    sesion = FabricaSesiones()
    try:
        ids = respuesta.ids_pasos_eliminados  # type: ignore[attr-defined]
        consulta = select(PasoWorkflowModelo.id).where(PasoWorkflowModelo.id.in_(ids))
        assert ids and list(sesion.scalars(consulta)) == []
    finally:
        sesion.close()


@then("la API responde que el workflow no existe")
def el_workflow_no_existe(respuesta: Response) -> None:
    # El cuerpo distingue el 404 de dominio del 404 de "ruta no encontrada".
    assert respuesta.status_code == 404
    assert respuesta.json() == {"detalle": f"No existe el workflow con id {_ID_INEXISTENTE}"}


@then(parsers.parse('la API responde 201 con el workflow "{nombre}" y los pasos "{pasos}"'))
def responde_201_con_el_workflow(respuesta: Response, nombre: str, pasos: str) -> None:
    assert respuesta.status_code == 201
    _comprobar_workflow(respuesta.json(), nombre, _lista(pasos))


@then(parsers.parse('la API responde 201 con el workflow "{nombre}" y un paso de 50 caracteres'))
def responde_201_con_un_paso_de_50(respuesta: Response, nombre: str) -> None:
    responde_201_con_el_workflow(respuesta, nombre, "n" * 50)
    assert _pasos_guardados(respuesta.json()["id"]) == [(1, "n" * 50)]


@then("la API rechaza la operación por datos inválidos")
def la_api_rechaza_por_datos_invalidos(respuesta: Response) -> None:
    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]


@then(parsers.parse('la API responde que el paso "{paso}" no existe en el workflow "{workflow}"'))
def el_paso_no_existe(cliente: TestClient, respuesta: Response, paso: str, workflow: str) -> None:
    assert respuesta.status_code == 404
    id_paso = respuesta.id_paso  # type: ignore[attr-defined]
    assert respuesta.json() == {
        "detalle": (
            f"No existe el paso con id {id_paso} en el workflow con id "
            f"{_id_workflow(cliente, workflow)}"
        )
    }


@then(parsers.parse('el workflow "{nombre}" guarda los pasos "{pasos}"'))
def el_workflow_guarda_los_pasos(cliente: TestClient, nombre: str, pasos: str) -> None:
    esperados = _lista(pasos)
    workflow = _workflow(cliente, nombre)
    assert _pasos_guardados(workflow["id"]) == list(enumerate(esperados, start=1))
    _comprobar_pasos(workflow["pasos"], esperados)


@then("la API responde que la ruta no existe")
def la_ruta_no_existe(respuesta: Response) -> None:
    assert respuesta.status_code == 404
    assert respuesta.json() == {"detail": "Not Found"}
