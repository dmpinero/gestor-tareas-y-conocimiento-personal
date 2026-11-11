import json
import re
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("comentarios.feature")

_TAREAS = "/api/v1/tareas"

_DATOS = {"descripcion": "d", "fecha_creacion": "2026-11-10T09:00:00"}

# "creado" y "editado" en UTC con precisión de segundos y una "Z" final.
_INSTANTE_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

_CLAVES = {"id", "texto", "creado", "editado"}


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


def _ruta_comentario(id_tarea: int, id_comentario: int) -> str:
    return f"{_ruta(id_tarea)}/{id_comentario}"


def _comentar(cliente: TestClient, tarea: str, cuerpo: dict) -> Response:
    return cliente.post(_ruta(_id_tarea(cliente, tarea)), json=cuerpo)


def _listar(cliente: TestClient, tarea: str) -> list[dict]:
    respuesta = cliente.get(_ruta(_id_tarea(cliente, tarea)))
    assert respuesta.status_code == 200
    return respuesta.json()


def _id_comentario(cliente: TestClient, tarea: str, texto: str) -> int:
    return next(c["id"] for c in _listar(cliente, tarea) if c["texto"] == texto)


def _ruta_por_texto(cliente: TestClient, tarea: str, texto: str) -> str:
    return _ruta_comentario(_id_tarea(cliente, tarea), _id_comentario(cliente, tarea, texto))


def _operar(cliente: TestClient, accion: str, ruta: str) -> Response:
    if accion == "editar":
        return cliente.put(ruta, json={"texto": "Otro"})
    return cliente.delete(ruta)


def _creado(comentario: dict) -> datetime:
    assert _INSTANTE_UTC.fullmatch(comentario["creado"]), comentario["creado"]
    return datetime.fromisoformat(comentario["creado"])


def _editado(comentario: dict) -> datetime:
    assert _INSTANTE_UTC.fullmatch(comentario["editado"]), comentario["editado"]
    return datetime.fromisoformat(comentario["editado"])


@pytest.fixture
def originales() -> dict[int, dict]:
    """Comentarios dados de alta en los antecedentes, por id, tal como se crearon."""
    return {}


@given(parsers.re(r'^que existe la tarea "(?P<nombre>[^"]+)"$'))
def existe_la_tarea(cliente: TestClient, nombre: str) -> None:
    assert cliente.post(_TAREAS, json={**_DATOS, "nombre": nombre}).status_code == 201


@given(parsers.re(r'^que "(?P<tarea>[^"]+)" tiene los comentarios "(?P<textos>[^"]*)"$'))
def tiene_los_comentarios(
    cliente: TestClient, originales: dict[int, dict], tarea: str, textos: str
) -> None:
    for texto in _lista(textos):
        respuesta = _comentar(cliente, tarea, {"texto": texto})
        assert respuesta.status_code == 201
        originales[respuesta.json()["id"]] = respuesta.json()


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


@when(
    parsers.re(
        r'^edito el comentario "(?P<comentario>[^"]+)" de "(?P<tarea>[^"]+)"'
        r' con el texto "(?P<texto>[^"]*)"$'
    ),
    target_fixture="respuesta",
)
def editar_comentario(cliente: TestClient, comentario: str, tarea: str, texto: str) -> Response:
    return cliente.put(_ruta_por_texto(cliente, tarea, comentario), json={"texto": _texto(texto)})


@when(
    parsers.re(
        r'^edito el comentario "(?P<comentario>[^"]+)" de "(?P<tarea>[^"]+)"'
        r" con un texto de 500 caracteres$"
    ),
    target_fixture="respuesta",
)
def editar_comentario_en_el_limite(cliente: TestClient, comentario: str, tarea: str) -> Response:
    return cliente.put(_ruta_por_texto(cliente, tarea, comentario), json={"texto": "á" * 500})


@when(
    parsers.re(
        r'^intento editar el comentario "(?P<comentario>[^"]+)" de "(?P<tarea>[^"]+)"'
        r" con el cuerpo (?P<cuerpo>.+)$"
    ),
    target_fixture="respuesta",
)
def editar_comentario_con_cuerpo(
    cliente: TestClient, comentario: str, tarea: str, cuerpo: str
) -> Response:
    return cliente.put(_ruta_por_texto(cliente, tarea, comentario), json=json.loads(cuerpo))


@when(
    parsers.re(
        r'^intento editar el comentario "(?P<comentario>[^"]+)" de "(?P<tarea>[^"]+)"'
        r" con un texto de 501 caracteres$"
    ),
    target_fixture="respuesta",
)
def editar_comentario_texto_largo(cliente: TestClient, comentario: str, tarea: str) -> Response:
    return cliente.put(_ruta_por_texto(cliente, tarea, comentario), json={"texto": "a" * 501})


@when(
    parsers.re(r'^elimino el comentario "(?P<comentario>[^"]+)" de "(?P<tarea>[^"]+)"$'),
    target_fixture="respuesta",
)
def eliminar_comentario(cliente: TestClient, comentario: str, tarea: str) -> Response:
    return cliente.delete(_ruta_por_texto(cliente, tarea, comentario))


@when(
    parsers.re(
        r'^intento (?P<accion>editar|eliminar) el comentario "(?P<comentario>[^"]+)"'
        r" de la tarea con id (?P<i>\d+)$"
    ),
    target_fixture="respuesta",
)
def operar_en_tarea_inexistente(
    cliente: TestClient, originales: dict[int, dict], accion: str, comentario: str, i: str
) -> Response:
    id_comentario = next(i for i, c in originales.items() if c["texto"] == comentario)
    return _operar(cliente, accion, _ruta_comentario(int(i), id_comentario))


@when(
    parsers.re(
        r"^intento (?P<accion>editar|eliminar) el comentario con id (?P<i>\d+)"
        r' de "(?P<tarea>[^"]+)"$'
    ),
    target_fixture="respuesta",
)
def operar_comentario_inexistente(cliente: TestClient, accion: str, i: str, tarea: str) -> Response:
    return _operar(cliente, accion, _ruta_comentario(_id_tarea(cliente, tarea), int(i)))


@when(
    parsers.re(
        r'^intento (?P<accion>editar|eliminar) el comentario "(?P<comentario>[^"]+)"'
        r' de "(?P<otra>[^"]+)" a través de "(?P<tarea>[^"]+)"$'
    ),
    target_fixture="respuesta",
)
def operar_comentario_de_otra(
    cliente: TestClient, accion: str, comentario: str, otra: str, tarea: str
) -> Response:
    id_comentario = _id_comentario(cliente, otra, comentario)
    return _operar(cliente, accion, _ruta_comentario(_id_tarea(cliente, tarea), id_comentario))


@then(
    parsers.re(r'^la API responde 201 con el comentario "(?P<texto>[^"]*)" fechado ahora en UTC$')
)
def la_api_responde_con_el_comentario(respuesta: Response, texto: str) -> None:
    assert respuesta.status_code == 201
    comentario = respuesta.json()
    assert set(comentario) == _CLAVES
    assert isinstance(comentario["id"], int)
    assert comentario["texto"] == _texto(texto)
    assert comentario["editado"] is None
    ahora = datetime.now(UTC)
    assert ahora - timedelta(seconds=30) <= _creado(comentario) <= ahora


@then("la API responde 201 con un comentario de 500 caracteres")
def la_api_responde_en_el_limite(cliente: TestClient, respuesta: Response) -> None:
    assert respuesta.status_code == 201
    assert respuesta.json()["texto"] == "á" * 500
    listado = cliente.get(_ruta(_id_tarea(cliente, "Mudanza"))).json()
    assert [c["texto"] for c in listado] == ["á" * 500]


def _comprobar_editado(comentario: dict, original: dict, texto: str) -> None:
    assert set(comentario) == _CLAVES
    assert comentario["id"] == original["id"]
    assert comentario["texto"] == texto
    # La fecha de alta no cambia; la de edición la pone el servidor, ahora y en UTC.
    assert comentario["creado"] == original["creado"]
    ahora = datetime.now(UTC)
    assert _creado(original) <= _editado(comentario) <= ahora
    assert ahora - timedelta(seconds=30) <= _editado(comentario)


@then(
    parsers.re(
        r'^la API responde 200 con el comentario editado "(?P<texto>[^"]*)" con su fecha de alta$'
    )
)
def la_api_responde_con_el_comentario_editado(
    respuesta: Response, originales: dict[int, dict], texto: str
) -> None:
    assert respuesta.status_code == 200
    comentario = respuesta.json()
    _comprobar_editado(comentario, originales[comentario["id"]], _texto(texto))


@then("la API responde 200 con un comentario editado de 500 caracteres")
def la_api_responde_editado_en_el_limite(
    cliente: TestClient, respuesta: Response, originales: dict[int, dict]
) -> None:
    assert respuesta.status_code == 200
    comentario = respuesta.json()
    _comprobar_editado(comentario, originales[comentario["id"]], "á" * 500)
    assert _listar(cliente, "Mudanza") == [comentario]


@then(
    parsers.re(
        r'^en "(?P<tarea>[^"]+)" solo está editado "(?P<texto>[^"]*)", con su fecha de alta$'
    )
)
def solo_esta_editado(
    cliente: TestClient,
    respuesta: Response,
    originales: dict[int, dict],
    tarea: str,
    texto: str,
) -> None:
    comentarios = _listar(cliente, tarea)
    assert set(c["id"] for c in comentarios) == set(originales)
    for comentario in comentarios:
        original = originales[comentario["id"]]
        if comentario["texto"] == _texto(texto):
            # Lo guardado es justo lo que devolvió la edición.
            assert comentario == respuesta.json()
            _comprobar_editado(comentario, original, _texto(texto))
        else:
            assert comentario == original


@then(parsers.re(r'^ningún comentario de "(?P<tarea>[^"]+)" está editado$'))
def ninguno_esta_editado(cliente: TestClient, originales: dict[int, dict], tarea: str) -> None:
    comentarios = _listar(cliente, tarea)
    assert comentarios
    assert all(c["editado"] is None for c in comentarios)
    # Los creados en los antecedentes siguen tal cual (texto y fecha de alta).
    assert all(c == originales[c["id"]] for c in comentarios if c["id"] in originales)


@then("la API responde 204 sin contenido")
def la_api_responde_sin_contenido(respuesta: Response) -> None:
    assert respuesta.status_code == 204
    assert respuesta.content == b""


@then(parsers.re(r'^los comentarios de "(?P<tarea>[^"]+)" son "(?P<textos>[^"]*)"$'))
def los_comentarios_son(cliente: TestClient, tarea: str, textos: str) -> None:
    respuesta = cliente.get(_ruta(_id_tarea(cliente, tarea)))
    assert respuesta.status_code == 200
    comentarios = respuesta.json()
    assert all(set(c) == _CLAVES for c in comentarios)
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


def _comentario_inexistente(respuesta: Response, id_tarea: int, id_comentario: int) -> None:
    assert respuesta.status_code == 404
    assert respuesta.json() == {
        "detalle": f"No existe el comentario con id {id_comentario} en la tarea con id {id_tarea}"
    }


@then(
    parsers.re(r'^la API responde que "(?P<tarea>[^"]+)" no tiene el comentario con id (?P<i>\d+)$')
)
def la_api_responde_comentario_inexistente(
    cliente: TestClient, respuesta: Response, tarea: str, i: str
) -> None:
    _comentario_inexistente(respuesta, _id_tarea(cliente, tarea), int(i))


@then(
    parsers.re(
        r'^la API responde que "(?P<tarea>[^"]+)" no tiene el comentario "(?P<comentario>[^"]+)"'
        r' de "(?P<otra>[^"]+)"$'
    )
)
def la_api_responde_comentario_de_otra(
    cliente: TestClient, respuesta: Response, tarea: str, comentario: str, otra: str
) -> None:
    _comentario_inexistente(
        respuesta, _id_tarea(cliente, tarea), _id_comentario(cliente, otra, comentario)
    )
