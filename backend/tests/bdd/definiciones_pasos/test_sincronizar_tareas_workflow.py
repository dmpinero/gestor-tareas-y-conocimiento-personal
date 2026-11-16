from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from httpx import Response
from pytest_bdd import given, parsers, scenarios, then, when
from sqlalchemy import select

from gestor_tareas.infraestructura.persistencia.modelos import SubtareaModelo
from gestor_tareas.infraestructura.persistencia.sesion import FabricaSesiones

scenarios("sincronizar_tareas_workflow.feature")

_TAREAS = "/api/v1/tareas"
_WORKFLOWS = "/api/v1/workflows"
_ID_INEXISTENTE = 999999
_DATOS = {"descripcion": "d", "fecha_creacion": "2026-11-10T09:00:00"}


def _lista(texto: str, separador: str = ", ") -> list[str]:
    return texto.split(separador) if texto else []


def _workflow(cliente: TestClient, nombre: str) -> dict:
    respuesta = cliente.get(_WORKFLOWS)
    assert respuesta.status_code == 200
    return next(w for w in respuesta.json() if w["nombre"] == nombre)


def _paso(cliente: TestClient, workflow: str, paso: str) -> str:
    datos = _workflow(cliente, workflow)
    id_paso = next(p["id"] for p in datos["pasos"] if p["nombre"] == paso)
    return f"{_WORKFLOWS}/{datos['id']}/pasos/{id_paso}"


def _tarea(cliente: TestClient, nombre: str) -> dict:
    respuesta = cliente.get(_TAREAS)
    assert respuesta.status_code == 200
    return next(t for t in respuesta.json() if t["nombre"] == nombre)


def _ruta_subtarea(cliente: TestClient, tarea: str, subtarea: str) -> str:
    datos = _tarea(cliente, tarea)
    id_subtarea = next(s["id"] for s in datos["subtareas"] if s["nombre"] == subtarea)
    return f"{_TAREAS}/{datos['id']}/subtareas/{id_subtarea}"


def _ruta_sincronizacion(cliente: TestClient, workflow: str) -> str:
    return f"{_WORKFLOWS}/{_workflow(cliente, workflow)['id']}/sincronizacion"


def _pasos_guardados(id_tarea: int) -> dict[str, int | None]:
    sesion = FabricaSesiones()
    try:
        consulta = select(SubtareaModelo.nombre, SubtareaModelo.paso_id).where(
            SubtareaModelo.tarea_id == id_tarea
        )
        return {fila.nombre: fila.paso_id for fila in sesion.execute(consulta)}
    finally:
        sesion.close()


def _cambios_esperados(cliente: TestClient, texto: str) -> dict:
    """Convierte "Tarea: añadir A, B; renombrar X > Y" en la respuesta esperada."""
    tareas = []
    for bloque in _lista(texto, " | "):
        nombre, detalle = bloque.split(": ", 1)
        datos = _tarea(cliente, nombre)
        anadir: list[str] = []
        renombrar = []
        for parte in _lista(detalle, "; "):
            if parte.startswith("añadir "):
                anadir = _lista(parte.removeprefix("añadir "))
            else:
                for par in _lista(parte.removeprefix("renombrar "), ", "):
                    actual, nuevo = par.split(" > ")
                    # Antes de sincronizar se busca por su nombre actual, y después
                    # por el nuevo.
                    id_subtarea = next(
                        s["id"] for s in datos["subtareas"] if s["nombre"] in (actual, nuevo)
                    )
                    renombrar.append(
                        {"id": id_subtarea, "nombre_actual": actual, "nombre_nuevo": nuevo}
                    )
        tareas.append(
            {
                "id": datos["id"],
                "nombre": nombre,
                "subtareas_a_anadir": anadir,
                "subtareas_a_renombrar": renombrar,
            }
        )
    return {"tareas": tareas}


# --- Dado -------------------------------------------------------------------


@given(parsers.parse('que el workflow "{nombre}" tiene los pasos "{pasos}"'))
def workflow_con_pasos(cliente: TestClient, nombre: str, pasos: str) -> None:
    respuesta = cliente.post(_WORKFLOWS, json={"nombre": nombre})
    assert respuesta.status_code == 201
    for paso in _lista(pasos):
        ruta = f"{_WORKFLOWS}/{respuesta.json()['id']}/pasos"
        assert cliente.post(ruta, json={"nombre": paso}).status_code == 201


@given(parsers.parse('que existe la tarea "{nombre}" con el workflow "{workflow}"'))
def existe_la_tarea(cliente: TestClient, nombre: str, workflow: str) -> None:
    cuerpo = {**_DATOS, "nombre": nombre, "workflow_id": _workflow(cliente, workflow)["id"]}
    assert cliente.post(_TAREAS, json=cuerpo).status_code == 201


@given(parsers.parse('que la tarea "{nombre}" está completada'))
def tarea_completada(cliente: TestClient, nombre: str) -> None:
    ruta = f"{_TAREAS}/{_tarea(cliente, nombre)['id']}/completada"
    assert cliente.patch(ruta, json={"completada": True}).status_code == 200


@given(parsers.parse('que la tarea "{tarea}" tiene la subtarea "{subtarea}" añadida a mano'))
def subtarea_a_mano(cliente: TestClient, tarea: str, subtarea: str) -> None:
    ruta = f"{_TAREAS}/{_tarea(cliente, tarea)['id']}/subtareas"
    assert cliente.post(ruta, json={"nombre": subtarea}).status_code == 201


@given(parsers.parse('la subtarea "{subtarea}" de "{tarea}" está resuelta'))
def subtarea_resuelta(cliente: TestClient, subtarea: str, tarea: str) -> None:
    ruta = f"{_ruta_subtarea(cliente, tarea, subtarea)}/resuelta"
    assert cliente.patch(ruta, json={"resuelta": True}).status_code == 200


@given(parsers.parse('que añado el paso "{paso}" al workflow "{nombre}"'))
def anadir_paso(cliente: TestClient, paso: str, nombre: str) -> None:
    ruta = f"{_WORKFLOWS}/{_workflow(cliente, nombre)['id']}/pasos"
    assert cliente.post(ruta, json={"nombre": paso}).status_code == 201


@given(parsers.parse('que renombro el paso "{paso}" del workflow "{workflow}" a "{nuevo}"'))
def renombrar_paso(cliente: TestClient, paso: str, workflow: str, nuevo: str) -> None:
    assert cliente.put(_paso(cliente, workflow, paso), json={"nombre": nuevo}).status_code == 200


@given(parsers.parse('que elimino el paso "{paso}" del workflow "{workflow}"'))
def eliminar_paso(cliente: TestClient, paso: str, workflow: str) -> None:
    assert cliente.delete(_paso(cliente, workflow, paso)).status_code == 200


@given(parsers.parse('que reordeno los pasos del workflow "{nombre}" como "{pasos}"'))
def reordenar(cliente: TestClient, nombre: str, pasos: str) -> None:
    workflow = _workflow(cliente, nombre)
    por_nombre = {p["nombre"]: p["id"] for p in workflow["pasos"]}
    ruta = f"{_WORKFLOWS}/{workflow['id']}/orden"
    ids = [por_nombre[p] for p in _lista(pasos)]
    assert cliente.put(ruta, json={"ids": ids}).status_code == 200


@given(parsers.parse('que el paso "{paso}" de "{workflow}" tiene el comentario "{texto}"'))
def comentario_de_paso(cliente: TestClient, paso: str, workflow: str, texto: str) -> None:
    ruta = f"{_paso(cliente, workflow, paso)}/comentarios"
    assert cliente.post(ruta, json={"texto": texto}).status_code == 201


@given(parsers.parse('que sincronizo las tareas del workflow "{nombre}"'))
def sincronizar_antes(cliente: TestClient, nombre: str) -> None:
    assert cliente.post(_ruta_sincronizacion(cliente, nombre)).status_code == 200


# --- Cuando -----------------------------------------------------------------


@when(
    parsers.parse('consulto los cambios pendientes del workflow "{nombre}"'),
    target_fixture="respuesta",
)
def consultar(cliente: TestClient, nombre: str) -> Response:
    return cliente.get(_ruta_sincronizacion(cliente, nombre))


@when(parsers.parse('sincronizo las tareas del workflow "{nombre}"'), target_fixture="respuesta")
def sincronizar(cliente: TestClient, nombre: str) -> dict:
    antes = datetime.now(UTC).replace(microsecond=0, tzinfo=None)
    respuesta = cliente.post(_ruta_sincronizacion(cliente, nombre))
    despues = datetime.now(UTC).replace(tzinfo=None) + timedelta(seconds=1)
    return {"respuesta": respuesta, "antes": antes, "despues": despues}


@when(
    parsers.parse("{operacion} de un workflow que no existe"),
    target_fixture="respuesta",
)
def operar_con_workflow_inexistente(cliente: TestClient, operacion: str) -> Response:
    ruta = f"{_WORKFLOWS}/{_ID_INEXISTENTE}/sincronizacion"
    if operacion == "consulto los cambios":
        return cliente.get(ruta)
    return cliente.post(ruta)


# --- Entonces ---------------------------------------------------------------


def _respuesta(respuesta: Response | dict) -> Response:
    return respuesta["respuesta"] if isinstance(respuesta, dict) else respuesta


@then(parsers.parse('la API responde 200 con los cambios "{cambios}"'))
def responde_con_cambios(cliente: TestClient, respuesta: Response | dict, cambios: str) -> None:
    obtenida = _respuesta(respuesta)
    assert obtenida.status_code == 200, obtenida.text
    esperada = _cambios_esperados(cliente, cambios)
    assert obtenida.json() == esperada


@then("la API responde 200 sin cambios")
def responde_sin_cambios(respuesta: Response | dict) -> None:
    obtenida = _respuesta(respuesta)
    assert obtenida.status_code == 200
    assert obtenida.json() == {"tareas": []}


@then(parsers.parse('"{tarea}" tiene las subtareas "{subtareas}"'))
def tiene_las_subtareas(cliente: TestClient, tarea: str, subtareas: str) -> None:
    """Las subtareas en el orden en que se muestran: "A, B" compara los nombres y
    "A: resuelta; B: pendiente" también su estado."""
    obtenidas = _tarea(cliente, tarea)["subtareas"]
    if ": " not in subtareas:
        assert [s["nombre"] for s in obtenidas] == _lista(subtareas)
        return
    esperadas = [(n, e == "resuelta") for n, e in (x.split(": ") for x in _lista(subtareas, "; "))]
    assert [(s["nombre"], s["resuelta"]) for s in obtenidas] == esperadas


@then(
    parsers.parse(
        'las subtareas "{subtareas}" de "{tarea}" están vinculadas a sus pasos del workflow '
        '"{workflow}"'
    )
)
def vinculadas(cliente: TestClient, subtareas: str, tarea: str, workflow: str) -> None:
    pasos = {p["nombre"]: p["id"] for p in _workflow(cliente, workflow)["pasos"]}
    guardados = _pasos_guardados(_tarea(cliente, tarea)["id"])
    assert {n: guardados[n] for n in _lista(subtareas)} == {n: pasos[n] for n in _lista(subtareas)}


@then(parsers.parse('la subtarea "{subtarea}" de "{tarea}" no está vinculada a ningún paso'))
def sin_vinculo(cliente: TestClient, subtarea: str, tarea: str) -> None:
    assert _pasos_guardados(_tarea(cliente, tarea)["id"])[subtarea] is None


@then(
    parsers.parse(
        'la subtarea "{subtarea}" de "{tarea}" no tiene persona ni prioridad y tiene los '
        'comentarios copiados "{textos}"'
    )
)
def subtarea_nueva_con_comentarios(
    cliente: TestClient, respuesta: dict, subtarea: str, tarea: str, textos: str
) -> None:
    datos = next(s for s in _tarea(cliente, tarea)["subtareas"] if s["nombre"] == subtarea)
    assert datos["asignado"] is None and datos["prioridad"] is None
    assert datos["resuelta"] is False
    comentarios = cliente.get(f"{_ruta_subtarea(cliente, tarea, subtarea)}/comentarios").json()
    assert [c["texto"] for c in comentarios] == _lista(textos, "; ")
    assert all(c["editado"] is None for c in comentarios)
    for comentario in comentarios:
        creado = datetime.fromisoformat(comentario["creado"]).replace(tzinfo=None)
        assert respuesta["antes"] <= creado <= respuesta["despues"]


@then(parsers.parse('al consultar los cambios pendientes del workflow "{nombre}" no hay ninguno'))
def sin_cambios_pendientes(cliente: TestClient, nombre: str) -> None:
    respuesta = cliente.get(_ruta_sincronizacion(cliente, nombre))
    assert respuesta.status_code == 200
    assert respuesta.json() == {"tareas": []}


@then("la API responde 404 porque el workflow no existe")
def responde_404(respuesta: Response) -> None:
    assert respuesta.status_code == 404
    assert respuesta.json() == {"detalle": f"No existe el workflow con id {_ID_INEXISTENTE}"}
