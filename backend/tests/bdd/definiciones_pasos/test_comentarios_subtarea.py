import json
import re
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from pytest_bdd import given, parsers, scenarios, then, when
from sqlalchemy import select

from gestor_tareas.infraestructura.persistencia.modelos import ComentarioSubtareaModelo
from gestor_tareas.infraestructura.persistencia.sesion import FabricaSesiones
from tests.bdd.comentarios_html import html_guardado

scenarios("comentarios_subtarea.feature")

_TAREAS = "/api/v1/tareas"

_DATOS = {"descripcion": "d", "fecha_creacion": "2026-11-10T09:00:00"}

# "creado" y "editado" en UTC con precisión de segundos y una "Z" final.
_INSTANTE_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

_CLAVES = {"id", "texto", "creado", "editado"}

# Texto entre comillas sin comillas dentro.
_T = r'"(?P<{}>[^"]*)"'


def _patron(texto: str) -> parsers.re:
    """Patrón de un paso: cada ``{nombre}`` es un texto entre comillas, ``{n}`` un
    número y ``{x}`` una de las operaciones con los comentarios."""
    return parsers.re("^" + texto.format_map(_Grupos()) + "$")


class _Grupos(dict):
    def __missing__(self, clave: str) -> str:
        if clave == "n" or clave.startswith("id_"):
            return rf"(?P<{clave}>\d+)"
        if clave == "accion":
            return r"(?P<accion>listar|comentar|editar|eliminar)"
        return _T.format(clave)


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


def _tarea(cliente: TestClient, nombre: str) -> dict:
    respuesta = cliente.get(_TAREAS)
    assert respuesta.status_code == 200
    return next(t for t in respuesta.json() if t["nombre"] == nombre)


def _subtarea(cliente: TestClient, tarea: str, subtarea: str) -> dict:
    return next(s for s in _tarea(cliente, tarea)["subtareas"] if s["nombre"] == subtarea)


def _ruta(id_tarea: int, id_subtarea: int, id_comentario: int | None = None) -> str:
    ruta = f"{_TAREAS}/{id_tarea}/subtareas/{id_subtarea}/comentarios"
    return ruta if id_comentario is None else f"{ruta}/{id_comentario}"


def _ruta_de(cliente: TestClient, tarea: str, subtarea: str) -> str:
    return _ruta(_tarea(cliente, tarea)["id"], _subtarea(cliente, tarea, subtarea)["id"])


def _listar(cliente: TestClient, tarea: str, subtarea: str) -> list[dict]:
    respuesta = cliente.get(_ruta_de(cliente, tarea, subtarea))
    assert respuesta.status_code == 200
    assert all(set(c) == _CLAVES for c in respuesta.json())
    return respuesta.json()


def _id_comentario(cliente: TestClient, tarea: str, subtarea: str, texto: str) -> int:
    comentarios = _listar(cliente, tarea, subtarea)
    return next(c["id"] for c in comentarios if c["texto"] == _guardado(texto))


def _cuerpo(cuerpo: str) -> dict:
    datos = json.loads(cuerpo)
    if datos.get("texto") == "<501 caracteres>":
        datos["texto"] = "a" * 501
    return datos


def _operar(cliente: TestClient, accion: str, id_tarea: int, id_subtarea: int, id_c: int):
    """Ejecuta la acción sobre el comentario ``id_c`` (o la lista, para listar y
    comentar) de la subtarea ``id_subtarea`` de la tarea ``id_tarea``."""
    if accion == "listar":
        return cliente.get(_ruta(id_tarea, id_subtarea))
    if accion == "comentar":
        return cliente.post(_ruta(id_tarea, id_subtarea), json={"texto": "Otro"})
    if accion == "editar":
        return cliente.put(_ruta(id_tarea, id_subtarea, id_c), json={"texto": "Otro"})
    return cliente.delete(_ruta(id_tarea, id_subtarea, id_c))


def _creado(comentario: dict) -> datetime:
    assert _INSTANTE_UTC.fullmatch(comentario["creado"]), comentario["creado"]
    return datetime.fromisoformat(comentario["creado"])


def _comprobar_404(respuesta: Response, detalle: str) -> None:
    # El cuerpo distingue el 404 de dominio del 404 de "ruta no encontrada".
    assert respuesta.status_code == 404
    assert respuesta.json() == {"detalle": detalle}


@pytest.fixture
def originales() -> dict[int, dict]:
    """Comentarios dados de alta en los antecedentes, por id, tal como se crearon."""
    return {}


@given(_patron("que existe la tarea {tarea} con las subtareas {subtareas}"))
def existe_la_tarea_con_subtareas(cliente: TestClient, tarea: str, subtareas: str) -> None:
    respuesta = cliente.post(_TAREAS, json={**_DATOS, "nombre": tarea})
    assert respuesta.status_code == 201
    for subtarea in _lista(subtareas):
        ruta = f"{_TAREAS}/{respuesta.json()['id']}/subtareas"
        assert cliente.post(ruta, json={"nombre": subtarea}).status_code == 201


@given(_patron("que la subtarea {subtarea} de {tarea} tiene los comentarios {textos}"))
def tiene_los_comentarios(
    cliente: TestClient, originales: dict[int, dict], subtarea: str, tarea: str, textos: str
) -> None:
    for texto in _lista(textos):
        respuesta = cliente.post(_ruta_de(cliente, tarea, subtarea), json={"texto": texto})
        assert respuesta.status_code == 201
        originales[respuesta.json()["id"]] = respuesta.json()


@given(_patron("que {tarea} tiene el comentario de tarea {texto}"))
def tiene_el_comentario_de_tarea(cliente: TestClient, tarea: str, texto: str) -> None:
    ruta = f"{_TAREAS}/{_tarea(cliente, tarea)['id']}/comentarios"
    assert cliente.post(ruta, json={"texto": texto}).status_code == 201


@when(
    _patron("comento {texto} en la subtarea {subtarea} de {tarea}"),
    target_fixture="respuesta",
)
def comentar(cliente: TestClient, texto: str, subtarea: str, tarea: str) -> Response:
    antes = datetime.now(UTC).replace(microsecond=0)
    respuesta = cliente.post(_ruta_de(cliente, tarea, subtarea), json={"texto": _texto(texto)})
    despues = datetime.now(UTC)
    assert respuesta.status_code == 201
    assert antes <= _creado(respuesta.json()) <= despues
    return respuesta


@when(
    _patron("comento un texto de 500 caracteres en la subtarea {subtarea} de {tarea}"),
    target_fixture="respuesta",
)
def comentar_en_el_limite(cliente: TestClient, subtarea: str, tarea: str) -> Response:
    return cliente.post(_ruta_de(cliente, tarea, subtarea), json={"texto": "á" * 500})


@when(
    parsers.re(
        r'^intento comentar en la subtarea "(?P<subtarea>[^"]+)" de "(?P<tarea>[^"]+)" '
        r"con el cuerpo (?P<cuerpo>.+)$"
    ),
    target_fixture="respuesta",
)
def comentar_con_cuerpo(cliente: TestClient, subtarea: str, tarea: str, cuerpo: str) -> Response:
    return cliente.post(_ruta_de(cliente, tarea, subtarea), json=_cuerpo(cuerpo))


@when(
    _patron(
        "edito el comentario {comentario} de la subtarea {subtarea} de {tarea} con el texto {texto}"
    ),
    target_fixture="respuesta",
)
def editar_comentario(
    cliente: TestClient, comentario: str, subtarea: str, tarea: str, texto: str
) -> Response:
    id_c = _id_comentario(cliente, tarea, subtarea, comentario)
    ruta = f"{_ruta_de(cliente, tarea, subtarea)}/{id_c}"
    return cliente.put(ruta, json={"texto": _texto(texto)})


@when(
    parsers.re(
        r'^intento editar el comentario "(?P<comentario>[^"]+)" de la subtarea '
        r'"(?P<subtarea>[^"]+)" de "(?P<tarea>[^"]+)" con el cuerpo (?P<cuerpo>.+)$'
    ),
    target_fixture="respuesta",
)
def editar_comentario_con_cuerpo(
    cliente: TestClient, comentario: str, subtarea: str, tarea: str, cuerpo: str
) -> Response:
    id_c = _id_comentario(cliente, tarea, subtarea, comentario)
    return cliente.put(f"{_ruta_de(cliente, tarea, subtarea)}/{id_c}", json=_cuerpo(cuerpo))


@when(
    _patron("elimino el comentario {comentario} de la subtarea {subtarea} de {tarea}"),
    target_fixture="respuesta",
)
def eliminar_comentario(
    cliente: TestClient, comentario: str, subtarea: str, tarea: str
) -> Response:
    id_c = _id_comentario(cliente, tarea, subtarea, comentario)
    return cliente.delete(f"{_ruta_de(cliente, tarea, subtarea)}/{id_c}")


@when(_patron("borro la subtarea {subtarea} de {tarea}"))
def borrar_subtarea(cliente: TestClient, subtarea: str, tarea: str) -> None:
    id_tarea = _tarea(cliente, tarea)["id"]
    id_subtarea = _subtarea(cliente, tarea, subtarea)["id"]
    respuesta = cliente.delete(f"{_TAREAS}/{id_tarea}/subtareas/{id_subtarea}")
    assert respuesta.status_code == 200


@when(
    _patron(
        "intento {accion} el comentario {comentario} de la subtarea {subtarea} "
        "a través de la tarea con id {id_tarea}"
    ),
    target_fixture="respuesta",
)
def operar_en_tarea_inexistente(
    cliente: TestClient, accion: str, comentario: str, subtarea: str, id_tarea: str
) -> Response:
    tarea = next(
        t
        for t in cliente.get(_TAREAS).json()
        if any(s["nombre"] == subtarea for s in t["subtareas"])
    )
    id_subtarea = _subtarea(cliente, tarea["nombre"], subtarea)["id"]
    id_c = _id_comentario(cliente, tarea["nombre"], subtarea, comentario)
    return _operar(cliente, accion, int(id_tarea), id_subtarea, id_c)


@when(
    _patron("intento {accion} los comentarios de la subtarea con id {id_subtarea} de {tarea}"),
    target_fixture="respuesta",
)
def operar_en_subtarea_inexistente(
    cliente: TestClient, accion: str, id_subtarea: str, tarea: str
) -> Response:
    return _operar(cliente, accion, _tarea(cliente, tarea)["id"], int(id_subtarea), 1)


@when(
    _patron(
        "intento {accion} el comentario {comentario} de la subtarea {subtarea} de "
        "{otra} a través de {tarea}"
    ),
    target_fixture="respuesta",
)
def operar_en_subtarea_de_otra(
    cliente: TestClient, accion: str, comentario: str, subtarea: str, otra: str, tarea: str
) -> Response:
    id_subtarea = _subtarea(cliente, otra, subtarea)["id"]
    id_c = _id_comentario(cliente, otra, subtarea, comentario)
    return _operar(cliente, accion, _tarea(cliente, tarea)["id"], id_subtarea, id_c)


@when(
    _patron("intento {accion} el comentario con id {id_c} de la subtarea {subtarea} de {tarea}"),
    target_fixture="respuesta",
)
def operar_comentario_inexistente(
    cliente: TestClient, accion: str, id_c: str, subtarea: str, tarea: str
) -> Response:
    id_subtarea = _subtarea(cliente, tarea, subtarea)["id"]
    return _operar(cliente, accion, _tarea(cliente, tarea)["id"], id_subtarea, int(id_c))


@when(
    _patron(
        "intento {accion} el comentario {comentario} de {otra} a través de la "
        "subtarea {subtarea} de {tarea}"
    ),
    target_fixture="respuesta",
)
def operar_comentario_de_otra_subtarea(
    cliente: TestClient, accion: str, comentario: str, otra: str, subtarea: str, tarea: str
) -> Response:
    id_c = _id_comentario(cliente, tarea, otra, comentario)
    id_subtarea = _subtarea(cliente, tarea, subtarea)["id"]
    return _operar(cliente, accion, _tarea(cliente, tarea)["id"], id_subtarea, id_c)


@when(
    _patron(
        "intento {accion} el comentario de tarea {comentario} a través de la "
        "subtarea {subtarea} de {tarea}"
    ),
    target_fixture="respuesta",
)
def operar_comentario_de_tarea(
    cliente: TestClient, accion: str, comentario: str, subtarea: str, tarea: str
) -> Response:
    id_tarea = _tarea(cliente, tarea)["id"]
    comentarios = cliente.get(f"{_TAREAS}/{id_tarea}/comentarios").json()
    id_c = next(c["id"] for c in comentarios if c["texto"] == _guardado(comentario))
    return _operar(cliente, accion, id_tarea, _subtarea(cliente, tarea, subtarea)["id"], id_c)


@then(_patron("la API responde 201 con el comentario {texto} fechado ahora en UTC"))
def la_api_responde_con_el_comentario(respuesta: Response, texto: str) -> None:
    assert respuesta.status_code == 201
    comentario = respuesta.json()
    assert set(comentario) == _CLAVES
    assert comentario["texto"] == _guardado(texto)
    assert comentario["editado"] is None


@then("la API responde 201 con un comentario de 500 caracteres")
def la_api_responde_en_el_limite(respuesta: Response) -> None:
    assert respuesta.status_code == 201
    assert respuesta.json()["texto"] == f"<p>{'á' * 500}</p>"


@then(_patron("la API responde 200 con el comentario editado {texto} con su fecha de alta"))
def la_api_responde_con_el_comentario_editado(
    originales: dict[int, dict], respuesta: Response, texto: str
) -> None:
    assert respuesta.status_code == 200
    comentario = respuesta.json()
    assert set(comentario) == _CLAVES
    assert comentario["texto"] == _guardado(texto)
    original = originales[comentario["id"]]
    assert comentario["creado"] == original["creado"]
    assert _INSTANTE_UTC.fullmatch(comentario["editado"])
    assert datetime.fromisoformat(comentario["editado"]) >= _creado(original)


@then(_patron("en la subtarea {subtarea} de {tarea} solo está editado {texto}"))
def solo_esta_editado(
    cliente: TestClient, originales: dict[int, dict], subtarea: str, tarea: str, texto: str
) -> None:
    for comentario in _listar(cliente, tarea, subtarea):
        assert comentario["creado"] == originales[comentario["id"]]["creado"]
        assert (comentario["editado"] is not None) == (comentario["texto"] == _guardado(texto))


@then(_patron("en la subtarea {subtarea} de {tarea} ningún comentario está editado"))
def ninguno_esta_editado(
    cliente: TestClient, originales: dict[int, dict], subtarea: str, tarea: str
) -> None:
    comentarios = _listar(cliente, tarea, subtarea)
    assert comentarios == [originales[c["id"]] for c in comentarios]


@then("la API responde 204 sin contenido")
def la_api_responde_sin_contenido(respuesta: Response) -> None:
    assert respuesta.status_code == 204
    assert respuesta.content == b""


@then(_patron("los comentarios de la subtarea {subtarea} de {tarea} son {textos}"))
def los_comentarios_son(cliente: TestClient, subtarea: str, tarea: str, textos: str) -> None:
    assert [c["texto"] for c in _listar(cliente, tarea, subtarea)] == _guardados(textos)


@then(_patron("los comentarios de {tarea} son {textos}"))
def los_comentarios_de_la_tarea_son(cliente: TestClient, tarea: str, textos: str) -> None:
    respuesta = cliente.get(f"{_TAREAS}/{_tarea(cliente, tarea)['id']}/comentarios")
    assert respuesta.status_code == 200
    assert [c["texto"] for c in respuesta.json()] == _guardados(textos)


@then(_patron("al consultar las tareas la subtarea {subtarea} de {tarea} tiene {n} comentarios"))
def la_subtarea_tiene_n_comentarios(cliente: TestClient, subtarea: str, tarea: str, n: str) -> None:
    assert _subtarea(cliente, tarea, subtarea)["comentarios"] == int(n)


@then(_patron("en la base de datos solo quedan los comentarios de subtarea {textos}"))
def solo_quedan_en_la_base_de_datos(textos: str) -> None:
    sesion = FabricaSesiones()
    try:
        filas = sesion.scalars(select(ComentarioSubtareaModelo.texto)).all()
    finally:
        sesion.close()
    assert sorted(filas) == sorted(_guardados(textos))


@then("la API rechaza la petición por datos inválidos")
def la_api_rechaza_por_datos_invalidos(respuesta: Response) -> None:
    assert respuesta.status_code == 422


@then(_patron("la API responde que no existe la tarea con id {id_tarea}"))
def la_api_responde_tarea_inexistente(respuesta: Response, id_tarea: str) -> None:
    _comprobar_404(respuesta, f"No existe la tarea con id {id_tarea}")


@then(_patron("la API responde que {tarea} no tiene la subtarea con id {id_subtarea}"))
def la_api_responde_subtarea_inexistente(
    cliente: TestClient, respuesta: Response, tarea: str, id_subtarea: str
) -> None:
    id_tarea = _tarea(cliente, tarea)["id"]
    _comprobar_404(
        respuesta, f"No existe la subtarea con id {id_subtarea} en la tarea con id {id_tarea}"
    )


@then(_patron("la API responde que {tarea} no tiene la subtarea {subtarea} de {otra}"))
def la_api_responde_subtarea_de_otra(
    cliente: TestClient, respuesta: Response, tarea: str, subtarea: str, otra: str
) -> None:
    id_subtarea = _subtarea(cliente, otra, subtarea)["id"]
    la_api_responde_subtarea_inexistente(cliente, respuesta, tarea, str(id_subtarea))


def _comentario_inexistente(respuesta: Response, id_subtarea: int, id_comentario: int) -> None:
    _comprobar_404(
        respuesta,
        f"No existe el comentario con id {id_comentario} en la subtarea con id {id_subtarea}",
    )


@then(
    _patron(
        "la API responde que la subtarea {subtarea} de {tarea} no tiene el comentario con id {id_c}"
    )
)
def la_api_responde_comentario_inexistente(
    cliente: TestClient, respuesta: Response, subtarea: str, tarea: str, id_c: str
) -> None:
    _comentario_inexistente(respuesta, _subtarea(cliente, tarea, subtarea)["id"], int(id_c))


@then(
    _patron(
        "la API responde que la subtarea {subtarea} de {tarea} no tiene el comentario "
        "{comentario} de {otra}"
    )
)
def la_api_responde_comentario_de_otra_subtarea(
    cliente: TestClient, respuesta: Response, subtarea: str, tarea: str, comentario: str, otra: str
) -> None:
    id_c = _id_comentario(cliente, tarea, otra, comentario)
    _comentario_inexistente(respuesta, _subtarea(cliente, tarea, subtarea)["id"], id_c)


@then(
    _patron(
        "la API responde que la subtarea {subtarea} de {tarea} no tiene el comentario de "
        "tarea {comentario}"
    )
)
def la_api_responde_comentario_de_tarea(
    cliente: TestClient, respuesta: Response, subtarea: str, tarea: str, comentario: str
) -> None:
    id_tarea = _tarea(cliente, tarea)["id"]
    comentarios = cliente.get(f"{_TAREAS}/{id_tarea}/comentarios").json()
    id_c = next(c["id"] for c in comentarios if c["texto"] == _guardado(comentario))
    _comentario_inexistente(respuesta, _subtarea(cliente, tarea, subtarea)["id"], id_c)
