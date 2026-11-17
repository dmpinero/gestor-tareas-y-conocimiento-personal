from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from pytest_bdd import given, parsers, scenarios, then, when
from sqlalchemy import text

from gestor_tareas.infraestructura.persistencia.sesion import FabricaSesiones

scenarios("contador_congelado.feature")

_RUTA_GRUPOS = "/api/v1/grupos-estados"
_RUTA_TAREAS = "/api/v1/tareas"


def _lista(texto: str) -> list[str]:
    return texto.split(", ") if texto else []


def _ahora() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def _instante(texto: str) -> datetime:
    return datetime.fromisoformat(texto.replace("Z", "+00:00"))


def _ejecutar(sql: str, **parametros) -> list[tuple]:
    sesion = FabricaSesiones()
    try:
        resultado = sesion.execute(text(sql), parametros)
        filas = [tuple(f) for f in resultado] if resultado.returns_rows else []
        sesion.commit()
        return filas
    finally:
        sesion.close()


@pytest.fixture(autouse=True)
def intervalo() -> dict[str, datetime]:
    """Instantes entre los que ocurre la operación de la prueba (en UTC, sin fracción)."""
    return {"desde": _ahora()}


def _congelada_guardada(nombre: str) -> datetime | None:
    filas = _ejecutar("SELECT congelada_en FROM tareas WHERE nombre = :n", n=nombre)
    assert len(filas) == 1
    valor = filas[0][0]
    # La columna guarda el instante en UTC sin la zona.
    return valor.replace(tzinfo=UTC) if valor is not None else None


def _grupo(cliente: TestClient, nombre: str) -> dict:
    return next(g for g in cliente.get(_RUTA_GRUPOS).json() if g["nombre"] == nombre)


def _id_estado(cliente: TestClient, grupo: dict, estado: str) -> int:
    return next(e["id"] for e in grupo["estados"] if e["nombre"] == estado)


def _tarea(cliente: TestClient, nombre: str) -> dict:
    return next(t for t in cliente.get(_RUTA_TAREAS).json() if t["nombre"] == nombre)


def _cuerpo(nombre: str, vencimiento: str | None, grupo: dict | None) -> dict:
    return {
        "nombre": nombre,
        "descripcion": f"Descripción de {nombre}",
        "fecha_creacion": "2026-11-11T10:00:00",
        "fecha_vencimiento": vencimiento,
        "grupo_estados_id": grupo["id"] if grupo else None,
    }


# --- Dado ----------------------------------------------------------------------


@given(parsers.parse('que hay un grupo "{nombre}" con los estados "{estados}"'))
def grupo_con_estados(cliente: TestClient, nombre: str, estados: str) -> None:
    respuesta = cliente.post(_RUTA_GRUPOS, json={"nombre": nombre})
    assert respuesta.status_code == 201
    for estado in _lista(estados):
        ruta = f"{_RUTA_GRUPOS}/{respuesta.json()['id']}/estados"
        assert cliente.post(ruta, json={"nombre": estado}).status_code == 201


@given(
    parsers.parse(
        'que existe la tarea "{nombre}" en el grupo "{grupo}" con vencimiento "{vencimiento}"'
    )
)
def tarea_con_vencimiento(cliente: TestClient, nombre: str, grupo: str, vencimiento: str) -> None:
    cuerpo = _cuerpo(nombre, vencimiento, _grupo(cliente, grupo))
    assert cliente.post(_RUTA_TAREAS, json=cuerpo).status_code == 201


@given(parsers.parse('que existe la tarea "{nombre}" en el grupo "{grupo}" sin vencimiento'))
def tarea_sin_vencimiento(cliente: TestClient, nombre: str, grupo: str) -> None:
    cuerpo = _cuerpo(nombre, None, _grupo(cliente, grupo))
    assert cliente.post(_RUTA_TAREAS, json=cuerpo).status_code == 201


def _fijar_instante(nombre: str, instante: str) -> None:
    """Simula que la tarea se congeló en ese instante pasado."""
    valor = _instante(instante).astimezone(UTC).replace(tzinfo=None)
    _ejecutar("UPDATE tareas SET congelada_en = :v WHERE nombre = :n", v=valor, n=nombre)


@given(parsers.parse('que la tarea "{nombre}" está completada y congelada desde "{instante}"'))
def completada_desde(cliente: TestClient, nombre: str, instante: str) -> None:
    marcar(cliente, nombre, True)
    _fijar_instante(nombre, instante)


@given(parsers.parse('que la tarea "{nombre}" está en DONE y congelada desde "{instante}"'))
def en_done_desde(cliente: TestClient, nombre: str, instante: str) -> None:
    mover(cliente, nombre, "DONE")
    _fijar_instante(nombre, instante)


@given(
    parsers.parse('que la tarea "{nombre}" está en DONE, completada y congelada desde "{instante}"')
)
def en_done_y_completada_desde(cliente: TestClient, nombre: str, instante: str) -> None:
    mover(cliente, nombre, "DONE")
    marcar(cliente, nombre, True)
    _fijar_instante(nombre, instante)


# --- Cuando --------------------------------------------------------------------


def marcar(cliente: TestClient, nombre: str, completada: bool) -> Response:
    ruta = f"{_RUTA_TAREAS}/{_tarea(cliente, nombre)['id']}/completada"
    respuesta = cliente.patch(ruta, json={"completada": completada})
    assert respuesta.status_code == 200
    return respuesta


def mover(cliente: TestClient, nombre: str, estado: str) -> Response:
    tarea = _tarea(cliente, nombre)
    grupo = next(
        g for g in cliente.get(_RUTA_GRUPOS).json() if g["id"] == tarea["grupo_estados"]["id"]
    )
    ruta = f"{_RUTA_TAREAS}/{tarea['id']}/estado"
    respuesta = cliente.patch(ruta, json={"estado_id": _id_estado(cliente, grupo, estado)})
    assert respuesta.status_code == 200
    return respuesta


@when(parsers.parse('marco la tarea "{nombre}" como completada'), target_fixture="respuesta")
def marcar_completada(cliente: TestClient, nombre: str) -> Response:
    return marcar(cliente, nombre, True)


@when(parsers.parse('desmarco la tarea "{nombre}" como completada'), target_fixture="respuesta")
def desmarcar_completada(cliente: TestClient, nombre: str) -> Response:
    return marcar(cliente, nombre, False)


@given(parsers.parse('que muevo la tarea "{nombre}" al estado "{estado}"'))
@when(parsers.parse('muevo la tarea "{nombre}" al estado "{estado}"'), target_fixture="respuesta")
def mover_tarea(cliente: TestClient, nombre: str, estado: str) -> Response:
    return mover(cliente, nombre, estado)


@when(
    parsers.parse('edito la tarea "{nombre}" con vencimiento "{vencimiento}" y el grupo "{grupo}"'),
    target_fixture="respuesta",
)
def editar_con_grupo(cliente: TestClient, nombre: str, vencimiento: str, grupo: str) -> Response:
    ruta = f"{_RUTA_TAREAS}/{_tarea(cliente, nombre)['id']}"
    return cliente.put(ruta, json=_cuerpo(nombre, vencimiento, _grupo(cliente, grupo)))


@when(
    parsers.parse('edito la tarea "{nombre}" con vencimiento "{vencimiento}" y sin grupo'),
    target_fixture="respuesta",
)
def editar_sin_grupo(cliente: TestClient, nombre: str, vencimiento: str) -> Response:
    ruta = f"{_RUTA_TAREAS}/{_tarea(cliente, nombre)['id']}"
    return cliente.put(ruta, json=_cuerpo(nombre, vencimiento, None))


@when(
    parsers.parse('creo la tarea "{nombre}" en el grupo "{grupo}" con vencimiento "{vencimiento}"'),
    target_fixture="respuesta",
)
def crear(cliente: TestClient, nombre: str, grupo: str, vencimiento: str) -> Response:
    return cliente.post(_RUTA_TAREAS, json=_cuerpo(nombre, vencimiento, _grupo(cliente, grupo)))


@when(parsers.parse('cambio el nombre del estado "{estado}" del grupo "{grupo}" a "{nuevo}"'))
def renombrar_estado(cliente: TestClient, estado: str, grupo: str, nuevo: str) -> None:
    datos = _grupo(cliente, grupo)
    ruta = f"{_RUTA_GRUPOS}/{datos['id']}/estados/{_id_estado(cliente, datos, estado)}"
    assert cliente.put(ruta, json={"nombre": nuevo}).status_code == 200


@when(
    parsers.parse('borro el estado "{estado}" del grupo "{grupo}" pasando sus tareas a "{destino}"')
)
def eliminar_estado(cliente: TestClient, estado: str, grupo: str, destino: str) -> None:
    datos = _grupo(cliente, grupo)
    ruta = f"{_RUTA_GRUPOS}/{datos['id']}/estados/{_id_estado(cliente, datos, estado)}"
    respuesta = cliente.delete(ruta, params={"mover_a": _id_estado(cliente, datos, destino)})
    assert respuesta.status_code == 200


@when(parsers.parse('borro el grupo "{grupo}"'))
def eliminar_grupo(cliente: TestClient, grupo: str) -> None:
    respuesta = cliente.delete(f"{_RUTA_GRUPOS}/{_grupo(cliente, grupo)['id']}")
    assert respuesta.status_code == 204


# --- Entonces ------------------------------------------------------------------


def _comprobar_en_este_instante(valor: datetime | None, intervalo: dict[str, datetime]) -> None:
    assert valor is not None
    assert intervalo["desde"] <= valor <= _ahora()


@then(
    parsers.parse("la API responde {codigo:d} con la tarea congelada en este instante"),
)
def responde_congelada_ahora(
    respuesta: Response, codigo: int, intervalo: dict[str, datetime]
) -> None:
    assert respuesta.status_code == codigo
    texto = respuesta.json()["congelada_en"]
    # Instante en UTC con precisión de segundos y "Z" final.
    assert texto.endswith("Z") and len(texto) == len("2026-11-01T08:00:00Z")
    _comprobar_en_este_instante(_instante(texto), intervalo)


@then(parsers.parse('la API responde {codigo:d} con la tarea congelada desde "{instante}"'))
def responde_congelada_desde(respuesta: Response, codigo: int, instante: str) -> None:
    assert respuesta.status_code == codigo
    assert respuesta.json()["congelada_en"] == instante


@then(parsers.parse("la API responde {codigo:d} con la tarea sin congelar"))
def responde_sin_congelar(respuesta: Response, codigo: int) -> None:
    assert respuesta.status_code == codigo
    cuerpo = respuesta.json()
    assert "congelada_en" in cuerpo
    assert cuerpo["congelada_en"] is None


@then(parsers.parse('la respuesta tiene el vencimiento "{vencimiento}"'))
def respuesta_con_vencimiento(respuesta: Response, vencimiento: str) -> None:
    assert respuesta.json()["fecha_vencimiento"] == vencimiento


@then("la respuesta no tiene vencimiento")
def respuesta_sin_vencimiento(respuesta: Response) -> None:
    assert respuesta.json()["fecha_vencimiento"] is None


@then(parsers.parse('la tarea "{nombre}" se guarda congelada en este instante'))
def guardada_congelada_ahora(nombre: str, intervalo: dict[str, datetime]) -> None:
    _comprobar_en_este_instante(_congelada_guardada(nombre), intervalo)


@then(parsers.parse('la tarea "{nombre}" se guarda congelada desde "{instante}"'))
def guardada_congelada_desde(nombre: str, instante: str) -> None:
    assert _congelada_guardada(nombre) == _instante(instante)


@then(parsers.parse('la tarea "{nombre}" no está congelada'))
def no_congelada(cliente: TestClient, nombre: str) -> None:
    assert _congelada_guardada(nombre) is None
    assert _tarea(cliente, nombre)["congelada_en"] is None


@then(parsers.parse('el listado muestra la tarea "{nombre}" congelada desde "{instante}"'))
def listado_congelada(cliente: TestClient, nombre: str, instante: str) -> None:
    assert _tarea(cliente, nombre)["congelada_en"] == instante
