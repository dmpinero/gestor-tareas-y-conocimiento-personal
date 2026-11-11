import json

from fastapi.testclient import TestClient
from httpx import Response
from pytest_bdd import given, parsers, scenarios, then, when
from sqlalchemy import text

from gestor_tareas.infraestructura.persistencia.sesion import FabricaSesiones

scenarios("grupos_estados.feature", "estados_de_las_tareas.feature")

_RUTA = "/api/v1/grupos-estados"
_RUTA_TAREAS = "/api/v1/tareas"
_ID_INEXISTENTE = 999999

_NOMBRES_INVALIDOS = {
    "vacío": {"nombre": ""},
    "solo de espacios": {"nombre": "   "},
    "con espacio duro": {"nombre": "  "},
    "de 51 caracteres": {"nombre": "n" * 51},
    "ausente": {},
    "que no es texto": {"nombre": 5},
}


def _lista(texto: str) -> list[str]:
    """Convierte "a, b" en ["a", "b"]; el texto vacío es la lista vacía."""
    return texto.split(", ") if texto else []


def _consultar(sql: str, **parametros) -> list[tuple]:
    sesion = FabricaSesiones()
    try:
        return [tuple(fila) for fila in sesion.execute(text(sql), parametros)]
    finally:
        sesion.close()


# --- Lecturas de la API ------------------------------------------------------


def _grupos(cliente: TestClient) -> list[dict]:
    respuesta = cliente.get(_RUTA)
    assert respuesta.status_code == 200
    return respuesta.json()


def _grupo(cliente: TestClient, nombre: str) -> dict:
    return next(g for g in _grupos(cliente) if g["nombre"] == nombre)


def _id_estado(cliente: TestClient, grupo: str, estado: str) -> int:
    """Id del estado del grupo; "inexistente" es un id que no existe."""
    if estado == "inexistente":
        return _ID_INEXISTENTE
    for g in _grupos(cliente):
        for e in g["estados"]:
            if e["nombre"] == estado and (grupo is None or g["nombre"] == grupo):
                return e["id"]
    raise AssertionError(f"No hay estado {estado!r}")


def _id_estado_cualquiera(cliente: TestClient, estado: str) -> int:
    return _id_estado(cliente, None, estado)


def _comprobar_grupo(grupo: dict, nombre: str, estados: list[str]) -> None:
    assert set(grupo) == {"id", "nombre", "tareas", "estados"}
    assert grupo["nombre"] == nombre
    assert isinstance(grupo["id"], int)
    assert [(e["posicion"], e["nombre"]) for e in grupo["estados"]] == list(
        enumerate(estados, start=1)
    )
    assert all(set(e) == {"id", "nombre", "posicion", "tareas"} for e in grupo["estados"])
    assert len({e["id"] for e in grupo["estados"]}) == len(estados)


# --- Lecturas de la base de datos ------------------------------------------------


def _grupos_guardados() -> list[str]:
    return [fila[0] for fila in _consultar("SELECT nombre FROM grupos_estados ORDER BY nombre")]


def _estados_guardados(grupo: str) -> list[tuple[int, str]]:
    return _consultar(
        "SELECT e.posicion, e.nombre FROM estados_grupo e "
        "JOIN grupos_estados g ON g.id = e.grupo_id WHERE g.nombre = :grupo ORDER BY e.posicion",
        grupo=grupo,
    )


def _grupo_y_estado_guardados(tarea: str) -> tuple[str | None, str | None]:
    filas = _consultar(
        "SELECT g.nombre, e.nombre, e.grupo_id, t.grupo_estados_id FROM tareas t "
        "LEFT JOIN grupos_estados g ON g.id = t.grupo_estados_id "
        "LEFT JOIN estados_grupo e ON e.id = t.estado_id WHERE t.nombre = :tarea",
        tarea=tarea,
    )
    assert len(filas) == 1
    grupo, estado, grupo_del_estado, grupo_de_la_tarea = filas[0]
    # El estado de la tarea siempre es de su grupo.
    assert grupo_del_estado == grupo_de_la_tarea
    return grupo, estado


# --- Tareas ------------------------------------------------------------------


def _cuerpo_tarea(nombre: str, **extra) -> dict:
    return {
        "nombre": nombre,
        "descripcion": f"Descripción de {nombre}",
        "fecha_creacion": "2026-11-11T10:00:00",
        **extra,
    }


def _id_tarea(cliente: TestClient, nombre: str) -> int:
    return next(t["id"] for t in cliente.get(_RUTA_TAREAS).json() if t["nombre"] == nombre)


# --- Dado ----------------------------------------------------------------------


@given("que no hay grupos de estados")
def sin_grupos(cliente: TestClient) -> None:
    assert _grupos(cliente) == []


@given(parsers.parse('que existe el grupo "{nombre}" con los estados "{estados}"'))
def grupo_con_estados(cliente: TestClient, nombre: str, estados: str) -> None:
    respuesta = cliente.post(_RUTA, json={"nombre": nombre})
    assert respuesta.status_code == 201
    for estado in _lista(estados):
        ruta = f"{_RUTA}/{respuesta.json()['id']}/estados"
        assert cliente.post(ruta, json={"nombre": estado}).status_code == 201


@given(parsers.parse('que existe el grupo "{nombre}" sin estados'))
def grupo_sin_estados(cliente: TestClient, nombre: str) -> None:
    assert cliente.post(_RUTA, json={"nombre": nombre}).status_code == 201


@given(parsers.parse('que existe la tarea "{nombre}" sin grupo de estados'))
def tarea_sin_grupo(cliente: TestClient, nombre: str) -> None:
    assert cliente.post(_RUTA_TAREAS, json=_cuerpo_tarea(nombre)).status_code == 201


@given(parsers.parse('que existe la tarea "{nombre}" con el grupo "{grupo}"'))
def tarea_con_grupo(cliente: TestClient, nombre: str, grupo: str) -> None:
    cuerpo = _cuerpo_tarea(nombre, grupo_estados_id=_grupo(cliente, grupo)["id"])
    assert cliente.post(_RUTA_TAREAS, json=cuerpo).status_code == 201


@given(parsers.parse('que muevo la tarea "{tarea}" al estado "{estado}"'))
def tarea_movida(cliente: TestClient, tarea: str, estado: str) -> None:
    respuesta = mover_tarea(cliente, tarea, estado)
    assert respuesta.status_code == 200


@given(parsers.parse('que reordeno los estados del grupo "{grupo}" como "{estados}"'))
def estados_reordenados(cliente: TestClient, grupo: str, estados: str) -> None:
    assert reordenar_estados(cliente, grupo, estados).status_code == 200


# --- Cuando: grupos --------------------------------------------------------------


@when("consulto los grupos de estados", target_fixture="respuesta")
def consultar_grupos(cliente: TestClient) -> Response:
    return cliente.get(_RUTA)


@when(parsers.parse('creo el grupo de estados "{nombre}"'), target_fixture="respuesta")
def crear_grupo(cliente: TestClient, nombre: str) -> Response:
    return cliente.post(_RUTA, json={"nombre": nombre})


@when("creo un grupo de estados con un nombre de 50 caracteres", target_fixture="respuesta")
def crear_grupo_de_50(cliente: TestClient) -> Response:
    return cliente.post(_RUTA, json={"nombre": "n" * 50})


@when(
    parsers.parse("intento crear un grupo de estados con un nombre {nombre}"),
    target_fixture="respuesta",
)
def crear_grupo_invalido(cliente: TestClient, nombre: str) -> Response:
    return cliente.post(_RUTA, json=_NOMBRES_INVALIDOS[nombre])


@when(parsers.parse('renombro el grupo "{actual}" a "{nuevo}"'), target_fixture="respuesta")
def renombrar_grupo(cliente: TestClient, actual: str, nuevo: str) -> Response:
    return cliente.put(f"{_RUTA}/{_grupo(cliente, actual)['id']}", json={"nombre": nuevo})


@when(parsers.parse('elimino el grupo "{nombre}"'), target_fixture="respuesta")
def eliminar_grupo(cliente: TestClient, nombre: str) -> Response:
    return cliente.delete(f"{_RUTA}/{_grupo(cliente, nombre)['id']}")


@when(parsers.parse('añado el estado "{estado}" al grupo "{grupo}"'), target_fixture="respuesta")
def anadir_estado(cliente: TestClient, estado: str, grupo: str) -> Response:
    return cliente.post(f"{_RUTA}/{_grupo(cliente, grupo)['id']}/estados", json={"nombre": estado})


@when(
    parsers.parse('intento añadir al grupo "{grupo}" un estado con un nombre {nombre}'),
    target_fixture="respuesta",
)
def anadir_estado_invalido(cliente: TestClient, grupo: str, nombre: str) -> Response:
    ruta = f"{_RUTA}/{_grupo(cliente, grupo)['id']}/estados"
    return cliente.post(ruta, json=_NOMBRES_INVALIDOS[nombre])


@when(
    parsers.parse('renombro el estado "{estado}" del grupo "{grupo}" a "{nuevo}"'),
    target_fixture="respuesta",
)
def renombrar_estado(cliente: TestClient, estado: str, grupo: str, nuevo: str) -> Response:
    id_grupo = _grupo(cliente, grupo)["id"]
    ruta = f"{_RUTA}/{id_grupo}/estados/{_id_estado(cliente, grupo, estado)}"
    return cliente.put(ruta, json={"nombre": nuevo})


@when(parsers.parse('elimino el estado "{estado}" del grupo "{grupo}"'), target_fixture="respuesta")
def eliminar_estado(cliente: TestClient, estado: str, grupo: str) -> Response:
    id_grupo = _grupo(cliente, grupo)["id"]
    return cliente.delete(f"{_RUTA}/{id_grupo}/estados/{_id_estado(cliente, grupo, estado)}")


@when(
    parsers.parse(
        'elimino el estado "{estado}" del grupo "{grupo}" moviendo sus tareas a "{destino}"'
    ),
    target_fixture="respuesta",
)
def eliminar_estado_moviendo(
    cliente: TestClient, estado: str, grupo: str, destino: str
) -> Response:
    id_grupo = _grupo(cliente, grupo)["id"]
    ruta = f"{_RUTA}/{id_grupo}/estados/{_id_estado(cliente, grupo, estado)}"
    return cliente.delete(ruta, params={"mover_a": _id_estado_cualquiera(cliente, destino)})


@when(
    parsers.parse('reordeno los estados del grupo "{grupo}" como "{estados}"'),
    target_fixture="respuesta",
)
def reordenar_estados(cliente: TestClient, grupo: str, estados: str) -> Response:
    ids = [_id_estado(cliente, grupo, e) for e in _lista(estados)]
    return cliente.put(f"{_RUTA}/{_grupo(cliente, grupo)['id']}/orden", json={"ids": ids})


@when(
    parsers.parse('intento reordenar los estados del grupo "{grupo}" con un orden {orden}'),
    target_fixture="respuesta",
)
def reordenar_estados_invalido(cliente: TestClient, grupo: str, orden: str) -> Response:
    datos = _grupo(cliente, grupo)
    ids = [e["id"] for e in datos["estados"]]
    de_otro_grupo = _id_estado_cualquiera(cliente, "Nueva")
    cuerpos = {
        "con un estado repetido": {"ids": [*ids, ids[0]]},
        "al que le falta un estado": {"ids": ids[1:]},
        "con un estado de otro grupo": {"ids": [*ids, de_otro_grupo]},
        "con un estado que no existe": {"ids": [*ids, _ID_INEXISTENTE]},
        "vacío": {"ids": []},
        "con ids que no son enteros": {"ids": [str(i) for i in ids]},
        "ausente": {},
    }
    return cliente.put(f"{_RUTA}/{datos['id']}/orden", json=cuerpos[orden])


@when(parsers.parse("intento {operacion} un grupo que no existe"), target_fixture="respuesta")
def operar_grupo_inexistente(cliente: TestClient, operacion: str) -> Response:
    ruta = f"{_RUTA}/{_ID_INEXISTENTE}"
    id_estado = _id_estado_cualquiera(cliente, "Nueva")
    operaciones = {
        "renombrar": lambda: cliente.put(ruta, json={"nombre": "Otro"}),
        "eliminar": lambda: cliente.delete(ruta),
        "añadir un estado a": lambda: cliente.post(f"{ruta}/estados", json={"nombre": "Otro"}),
        "renombrar un estado de": lambda: cliente.put(
            f"{ruta}/estados/{id_estado}", json={"nombre": "Otro"}
        ),
        "eliminar un estado de": lambda: cliente.delete(f"{ruta}/estados/{id_estado}"),
        "reordenar los estados de": lambda: cliente.put(f"{ruta}/orden", json={"ids": [id_estado]}),
    }
    return operaciones[operacion]()


@when(
    parsers.parse('intento {operacion} el estado "{estado}" en el grupo "{grupo}"'),
    target_fixture="respuesta",
)
def operar_estado_ajeno(cliente: TestClient, operacion: str, estado: str, grupo: str) -> Response:
    id_grupo = _grupo(cliente, grupo)["id"]
    id_estado = _id_estado_cualquiera(cliente, estado)
    ruta = f"{_RUTA}/{id_grupo}/estados/{id_estado}"
    if operacion == "renombrar":
        return cliente.put(ruta, json={"nombre": "Otro"})
    return cliente.delete(ruta)


# --- Cuando: tareas ---------------------------------------------------------------


@when(parsers.parse('creo la tarea "{nombre}" sin grupo de estados'), target_fixture="respuesta")
def crear_tarea_sin_grupo(cliente: TestClient, nombre: str) -> Response:
    return cliente.post(_RUTA_TAREAS, json=_cuerpo_tarea(nombre))


@when(parsers.parse('creo la tarea "{nombre}" con el grupo "{grupo}"'), target_fixture="respuesta")
def crear_tarea_con_grupo(cliente: TestClient, nombre: str, grupo: str) -> Response:
    cuerpo = _cuerpo_tarea(nombre, grupo_estados_id=_grupo(cliente, grupo)["id"])
    return cliente.post(_RUTA_TAREAS, json=cuerpo)


@when(
    parsers.parse('creo la tarea "{nombre}" con un grupo que no existe'), target_fixture="respuesta"
)
def crear_tarea_con_grupo_inexistente(cliente: TestClient, nombre: str) -> Response:
    return cliente.post(_RUTA_TAREAS, json=_cuerpo_tarea(nombre, grupo_estados_id=_ID_INEXISTENTE))


@when(
    parsers.parse('creo la tarea "{nombre}" con grupo_estados_id {valor}'),
    target_fixture="respuesta",
)
def crear_tarea_con_valor(cliente: TestClient, nombre: str, valor: str) -> Response:
    return cliente.post(
        _RUTA_TAREAS, json=_cuerpo_tarea(nombre, grupo_estados_id=json.loads(valor))
    )


@when(
    parsers.parse('edito la tarea "{nombre}" con grupo_estados_id {valor}'),
    target_fixture="respuesta",
)
def editar_tarea_con_valor(cliente: TestClient, nombre: str, valor: str) -> Response:
    extra = {} if valor == "ausente" else {"grupo_estados_id": json.loads(valor)}
    ruta = f"{_RUTA_TAREAS}/{_id_tarea(cliente, nombre)}"
    return cliente.put(ruta, json=_cuerpo_tarea(nombre, **extra))


def _editar_con_id_de_grupo(cliente: TestClient, nombre: str, id_grupo: int) -> Response:
    cuerpo = _cuerpo_tarea(nombre, grupo_estados_id=id_grupo)
    return cliente.put(f"{_RUTA_TAREAS}/{_id_tarea(cliente, nombre)}", json=cuerpo)


@when(parsers.parse('edito la tarea "{nombre}" con el grupo "{grupo}"'), target_fixture="respuesta")
def editar_tarea_con_grupo(cliente: TestClient, nombre: str, grupo: str) -> Response:
    return _editar_con_id_de_grupo(cliente, nombre, _grupo(cliente, grupo)["id"])


@when(
    parsers.parse('edito la tarea "{nombre}" con un grupo que no existe'),
    target_fixture="respuesta",
)
def editar_tarea_con_grupo_inexistente(cliente: TestClient, nombre: str) -> Response:
    return _editar_con_id_de_grupo(cliente, nombre, _ID_INEXISTENTE)


@when(parsers.parse('muevo la tarea "{tarea}" al estado "{estado}"'), target_fixture="respuesta")
def mover_tarea(cliente: TestClient, tarea: str, estado: str) -> Response:
    ruta = f"{_RUTA_TAREAS}/{_id_tarea(cliente, tarea)}/estado"
    return cliente.patch(ruta, json={"estado_id": _id_estado_cualquiera(cliente, estado)})


@when(
    parsers.parse('muevo una tarea que no existe al estado "{estado}"'), target_fixture="respuesta"
)
def mover_tarea_inexistente(cliente: TestClient, estado: str) -> Response:
    ruta = f"{_RUTA_TAREAS}/{_ID_INEXISTENTE}/estado"
    return cliente.patch(ruta, json={"estado_id": _id_estado_cualquiera(cliente, estado)})


@when(
    parsers.parse('cambio el estado de la tarea "{tarea}" con el cuerpo {cuerpo}'),
    target_fixture="respuesta",
)
def cambiar_estado_con_cuerpo(cliente: TestClient, tarea: str, cuerpo: str) -> Response:
    ruta = f"{_RUTA_TAREAS}/{_id_tarea(cliente, tarea)}/estado"
    return cliente.patch(ruta, json=json.loads(cuerpo))


# --- Entonces: grupos -------------------------------------------------------------


@then("la API devuelve una lista de grupos vacía")
def lista_vacia(respuesta: Response) -> None:
    assert respuesta.status_code == 200
    assert respuesta.json() == []


@then(parsers.parse('la API responde que el grupo "{nombre}" se ha creado sin estados'))
def grupo_creado(respuesta: Response, nombre: str) -> None:
    assert respuesta.status_code == 201
    _comprobar_grupo(respuesta.json(), nombre, [])
    assert respuesta.json()["tareas"] == 0


@then("la API responde que el grupo se ha creado con ese nombre")
def grupo_de_50_creado(respuesta: Response) -> None:
    grupo_creado(respuesta, "n" * 50)
    assert _grupos_guardados() == ["n" * 50]


@then(parsers.parse('se guardan los grupos "{nombres}"'))
def grupos_guardados(cliente: TestClient, nombres: str) -> None:
    esperados = _lista(nombres)
    assert sorted(_grupos_guardados(), key=str.casefold) == esperados
    assert [g["nombre"] for g in _grupos(cliente)] == esperados


@then(parsers.parse('se guardan los estados "{nombres}"'))
def estados_guardados_en_total(nombres: str) -> None:
    filas = _consultar("SELECT nombre FROM estados_grupo ORDER BY id")
    assert [f[0] for f in filas] == _lista(nombres)


@then(parsers.parse('la API devuelve los grupos "{nombres}"'))
def la_api_devuelve_los_grupos(respuesta: Response, nombres: str) -> None:
    assert respuesta.status_code == 200
    assert [g["nombre"] for g in respuesta.json()] == _lista(nombres)


@then(parsers.parse('el grupo "{grupo}" tiene los estados "{estados}"'))
def grupo_de_la_respuesta_con_estados(respuesta: Response, grupo: str, estados: str) -> None:
    datos = next(g for g in respuesta.json() if g["nombre"] == grupo)
    _comprobar_grupo(datos, grupo, _lista(estados))


@then(parsers.parse('la API responde que ya existe un grupo de estados llamado "{nombre}"'))
def grupo_duplicado(respuesta: Response, nombre: str) -> None:
    assert respuesta.status_code == 409
    assert respuesta.json() == {"detalle": f"Ya existe un grupo de estados llamado «{nombre}»"}


@then(parsers.parse('la API responde con el grupo "{grupo}" y los estados "{estados}"'))
def responde_con_el_grupo(respuesta: Response, grupo: str, estados: str) -> None:
    assert respuesta.status_code == 200
    _comprobar_grupo(respuesta.json(), grupo, _lista(estados))


@then(parsers.parse('la API responde con el grupo "{grupo}" sin estados'))
def responde_con_el_grupo_sin_estados(respuesta: Response, grupo: str) -> None:
    assert respuesta.status_code == 200
    _comprobar_grupo(respuesta.json(), grupo, [])


@then(parsers.parse('el grupo "{grupo}" no guarda estados'))
def grupo_sin_estados_guardados(cliente: TestClient, grupo: str) -> None:
    assert _estados_guardados(grupo) == []
    _comprobar_grupo(_grupo(cliente, grupo), grupo, [])


@then(parsers.parse('la API responde 201 con el grupo "{grupo}" y los estados "{estados}"'))
def responde_201_con_el_grupo(respuesta: Response, grupo: str, estados: str) -> None:
    assert respuesta.status_code == 201
    _comprobar_grupo(respuesta.json(), grupo, _lista(estados))


@then("la API responde que el grupo se ha eliminado")
def grupo_eliminado(respuesta: Response) -> None:
    assert respuesta.status_code == 204
    assert respuesta.content == b""


@then(parsers.parse('el grupo "{grupo}" guarda los estados "{estados}"'))
def grupo_guarda_estados(cliente: TestClient, grupo: str, estados: str) -> None:
    esperados = _lista(estados)
    assert _estados_guardados(grupo) == list(enumerate(esperados, start=1))
    _comprobar_grupo(_grupo(cliente, grupo), grupo, esperados)


@then(
    parsers.parse(
        'la API responde que ya existe un estado llamado "{nombre}" en el grupo "{grupo}"'
    )
)
def estado_duplicado(respuesta: Response, nombre: str, grupo: str) -> None:
    assert respuesta.status_code == 409
    assert respuesta.json() == {
        "detalle": f"Ya existe un estado llamado «{nombre}» en el grupo de estados «{grupo}»"
    }


@then("la API rechaza la operación por datos inválidos")
def datos_invalidos(respuesta: Response) -> None:
    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]


@then("la API responde que el grupo de estados no existe")
def grupo_inexistente(respuesta: Response) -> None:
    assert respuesta.status_code == 404
    assert respuesta.json() == {
        "detalle": f"No existe el grupo de estados con id {_ID_INEXISTENTE}"
    }


@then(parsers.parse('la API responde que el estado no es del grupo "{grupo}"'))
def estado_de_otro_grupo(cliente: TestClient, respuesta: Response, grupo: str) -> None:
    assert respuesta.status_code == 404
    detalle = respuesta.json()["detalle"]
    id_grupo = _grupo(cliente, grupo)["id"]
    assert detalle.startswith("No existe el estado con id ")
    assert detalle.endswith(f" en el grupo de estados con id {id_grupo}")


@then(parsers.parse('el grupo "{grupo}" tiene {total:d} tareas: {detalle}'))
def grupo_con_tareas(respuesta: Response, grupo: str, total: int, detalle: str) -> None:
    datos = next(g for g in respuesta.json() if g["nombre"] == grupo)
    assert datos["tareas"] == total
    esperados = []
    for parte in detalle.split(", "):
        nombre, cuantas = parte.rsplit(" ", 1)
        esperados.append((nombre.strip('"'), int(cuantas)))
    assert [(e["nombre"], e["tareas"]) for e in datos["estados"]] == esperados


@then(parsers.parse('el grupo "{grupo}" tiene {total:d} tareas'))
def grupo_con_tareas_sin_estados(respuesta: Response, grupo: str, total: int) -> None:
    datos = next(g for g in respuesta.json() if g["nombre"] == grupo)
    assert (datos["tareas"], datos["estados"]) == (total, [])


@then(parsers.parse('el estado "{estado}" del grupo "{grupo}" tiene {total:d} tareas'))
def estado_con_tareas(respuesta: Response, estado: str, grupo: str, total: int) -> None:
    datos = respuesta.json()
    assert datos["nombre"] == grupo
    assert next(e for e in datos["estados"] if e["nombre"] == estado)["tareas"] == total
    assert datos["tareas"] == sum(e["tareas"] for e in datos["estados"])


@then(
    parsers.parse(
        'la API responde que el estado "{estado}" tiene {total:d} tareas '
        "y hay que indicar a dónde moverlas"
    )
)
def estado_con_tareas_sin_destino(respuesta: Response, estado: str, total: int) -> None:
    assert respuesta.status_code == 409
    assert respuesta.json() == {
        "detalle": (
            f"El estado «{estado}» tiene {total} tareas: indica en mover_a a qué otro "
            "estado del grupo moverlas"
        )
    }


@then(
    parsers.parse('la API responde que hay que mover las tareas a otro estado del grupo "{grupo}"')
)
def destino_invalido(respuesta: Response, grupo: str) -> None:
    assert respuesta.status_code == 409
    detalle = respuesta.json()["detalle"]
    assert detalle.startswith(f"mover_a debe ser otro estado del grupo de estados «{grupo}»")


# --- Entonces: tareas -------------------------------------------------------------


def _comprobar_tarea(respuesta: Response, codigo: int, grupo: str | None, estado: str | None):
    assert respuesta.status_code == codigo
    cuerpo = respuesta.json()
    assert "grupo_estados" in cuerpo
    assert "estado" in cuerpo
    if grupo is None:
        assert (cuerpo["grupo_estados"], cuerpo["estado"]) == (None, None)
        return
    assert set(cuerpo["grupo_estados"]) == {"id", "nombre"}
    assert set(cuerpo["estado"]) == {"id", "nombre"}
    assert (cuerpo["grupo_estados"]["nombre"], cuerpo["estado"]["nombre"]) == (grupo, estado)


@then("la API responde 201 con la tarea sin grupo ni estado")
def tarea_201_sin_grupo(respuesta: Response) -> None:
    _comprobar_tarea(respuesta, 201, None, None)


@then("la API responde 200 con la tarea sin grupo ni estado")
def tarea_200_sin_grupo(respuesta: Response) -> None:
    _comprobar_tarea(respuesta, 200, None, None)


@then(
    parsers.parse(
        'la API responde {codigo:d} con la tarea en el grupo "{grupo}" y el estado "{estado}"'
    )
)
def tarea_con_grupo_y_estado(
    cliente: TestClient, respuesta: Response, codigo: int, grupo: str, estado: str
) -> None:
    _comprobar_tarea(respuesta, codigo, grupo, estado)
    cuerpo = respuesta.json()
    assert cuerpo["grupo_estados"]["id"] == _grupo(cliente, grupo)["id"]
    assert cuerpo["estado"]["id"] == _id_estado(cliente, grupo, estado)


@then(parsers.parse('la tarea "{tarea}" se guarda sin grupo ni estado'))
def tarea_guardada_sin_grupo(cliente: TestClient, tarea: str) -> None:
    assert _grupo_y_estado_guardados(tarea) == (None, None)
    datos = next(t for t in cliente.get(_RUTA_TAREAS).json() if t["nombre"] == tarea)
    assert (datos["grupo_estados"], datos["estado"]) == (None, None)


@then(parsers.parse('la tarea "{tarea}" se guarda en el grupo "{grupo}" y el estado "{estado}"'))
def tarea_guardada_con_grupo(cliente: TestClient, tarea: str, grupo: str, estado: str) -> None:
    assert _grupo_y_estado_guardados(tarea) == (grupo, estado)
    datos = next(t for t in cliente.get(_RUTA_TAREAS).json() if t["nombre"] == tarea)
    assert (datos["grupo_estados"]["nombre"], datos["estado"]["nombre"]) == (grupo, estado)


@then("no se guarda ninguna tarea")
def ninguna_tarea() -> None:
    assert _consultar("SELECT COUNT(*) FROM tareas") == [(0,)]


def _error_de_validacion(respuesta: Response, campo: str) -> str:
    assert respuesta.status_code == 422
    (error,) = respuesta.json()["detail"]
    assert error["loc"] == ["body", campo]
    return error["msg"]


@then("la API rechaza la tarea porque no existe el grupo")
def tarea_con_grupo_inexistente(respuesta: Response) -> None:
    mensaje = _error_de_validacion(respuesta, "grupo_estados_id")
    assert mensaje == f"No existe el grupo de estados con id {_ID_INEXISTENTE}"


@then(parsers.parse('la API rechaza la tarea porque el grupo "{grupo}" no tiene estados'))
def tarea_con_grupo_sin_estados(respuesta: Response, grupo: str) -> None:
    mensaje = _error_de_validacion(respuesta, "grupo_estados_id")
    assert mensaje == (
        f"El grupo de estados «{grupo}» no tiene estados: añade al menos uno antes de "
        "asignarlo a una tarea"
    )


@then("la API rechaza el cambio de estado porque la tarea no tiene grupo")
def tarea_sin_grupo_no_se_mueve(cliente: TestClient, respuesta: Response) -> None:
    mensaje = _error_de_validacion(respuesta, "estado_id")
    assert mensaje == f"La tarea con id {_id_tarea(cliente, 'Informe')} no tiene grupo de estados"


@then(
    parsers.parse('la API rechaza el cambio de estado porque el estado no es del grupo "{grupo}"')
)
def estado_ajeno_a_la_tarea(respuesta: Response, grupo: str) -> None:
    mensaje = _error_de_validacion(respuesta, "estado_id")
    assert mensaje.startswith("El estado con id ")
    assert mensaje.endswith(f" no es del grupo de estados «{grupo}» de la tarea")


@then("la API responde que la tarea no existe")
def tarea_inexistente(respuesta: Response) -> None:
    assert respuesta.status_code == 404
    assert respuesta.json() == {"detalle": f"No existe la tarea con id {_ID_INEXISTENTE}"}


@then(parsers.parse('el resto de datos de la tarea "{tarea}" no cambia'))
def resto_sin_cambios(cliente: TestClient, respuesta: Response, tarea: str) -> None:
    assert respuesta.status_code == 200
    guardada = next(t for t in cliente.get(_RUTA_TAREAS).json() if t["nombre"] == tarea)
    esperada = {
        "nombre": tarea,
        "descripcion": f"Descripción de {tarea}",
        "fecha_creacion": "2026-11-11T10:00:00",
        "fecha_vencimiento": None,
        "prioridad": None,
        "etiquetas": [],
        "asignados": [],
        "tipo": None,
        "oportunidad": None,
        "completada": False,
        "subtareas": [],
    }
    for campo, valor in esperada.items():
        assert respuesta.json()[campo] == valor
        assert guardada[campo] == valor
    assert respuesta.json() == guardada
