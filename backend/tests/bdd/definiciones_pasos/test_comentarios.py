import json
import re
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from httpx import Response
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("comentarios.feature")

_TAREAS = "/api/v1/tareas"

_DATOS = {"descripcion": "d", "fecha_creacion": "2026-11-10T09:00:00"}

# "creado" en UTC con precisión de segundos y una "Z" final.
_INSTANTE_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def _texto(texto: str) -> str:
    """Los "\\n" escritos en el escenario son saltos de línea."""
    return texto.replace("\\n", "\n")


def _lista(texto: str) -> list[str]:
    return [_texto(t) for t in texto.split("; ")] if texto else []


def _id_tarea(cliente: TestClient, nombre: str) -> int:
    respuesta = cliente.get(_TAREAS)
    assert respuesta.status_code == 200
    return next(t["id"] for t in respuesta.json() if t["nombre"] == nombre)


def _ruta(id_tarea: int) -> str:
    return f"{_TAREAS}/{id_tarea}/comentarios"


def _comentar(cliente: TestClient, tarea: str, cuerpo: dict) -> Response:
    return cliente.post(_ruta(_id_tarea(cliente, tarea)), json=cuerpo)


def _creado(comentario: dict) -> datetime:
    assert _INSTANTE_UTC.fullmatch(comentario["creado"]), comentario["creado"]
    return datetime.fromisoformat(comentario["creado"])


@given(parsers.re(r'^que existe la tarea "(?P<nombre>[^"]+)"$'))
def existe_la_tarea(cliente: TestClient, nombre: str) -> None:
    assert cliente.post(_TAREAS, json={**_DATOS, "nombre": nombre}).status_code == 201


@when(
    parsers.re(r'^comento "(?P<texto>[^"]*)" en "(?P<tarea>[^"]+)"$'),
    target_fixture="respuesta",
)
def comentar(cliente: TestClient, texto: str, tarea: str) -> Response:
    antes = datetime.now(UTC).replace(microsecond=0)
    respuesta = _comentar(cliente, tarea, {"texto": _texto(texto)})
    despues = datetime.now(UTC)
    assert respuesta.status_code == 201
    assert antes <= _creado(respuesta.json()) <= despues
    return respuesta


@when(
    parsers.re(r'^comento un texto de 500 caracteres en "(?P<tarea>[^"]+)"$'),
    target_fixture="respuesta",
)
def comentar_en_el_limite(cliente: TestClient, tarea: str) -> Response:
    return _comentar(cliente, tarea, {"texto": "á" * 500})


@when(
    parsers.re(r'^intento comentar en "(?P<tarea>[^"]+)" con el cuerpo (?P<cuerpo>.+)$'),
    target_fixture="respuesta",
)
def comentar_con_cuerpo(cliente: TestClient, tarea: str, cuerpo: str) -> Response:
    return _comentar(cliente, tarea, json.loads(cuerpo))


@when(
    parsers.re(r'^intento comentar en "(?P<tarea>[^"]+)" un texto de 501 caracteres$'),
    target_fixture="respuesta",
)
def comentar_texto_largo(cliente: TestClient, tarea: str) -> Response:
    return _comentar(cliente, tarea, {"texto": "a" * 501})


@when(
    parsers.re(r'^intento comentar "(?P<texto>[^"]+)" en la tarea con id (?P<i>\d+)$'),
    target_fixture="respuesta",
)
def comentar_en_tarea_inexistente(cliente: TestClient, texto: str, i: str) -> Response:
    return cliente.post(_ruta(int(i)), json={"texto": texto})


@when(
    parsers.re(r"^consulto los comentarios de la tarea con id (?P<i>\d+)$"),
    target_fixture="respuesta",
)
def consultar_de_tarea_inexistente(cliente: TestClient, i: str) -> Response:
    return cliente.get(_ruta(int(i)))


@then(
    parsers.re(r'^la API responde 201 con el comentario "(?P<texto>[^"]*)" fechado ahora en UTC$')
)
def la_api_responde_con_el_comentario(respuesta: Response, texto: str) -> None:
    assert respuesta.status_code == 201
    comentario = respuesta.json()
    assert set(comentario) == {"id", "texto", "creado"}
    assert isinstance(comentario["id"], int)
    assert comentario["texto"] == _texto(texto)
    ahora = datetime.now(UTC)
    assert ahora - timedelta(seconds=30) <= _creado(comentario) <= ahora


@then("la API responde 201 con un comentario de 500 caracteres")
def la_api_responde_en_el_limite(cliente: TestClient, respuesta: Response) -> None:
    assert respuesta.status_code == 201
    assert respuesta.json()["texto"] == "á" * 500
    listado = cliente.get(_ruta(_id_tarea(cliente, "Mudanza"))).json()
    assert [c["texto"] for c in listado] == ["á" * 500]


@then(parsers.re(r'^los comentarios de "(?P<tarea>[^"]+)" son "(?P<textos>[^"]*)"$'))
def los_comentarios_son(cliente: TestClient, tarea: str, textos: str) -> None:
    respuesta = cliente.get(_ruta(_id_tarea(cliente, tarea)))
    assert respuesta.status_code == 200
    comentarios = respuesta.json()
    assert all(set(c) == {"id", "texto", "creado"} for c in comentarios)
    assert [c["texto"] for c in comentarios] == _lista(textos)
    claves = [(_creado(c), c["id"]) for c in comentarios]
    assert claves == sorted(claves)


@then(parsers.re(r'^al consultar las tareas "(?P<tarea>[^"]+)" no incluye comentarios$'))
def la_tarea_no_incluye_comentarios(cliente: TestClient, tarea: str) -> None:
    tareas = cliente.get(_TAREAS).json()
    assert "comentarios" not in next(t for t in tareas if t["nombre"] == tarea)


@then("la API rechaza la petición por datos inválidos")
def la_api_rechaza_por_datos_invalidos(respuesta: Response) -> None:
    assert respuesta.status_code == 422


@then(parsers.re(r"^la API responde que no existe la tarea con id (?P<i>\d+)$"))
def la_api_responde_tarea_inexistente(respuesta: Response, i: str) -> None:
    assert respuesta.status_code == 404
    assert respuesta.json() == {"detalle": f"No existe la tarea con id {i}"}
