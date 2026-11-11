import json

from fastapi.testclient import TestClient
from httpx import Response
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("subtareas.feature")

_TAREAS = "/api/v1/tareas"
_PERSONAS = "/api/v1/personas"

_DATOS = {"descripcion": "d", "fecha_creacion": "2026-11-10T09:00:00"}

# Texto entre comillas sin comillas dentro.
_T = r'"(?P<{}>[^"]*)"'


def _patron(texto: str) -> parsers.re:
    """Patrón de un paso: cada ``{nombre}`` es un texto entre comillas."""
    return parsers.re("^" + texto.format_map(_Grupos()) + "$")


class _Grupos(dict):
    def __missing__(self, clave: str) -> str:
        return _T.format(clave)


def _lista(texto: str, separador: str = ", ") -> list[str]:
    return texto.split(separador) if texto else []


def _esperadas(texto: str) -> list[tuple[str, str | None, int | None, bool]]:
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


def _subtareas(tarea: dict) -> list[tuple[str, str | None, int | None, bool]]:
    subtareas = tarea["subtareas"]
    claves = {"id", "nombre", "asignado", "prioridad", "resuelta", "comentarios"}
    assert all(set(s) == claves for s in subtareas)
    assert all(s["comentarios"] == 0 for s in subtareas)
    ids = [s["id"] for s in subtareas]
    assert ids == sorted(set(ids))  # Ids únicos y por orden de alta.
    return [(s["nombre"], s["asignado"], s["prioridad"], s["resuelta"]) for s in subtareas]


def _tarea(cliente: TestClient, nombre: str) -> dict:
    respuesta = cliente.get(_TAREAS)
    assert respuesta.status_code == 200
    return next(t for t in respuesta.json() if t["nombre"] == nombre)


def _id_subtarea(cliente: TestClient, tarea: str, subtarea: str) -> int:
    return next(s["id"] for s in _tarea(cliente, tarea)["subtareas"] if s["nombre"] == subtarea)


def _ruta(id_tarea: int, id_subtarea: int | None = None) -> str:
    ruta = f"{_TAREAS}/{id_tarea}/subtareas"
    return ruta if id_subtarea is None else f"{ruta}/{id_subtarea}"


def _anadir(cliente: TestClient, tarea: str, cuerpo: dict) -> Response:
    return cliente.post(_ruta(_tarea(cliente, tarea)["id"]), json=cuerpo)


def _resolver(cliente: TestClient, id_tarea: int, id_subtarea: int, resuelta: bool) -> Response:
    return cliente.patch(f"{_ruta(id_tarea, id_subtarea)}/resuelta", json={"resuelta": resuelta})


@given(_patron("que existe la tarea {nombre}"))
def existe_la_tarea(cliente: TestClient, nombre: str) -> None:
    assert cliente.post(_TAREAS, json={**_DATOS, "nombre": nombre}).status_code == 201


@given(_patron("que existe la tarea {nombre} asignada a {persona}"))
def existe_la_tarea_asignada(cliente: TestClient, nombre: str, persona: str) -> None:
    cuerpo = {**_DATOS, "nombre": nombre, "asignados": [persona]}
    assert cliente.post(_TAREAS, json=cuerpo).status_code == 201


@given(_patron("que {tarea} tiene las subtareas {nombres}"))
def tiene_las_subtareas(cliente: TestClient, tarea: str, nombres: str) -> None:
    for nombre in _lista(nombres):
        assert _anadir(cliente, tarea, {"nombre": nombre}).status_code == 201


@given(_patron("la subtarea {subtarea} de {tarea} está resuelta"))
def la_subtarea_esta_resuelta(cliente: TestClient, subtarea: str, tarea: str) -> None:
    id_tarea = _tarea(cliente, tarea)["id"]
    respuesta = _resolver(cliente, id_tarea, _id_subtarea(cliente, tarea, subtarea), True)
    assert respuesta.status_code == 200


@when(_patron("añado a {tarea} la subtarea {nombre}"), target_fixture="respuesta")
def anadir_subtarea(cliente: TestClient, tarea: str, nombre: str) -> Response:
    return _anadir(cliente, tarea, {"nombre": nombre})


@when(
    _patron(r"añado a {tarea} la subtarea {nombre} asignada a {persona} con prioridad (?P<p>\d)"),
    target_fixture="respuesta",
)
def anadir_subtarea_completa(
    cliente: TestClient, tarea: str, nombre: str, persona: str, p: str
) -> Response:
    return _anadir(cliente, tarea, {"nombre": nombre, "asignado": persona, "prioridad": int(p)})


@when(
    _patron(
        "añado a {tarea} una subtarea con un nombre de 200 caracteres asignada a una persona de 100"
    ),
    target_fixture="respuesta",
)
def anadir_subtarea_en_el_limite(cliente: TestClient, tarea: str) -> Response:
    return _anadir(cliente, tarea, {"nombre": "n" * 200, "asignado": "p" * 100})


@when(
    _patron(r"marco la subtarea {subtarea} de {tarea} como (?P<estado>resuelta|pendiente)"),
    target_fixture="respuesta",
)
def marcar_subtarea(cliente: TestClient, subtarea: str, tarea: str, estado: str) -> Response:
    id_tarea = _tarea(cliente, tarea)["id"]
    return _resolver(
        cliente, id_tarea, _id_subtarea(cliente, tarea, subtarea), estado == "resuelta"
    )


@when(_patron("elimino la subtarea {subtarea} de {tarea}"), target_fixture="respuesta")
def eliminar_subtarea(cliente: TestClient, subtarea: str, tarea: str) -> Response:
    id_tarea = _tarea(cliente, tarea)["id"]
    return cliente.delete(_ruta(id_tarea, _id_subtarea(cliente, tarea, subtarea)))


def _editar(cliente: TestClient, nombre: str, cuerpo: dict) -> Response:
    return cliente.put(f"{_TAREAS}/{_tarea(cliente, nombre)['id']}", json=cuerpo)


@when(_patron("edito {nombre} como oportunidad"), target_fixture="respuesta")
def editar_como_oportunidad(cliente: TestClient, nombre: str) -> Response:
    cuerpo = {**_DATOS, "nombre": nombre, "tipo": "oportunidad", "oportunidad": {"codigo": "OP"}}
    return _editar(cliente, nombre, cuerpo)


@when(_patron("edito {nombre} sin tipo"), target_fixture="respuesta")
def editar_sin_tipo(cliente: TestClient, nombre: str) -> Response:
    return _editar(cliente, nombre, {**_DATOS, "nombre": nombre})


@when(_patron("marco {nombre} como completada"), target_fixture="respuesta")
def marcar_completada(cliente: TestClient, nombre: str) -> Response:
    ruta = f"{_TAREAS}/{_tarea(cliente, nombre)['id']}/completada"
    return cliente.patch(ruta, json={"completada": True})


@when(
    _patron("intento añadir a {tarea} una subtarea con el cuerpo (?P<cuerpo>.+)"),
    target_fixture="respuesta",
)
def anadir_con_cuerpo(cliente: TestClient, tarea: str, cuerpo: str) -> Response:
    return _anadir(cliente, tarea, json.loads(cuerpo))


@when(
    _patron("intento añadir a {tarea} una subtarea con un nombre de 201 caracteres"),
    target_fixture="respuesta",
)
def anadir_nombre_largo(cliente: TestClient, tarea: str) -> Response:
    return _anadir(cliente, tarea, {"nombre": "n" * 201})


@when(
    _patron("intento añadir a {tarea} una subtarea asignada a una persona de 101 caracteres"),
    target_fixture="respuesta",
)
def anadir_persona_larga(cliente: TestClient, tarea: str) -> Response:
    return _anadir(cliente, tarea, {"nombre": "A", "asignado": "p" * 101})


@when(
    _patron("intento cambiar la subtarea {subtarea} de {tarea} con el cuerpo (?P<cuerpo>.+)"),
    target_fixture="respuesta",
)
def cambiar_con_cuerpo(cliente: TestClient, subtarea: str, tarea: str, cuerpo: str) -> Response:
    id_tarea = _tarea(cliente, tarea)["id"]
    ruta = f"{_ruta(id_tarea, _id_subtarea(cliente, tarea, subtarea))}/resuelta"
    return cliente.patch(ruta, json=json.loads(cuerpo))


@when(
    _patron(
        r"intento añadir la subtarea {nombre} asignada a {persona} a la tarea con id (?P<i>\d+)"
    ),
    target_fixture="respuesta",
)
def anadir_a_tarea_inexistente(cliente: TestClient, nombre: str, persona: str, i: str) -> Response:
    return cliente.post(_ruta(int(i)), json={"nombre": nombre, "asignado": persona})


def _id_de_cualquier_tarea(cliente: TestClient, subtarea: str) -> int:
    return next(
        s["id"]
        for t in cliente.get(_TAREAS).json()
        for s in t["subtareas"]
        if s["nombre"] == subtarea
    )


@when(
    _patron(r"intento marcar como resuelta la subtarea {subtarea} de la tarea con id (?P<i>\d+)"),
    target_fixture="respuesta",
)
def resolver_en_tarea_inexistente(cliente: TestClient, subtarea: str, i: str) -> Response:
    return _resolver(cliente, int(i), _id_de_cualquier_tarea(cliente, subtarea), True)


@when(
    _patron(r"intento eliminar la subtarea {subtarea} de la tarea con id (?P<i>\d+)"),
    target_fixture="respuesta",
)
def eliminar_en_tarea_inexistente(cliente: TestClient, subtarea: str, i: str) -> Response:
    return cliente.delete(_ruta(int(i), _id_de_cualquier_tarea(cliente, subtarea)))


@when(
    _patron(r"intento marcar como resuelta la subtarea con id (?P<i>\d+) de {tarea}"),
    target_fixture="respuesta",
)
def resolver_subtarea_inexistente(cliente: TestClient, i: str, tarea: str) -> Response:
    return _resolver(cliente, _tarea(cliente, tarea)["id"], int(i), True)


@when(
    _patron(r"intento eliminar la subtarea con id (?P<i>\d+) de {tarea}"),
    target_fixture="respuesta",
)
def eliminar_subtarea_inexistente(cliente: TestClient, i: str, tarea: str) -> Response:
    return cliente.delete(_ruta(_tarea(cliente, tarea)["id"], int(i)))


@when(
    _patron("intento marcar como resuelta la subtarea {subtarea} de {otra} a través de {tarea}"),
    target_fixture="respuesta",
)
def resolver_de_otra(cliente: TestClient, subtarea: str, otra: str, tarea: str) -> Response:
    id_tarea = _tarea(cliente, tarea)["id"]
    return _resolver(cliente, id_tarea, _id_subtarea(cliente, otra, subtarea), True)


@when(
    _patron("intento eliminar la subtarea {subtarea} de {otra} a través de {tarea}"),
    target_fixture="respuesta",
)
def eliminar_de_otra(cliente: TestClient, subtarea: str, otra: str, tarea: str) -> Response:
    id_tarea = _tarea(cliente, tarea)["id"]
    return cliente.delete(_ruta(id_tarea, _id_subtarea(cliente, otra, subtarea)))


@given(
    _patron(r"que {tarea} tiene la subtarea {nombre} asignada a {persona} con prioridad (?P<p>\d)")
)
def tiene_la_subtarea_completa(
    cliente: TestClient, tarea: str, nombre: str, persona: str, p: str
) -> None:
    cuerpo = {"nombre": nombre, "asignado": persona, "prioridad": int(p)}
    assert _anadir(cliente, tarea, cuerpo).status_code == 201


def _editar_subtarea(
    cliente: TestClient, id_tarea: int, id_subtarea: int, cuerpo: dict
) -> Response:
    return cliente.put(_ruta(id_tarea, id_subtarea), json=cuerpo)


def _editar_por_nombre(cliente: TestClient, tarea: str, subtarea: str, cuerpo: dict) -> Response:
    id_tarea = _tarea(cliente, tarea)["id"]
    return _editar_subtarea(cliente, id_tarea, _id_subtarea(cliente, tarea, subtarea), cuerpo)


@when(
    _patron("edito la subtarea {subtarea} de {tarea} con el cuerpo (?P<cuerpo>.+)"),
    target_fixture="respuesta",
)
def editar_subtarea_con_cuerpo(
    cliente: TestClient, subtarea: str, tarea: str, cuerpo: str
) -> Response:
    return _editar_por_nombre(cliente, tarea, subtarea, json.loads(cuerpo))


@when(
    _patron(
        "edito la subtarea {subtarea} de {tarea} con un nombre de 200 caracteres"
        " y una persona de 100"
    ),
    target_fixture="respuesta",
)
def editar_subtarea_en_el_limite(cliente: TestClient, subtarea: str, tarea: str) -> Response:
    cuerpo = {"nombre": "n" * 200, "asignado": "p" * 100}
    return _editar_por_nombre(cliente, tarea, subtarea, cuerpo)


@when(
    _patron("intento editar la subtarea {subtarea} de {tarea} con un nombre de 201 caracteres"),
    target_fixture="respuesta",
)
def editar_subtarea_nombre_largo(cliente: TestClient, subtarea: str, tarea: str) -> Response:
    return _editar_por_nombre(cliente, tarea, subtarea, {"nombre": "n" * 201})


@when(
    _patron("intento editar la subtarea {subtarea} de {tarea} con una persona de 101 caracteres"),
    target_fixture="respuesta",
)
def editar_subtarea_persona_larga(cliente: TestClient, subtarea: str, tarea: str) -> Response:
    return _editar_por_nombre(cliente, tarea, subtarea, {"nombre": "A", "asignado": "p" * 101})


@when(
    _patron(
        r"intento editar la subtarea {subtarea} de la tarea con id (?P<i>\d+)"
        " asignándola a {persona}"
    ),
    target_fixture="respuesta",
)
def editar_en_tarea_inexistente(
    cliente: TestClient, subtarea: str, i: str, persona: str
) -> Response:
    id_subtarea = _id_de_cualquier_tarea(cliente, subtarea)
    return _editar_subtarea(cliente, int(i), id_subtarea, {"nombre": "X", "asignado": persona})


@when(
    _patron(r"intento editar la subtarea con id (?P<i>\d+) de {tarea} asignándola a {persona}"),
    target_fixture="respuesta",
)
def editar_subtarea_inexistente(cliente: TestClient, i: str, tarea: str, persona: str) -> Response:
    id_tarea = _tarea(cliente, tarea)["id"]
    return _editar_subtarea(cliente, id_tarea, int(i), {"nombre": "X", "asignado": persona})


@when(
    _patron(
        "intento editar la subtarea {subtarea} de {otra} a través de {tarea}"
        " asignándola a {persona}"
    ),
    target_fixture="respuesta",
)
def editar_de_otra(
    cliente: TestClient, subtarea: str, otra: str, tarea: str, persona: str
) -> Response:
    id_tarea = _tarea(cliente, tarea)["id"]
    id_subtarea = _id_subtarea(cliente, otra, subtarea)
    return _editar_subtarea(cliente, id_tarea, id_subtarea, {"nombre": "X", "asignado": persona})


@then(
    _patron(r"la API responde (?P<codigo>\d+) con {nombre} y sus subtareas {subtareas}"),
)
def la_api_responde_con_subtareas(
    respuesta: Response, codigo: str, nombre: str, subtareas: str
) -> None:
    assert respuesta.status_code == int(codigo)
    assert respuesta.json()["nombre"] == nombre
    assert _subtareas(respuesta.json()) == _esperadas(subtareas)


@then(
    parsers.re(
        r"^la API responde (?P<codigo>201|200) con una subtarea de nombre de 200 caracteres"
        r" y persona de 100$"
    )
)
def la_api_responde_en_el_limite(cliente: TestClient, respuesta: Response, codigo: str) -> None:
    assert respuesta.status_code == int(codigo)
    assert _subtareas(respuesta.json()) == [("n" * 200, "p" * 100, None, False)]
    assert _subtareas(_tarea(cliente, "Mudanza")) == [("n" * 200, "p" * 100, None, False)]


@then(_patron("al consultar las tareas {nombre} tiene las subtareas {subtareas}"))
def el_listado_tiene_subtareas(cliente: TestClient, nombre: str, subtareas: str) -> None:
    assert _subtareas(_tarea(cliente, nombre)) == _esperadas(subtareas)


@then(_patron("el catálogo de personas es {nombres}"))
def el_catalogo_de_personas(cliente: TestClient, nombres: str) -> None:
    respuesta = cliente.get(_PERSONAS)
    assert respuesta.status_code == 200
    assert [p["nombre"] for p in respuesta.json()] == _lista(nombres)


@then("la API rechaza la petición por datos inválidos")
def la_api_rechaza_por_datos_invalidos(respuesta: Response) -> None:
    assert respuesta.status_code == 422


@then(_patron(r"la API responde que no existe la tarea con id (?P<i>\d+)"))
def la_api_responde_tarea_inexistente(respuesta: Response, i: str) -> None:
    # El cuerpo distingue el 404 de dominio del 404 de "ruta no encontrada".
    assert respuesta.status_code == 404
    assert respuesta.json() == {"detalle": f"No existe la tarea con id {i}"}


def _subtarea_inexistente(respuesta: Response, id_tarea: int, id_subtarea: int) -> None:
    assert respuesta.status_code == 404
    assert respuesta.json() == {
        "detalle": f"No existe la subtarea con id {id_subtarea} en la tarea con id {id_tarea}"
    }


@then(_patron(r"la API responde que {tarea} no tiene la subtarea con id (?P<i>\d+)"))
def la_api_responde_subtarea_inexistente(
    cliente: TestClient, respuesta: Response, tarea: str, i: str
) -> None:
    _subtarea_inexistente(respuesta, _tarea(cliente, tarea)["id"], int(i))


@then(_patron("la API responde que {tarea} no tiene la subtarea {subtarea} de {otra}"))
def la_api_responde_subtarea_de_otra(
    cliente: TestClient, respuesta: Response, tarea: str, subtarea: str, otra: str
) -> None:
    id_subtarea = _id_subtarea(cliente, otra, subtarea)
    _subtarea_inexistente(respuesta, _tarea(cliente, tarea)["id"], id_subtarea)
