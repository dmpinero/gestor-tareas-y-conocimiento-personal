import json
import re
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from pytest_bdd import given, parsers, scenarios, then, when
from sqlalchemy import select

from gestor_tareas.infraestructura.persistencia.modelos import (
    ComentarioPasoModelo,
    ComentarioSubtareaModelo,
)
from gestor_tareas.infraestructura.persistencia.sesion import FabricaSesiones
from tests.bdd.comentarios_html import html_guardado

scenarios("comentarios_pasos_workflow.feature")

_TAREAS = "/api/v1/tareas"
_WORKFLOWS = "/api/v1/workflows"

_DATOS = {"descripcion": "d", "fecha_creacion": "2026-11-10T09:00:00"}

# "creado" y "editado" en UTC con precisión de segundos y una "Z" final.
_INSTANTE_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

_CLAVES = {"id", "texto", "creado", "editado"}


class _Grupos(dict):
    def __missing__(self, clave: str) -> str:
        if clave == "n" or clave.startswith("id_"):
            return rf"(?P<{clave}>\d+)"
        if clave == "accion":
            return r"(?P<accion>listar|comentar|editar|eliminar)"
        return rf'"(?P<{clave}>[^"]*)"'


def _patron(texto: str) -> parsers.re:
    """Patrón de un paso: cada ``{nombre}`` es un texto entre comillas, ``{n}`` e
    ``{id_...}`` números y ``{accion}`` una de las operaciones con los comentarios."""
    return parsers.re("^" + texto.format_map(_Grupos()) + "$")


def _texto(texto: str) -> str:
    """Los "\\n" escritos en el escenario son saltos de línea."""
    return texto.replace("\\n", "\n")


def _lista(texto: str) -> list[str]:
    return [_texto(t) for t in texto.split("; ")] if texto else []


def _guardado(texto: str) -> str:
    """El HTML guardado para un comentario escrito en el escenario."""
    return html_guardado(_texto(texto))


def _guardados(textos: str) -> list[str]:
    return [html_guardado(t) for t in _lista(textos)]


def _workflow(cliente: TestClient, nombre: str) -> dict:
    respuesta = cliente.get(_WORKFLOWS)
    assert respuesta.status_code == 200
    return next(w for w in respuesta.json() if w["nombre"] == nombre)


def _paso(cliente: TestClient, workflow: str, paso: str) -> dict:
    return next(p for p in _workflow(cliente, workflow)["pasos"] if p["nombre"] == paso)


def _ruta(id_workflow: int, id_paso: int, id_comentario: int | None = None) -> str:
    ruta = f"{_WORKFLOWS}/{id_workflow}/pasos/{id_paso}/comentarios"
    return ruta if id_comentario is None else f"{ruta}/{id_comentario}"


def _ruta_de(cliente: TestClient, workflow: str, paso: str) -> str:
    return _ruta(_workflow(cliente, workflow)["id"], _paso(cliente, workflow, paso)["id"])


def _listar(cliente: TestClient, ruta: str) -> list[dict]:
    respuesta = cliente.get(ruta)
    assert respuesta.status_code == 200
    assert all(set(c) == _CLAVES for c in respuesta.json())
    return respuesta.json()


def _id_en(cliente: TestClient, ruta: str, texto: str) -> int:
    return next(c["id"] for c in _listar(cliente, ruta) if c["texto"] == _guardado(texto))


def _tarea(cliente: TestClient, nombre: str) -> dict:
    respuesta = cliente.get(_TAREAS)
    assert respuesta.status_code == 200
    return next(t for t in respuesta.json() if t["nombre"] == nombre)


def _ruta_subtarea(cliente: TestClient, tarea: str, subtarea: str) -> str:
    datos = _tarea(cliente, tarea)
    id_subtarea = next(s["id"] for s in datos["subtareas"] if s["nombre"] == subtarea)
    return f"{_TAREAS}/{datos['id']}/subtareas/{id_subtarea}/comentarios"


def _cuerpo(cuerpo: str) -> dict:
    datos = json.loads(cuerpo)
    if datos.get("texto") == "<501 caracteres>":
        datos["texto"] = "a" * 501
    return datos


def _instante(texto: str) -> datetime:
    assert _INSTANTE_UTC.fullmatch(texto), texto
    return datetime.fromisoformat(texto)


def _operar(cliente: TestClient, accion: str, id_workflow: int, id_paso: int, id_c: int):
    if accion == "listar":
        return cliente.get(_ruta(id_workflow, id_paso))
    if accion == "comentar":
        return cliente.post(_ruta(id_workflow, id_paso), json={"texto": "Otro"})
    if accion == "editar":
        return cliente.put(_ruta(id_workflow, id_paso, id_c), json={"texto": "Otro"})
    return cliente.delete(_ruta(id_workflow, id_paso, id_c))


def _comprobar_404(respuesta: Response, detalle: str) -> None:
    # El cuerpo distingue el 404 de dominio del 404 de "ruta no encontrada".
    assert respuesta.status_code == 404
    assert respuesta.json() == {"detalle": detalle}


def _textos_en_bd(modelo) -> list[str]:
    sesion = FabricaSesiones()
    try:
        return sorted(sesion.scalars(select(modelo.texto)).all())
    finally:
        sesion.close()


@pytest.fixture
def originales() -> dict[int, dict]:
    """Comentarios dados de alta en los antecedentes, por id, tal como se crearon."""
    return {}


@pytest.fixture
def copia() -> dict[str, datetime]:
    """Instantes entre los que se ha hecho la última copia de comentarios."""
    return {}


# --- Antecedentes y preparación -------------------------------------------------------


@given(_patron("que el workflow {workflow} tiene los pasos {pasos}"))
def workflow_con_pasos(cliente: TestClient, workflow: str, pasos: str) -> None:
    respuesta = cliente.post(_WORKFLOWS, json={"nombre": workflow})
    assert respuesta.status_code == 201
    for paso in _lista(pasos):
        ruta = f"{_WORKFLOWS}/{respuesta.json()['id']}/pasos"
        assert cliente.post(ruta, json={"nombre": paso}).status_code == 201


@given(_patron("que el paso {paso} de {workflow} tiene los comentarios {textos}"))
def el_paso_tiene_comentarios(
    cliente: TestClient, originales: dict[int, dict], paso: str, workflow: str, textos: str
) -> None:
    for texto in _lista(textos):
        respuesta = cliente.post(_ruta_de(cliente, workflow, paso), json={"texto": texto})
        assert respuesta.status_code == 201
        originales[respuesta.json()["id"]] = respuesta.json()


def _guardar_tarea(cliente: TestClient, copia: dict, metodo, ruta: str, cuerpo: dict) -> Response:
    copia["antes"] = datetime.now(UTC).replace(microsecond=0)
    respuesta = metodo(ruta, json=cuerpo)
    copia["despues"] = datetime.now(UTC)
    return respuesta


@given(_patron("que existe la tarea {tarea} con el workflow {workflow}"))
@when(_patron("creo la tarea {tarea} con el workflow {workflow}"), target_fixture="respuesta")
def crear_tarea_con_workflow(
    cliente: TestClient, copia: dict, tarea: str, workflow: str
) -> Response:
    cuerpo = {**_DATOS, "nombre": tarea, "workflow_id": _workflow(cliente, workflow)["id"]}
    respuesta = _guardar_tarea(cliente, copia, cliente.post, _TAREAS, cuerpo)
    assert respuesta.status_code == 201
    return respuesta


def _editar_tarea(cliente: TestClient, copia: dict, tarea: str, workflow_id: int | None):
    ruta = f"{_TAREAS}/{_tarea(cliente, tarea)['id']}"
    cuerpo = {**_DATOS, "nombre": tarea, "workflow_id": workflow_id}
    respuesta = _guardar_tarea(cliente, copia, cliente.put, ruta, cuerpo)
    assert respuesta.status_code == 200
    return respuesta


@when(_patron("edito {tarea} con el workflow {workflow}"), target_fixture="respuesta")
def editar_tarea_con_workflow(
    cliente: TestClient, copia: dict, tarea: str, workflow: str
) -> Response:
    return _editar_tarea(cliente, copia, tarea, _workflow(cliente, workflow)["id"])


@when(_patron("edito {tarea} sin workflow"), target_fixture="respuesta")
def editar_tarea_sin_workflow(cliente: TestClient, copia: dict, tarea: str) -> Response:
    return _editar_tarea(cliente, copia, tarea, None)


# --- Operaciones con los comentarios del paso -----------------------------------------


@when(_patron("comento {texto} en el paso {paso} de {workflow}"), target_fixture="respuesta")
def comentar(cliente: TestClient, texto: str, paso: str, workflow: str) -> Response:
    antes = datetime.now(UTC).replace(microsecond=0)
    respuesta = cliente.post(_ruta_de(cliente, workflow, paso), json={"texto": _texto(texto)})
    assert respuesta.status_code == 201
    assert antes <= _instante(respuesta.json()["creado"]) <= datetime.now(UTC)
    return respuesta


@when(
    _patron("comento un texto de 500 caracteres en el paso {paso} de {workflow}"),
    target_fixture="respuesta",
)
def comentar_en_el_limite(cliente: TestClient, paso: str, workflow: str) -> Response:
    return cliente.post(_ruta_de(cliente, workflow, paso), json={"texto": "á" * 500})


@when(
    parsers.re(
        r'^intento comentar en el paso "(?P<paso>[^"]+)" de "(?P<workflow>[^"]+)" '
        r"con el cuerpo (?P<cuerpo>.+)$"
    ),
    target_fixture="respuesta",
)
def comentar_con_cuerpo(cliente: TestClient, paso: str, workflow: str, cuerpo: str) -> Response:
    return cliente.post(_ruta_de(cliente, workflow, paso), json=_cuerpo(cuerpo))


@when(
    _patron("edito el comentario {comentario} del paso {paso} de {workflow} con el texto {texto}"),
    target_fixture="respuesta",
)
def editar_comentario(
    cliente: TestClient, comentario: str, paso: str, workflow: str, texto: str
) -> Response:
    ruta = _ruta_de(cliente, workflow, paso)
    return cliente.put(f"{ruta}/{_id_en(cliente, ruta, comentario)}", json={"texto": _texto(texto)})


@when(
    parsers.re(
        r'^intento editar el comentario "(?P<comentario>[^"]+)" del paso "(?P<paso>[^"]+)" '
        r'de "(?P<workflow>[^"]+)" con el cuerpo (?P<cuerpo>.+)$'
    ),
    target_fixture="respuesta",
)
def editar_comentario_con_cuerpo(
    cliente: TestClient, comentario: str, paso: str, workflow: str, cuerpo: str
) -> Response:
    ruta = _ruta_de(cliente, workflow, paso)
    return cliente.put(f"{ruta}/{_id_en(cliente, ruta, comentario)}", json=_cuerpo(cuerpo))


@when(
    _patron("elimino el comentario {comentario} del paso {paso} de {workflow}"),
    target_fixture="respuesta",
)
def eliminar_comentario(cliente: TestClient, comentario: str, paso: str, workflow: str) -> Response:
    ruta = _ruta_de(cliente, workflow, paso)
    return cliente.delete(f"{ruta}/{_id_en(cliente, ruta, comentario)}")


@when(_patron("borro el paso {paso} de {workflow}"))
def borrar_paso(cliente: TestClient, paso: str, workflow: str) -> None:
    id_workflow = _workflow(cliente, workflow)["id"]
    id_paso = _paso(cliente, workflow, paso)["id"]
    assert cliente.delete(f"{_WORKFLOWS}/{id_workflow}/pasos/{id_paso}").status_code == 200


@when(
    _patron(
        "intento {accion} el comentario {comentario} del paso {paso} de {workflow} "
        "a través del workflow con id {id_workflow}"
    ),
    target_fixture="respuesta",
)
def operar_en_workflow_inexistente(
    cliente: TestClient, accion: str, comentario: str, paso: str, workflow: str, id_workflow: str
) -> Response:
    id_c = _id_en(cliente, _ruta_de(cliente, workflow, paso), comentario)
    return _operar(cliente, accion, int(id_workflow), _paso(cliente, workflow, paso)["id"], id_c)


@when(
    _patron(
        "intento {accion} el comentario {comentario} del paso {paso} de {otro} a través de "
        "{workflow}"
    ),
    target_fixture="respuesta",
)
def operar_en_paso_de_otro_workflow(
    cliente: TestClient, accion: str, comentario: str, paso: str, otro: str, workflow: str
) -> Response:
    id_c = _id_en(cliente, _ruta_de(cliente, otro, paso), comentario)
    id_workflow = _workflow(cliente, workflow)["id"]
    return _operar(cliente, accion, id_workflow, _paso(cliente, otro, paso)["id"], id_c)


@when(
    _patron(
        "intento {accion} el comentario {comentario} del paso {otro} de {workflow} a través "
        "del paso {paso}"
    ),
    target_fixture="respuesta",
)
def operar_comentario_de_otro_paso(
    cliente: TestClient, accion: str, comentario: str, otro: str, workflow: str, paso: str
) -> Response:
    id_c = _id_en(cliente, _ruta_de(cliente, workflow, otro), comentario)
    id_workflow = _workflow(cliente, workflow)["id"]
    return _operar(cliente, accion, id_workflow, _paso(cliente, workflow, paso)["id"], id_c)


# --- Operaciones con los comentarios copiados en la subtarea --------------------------


@when(
    _patron(
        "edito el comentario {comentario} de la subtarea {subtarea} de {tarea} con el texto {texto}"
    )
)
def editar_comentario_copiado(
    cliente: TestClient, comentario: str, subtarea: str, tarea: str, texto: str
) -> None:
    ruta = _ruta_subtarea(cliente, tarea, subtarea)
    respuesta = cliente.put(f"{ruta}/{_id_en(cliente, ruta, comentario)}", json={"texto": texto})
    assert respuesta.status_code == 200


@when(_patron("elimino el comentario {comentario} de la subtarea {subtarea} de {tarea}"))
def eliminar_comentario_copiado(
    cliente: TestClient, comentario: str, subtarea: str, tarea: str
) -> None:
    ruta = _ruta_subtarea(cliente, tarea, subtarea)
    assert cliente.delete(f"{ruta}/{_id_en(cliente, ruta, comentario)}").status_code == 204


# --- Comprobaciones -------------------------------------------------------------------


@then(_patron("la API responde 201 con el comentario {texto} fechado ahora en UTC"))
def responde_con_el_comentario(respuesta: Response, texto: str) -> None:
    assert respuesta.status_code == 201
    assert set(respuesta.json()) == _CLAVES
    assert respuesta.json()["texto"] == _guardado(texto)
    assert respuesta.json()["editado"] is None


@then("la API responde 201 con un comentario de 500 caracteres")
def responde_en_el_limite(respuesta: Response) -> None:
    assert respuesta.status_code == 201
    assert respuesta.json()["texto"] == f"<p>{'á' * 500}</p>"


@then(_patron("la API responde 200 con el comentario editado {texto} con su fecha de alta"))
def responde_con_el_comentario_editado(
    originales: dict[int, dict], respuesta: Response, texto: str
) -> None:
    assert respuesta.status_code == 200
    comentario = respuesta.json()
    assert set(comentario) == _CLAVES
    assert comentario["texto"] == _guardado(texto)
    original = originales[comentario["id"]]
    assert comentario["creado"] == original["creado"]
    assert _instante(comentario["editado"]) >= _instante(original["creado"])


@then("la API responde 204 sin contenido")
def responde_sin_contenido(respuesta: Response) -> None:
    assert respuesta.status_code == 204
    assert respuesta.content == b""


@then("la API rechaza la petición por datos inválidos")
def rechaza_por_datos_invalidos(respuesta: Response) -> None:
    assert respuesta.status_code == 422


@then(_patron("los comentarios del paso {paso} de {workflow} son {textos}"))
def los_comentarios_del_paso_son(
    cliente: TestClient, paso: str, workflow: str, textos: str
) -> None:
    comentarios = _listar(cliente, _ruta_de(cliente, workflow, paso))
    assert [c["texto"] for c in comentarios] == _guardados(textos)


@then(_patron("al consultar los workflows el paso {paso} de {workflow} tiene {n} comentarios"))
def el_paso_tiene_n_comentarios(cliente: TestClient, paso: str, workflow: str, n: str) -> None:
    assert _paso(cliente, workflow, paso)["comentarios"] == int(n)


@then(_patron("en la base de datos solo quedan los comentarios de paso {textos}"))
def solo_quedan_los_de_paso(textos: str) -> None:
    assert _textos_en_bd(ComentarioPasoModelo) == sorted(_guardados(textos))


@then(_patron("en la base de datos solo quedan los comentarios de subtarea {textos}"))
def solo_quedan_los_de_subtarea(textos: str) -> None:
    assert _textos_en_bd(ComentarioSubtareaModelo) == sorted(_guardados(textos))


@then(_patron("la API responde 404 con {detalle}"))
def responde_404(respuesta: Response, detalle: str) -> None:
    _comprobar_404(respuesta, detalle)


@then(_patron("la API responde que {workflow} no tiene el paso {paso} de {otro}"))
def responde_paso_de_otro_workflow(
    cliente: TestClient, respuesta: Response, workflow: str, paso: str, otro: str
) -> None:
    id_workflow = _workflow(cliente, workflow)["id"]
    id_paso = _paso(cliente, otro, paso)["id"]
    _comprobar_404(
        respuesta, f"No existe el paso con id {id_paso} en el workflow con id {id_workflow}"
    )


@then(
    _patron(
        "la API responde que el paso {paso} de {workflow} no tiene el comentario {comentario} "
        "del paso {otro}"
    )
)
def responde_comentario_de_otro_paso(
    cliente: TestClient, respuesta: Response, paso: str, workflow: str, comentario: str, otro: str
) -> None:
    id_c = _id_en(cliente, _ruta_de(cliente, workflow, otro), comentario)
    id_paso = _paso(cliente, workflow, paso)["id"]
    _comprobar_404(respuesta, f"No existe el comentario con id {id_c} en el paso con id {id_paso}")


@then(
    _patron(
        "la subtarea {subtarea} de {tarea} tiene los comentarios copiados {textos} "
        "fechados ahora y sin editar"
    )
)
def tiene_los_comentarios_copiados(
    cliente: TestClient,
    copia: dict,
    subtarea: str,
    tarea: str,
    textos: str,
) -> None:
    copiados = _listar(cliente, _ruta_subtarea(cliente, tarea, subtarea))
    assert [c["texto"] for c in copiados] == _guardados(textos)
    assert all(c["editado"] is None for c in copiados)
    assert all(copia["antes"] <= _instante(c["creado"]) <= copia["despues"] for c in copiados)


@then(_patron("los comentarios de la subtarea {subtarea} de {tarea} son {textos}"))
def los_comentarios_de_la_subtarea_son(
    cliente: TestClient, subtarea: str, tarea: str, textos: str
) -> None:
    comentarios = _listar(cliente, _ruta_subtarea(cliente, tarea, subtarea))
    assert [c["texto"] for c in comentarios] == _guardados(textos)


@then(_patron("al consultar las tareas las subtareas de {tarea} tienen {numeros} comentarios"))
def las_subtareas_tienen_n_comentarios(cliente: TestClient, tarea: str, numeros: str) -> None:
    subtareas = _tarea(cliente, tarea)["subtareas"]
    assert [s["comentarios"] for s in subtareas] == [int(n) for n in _lista(numeros)]
