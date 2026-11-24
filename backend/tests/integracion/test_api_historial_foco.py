"""API del historial del foco: un periodo por cada vez que se fija el foco, que se
cierra al fijar otro, al quitarlo o al borrar la tarea o la subtarea en foco. Los
nombres son los actuales mientras existen y, si se borran, los del momento."""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from gestor_tareas.infraestructura.persistencia.sesion import FabricaSesiones
from gestor_tareas.main import crear_aplicacion
from tests.integracion.tablas import vaciar_tablas

_FOCO = "/api/v1/foco"
_HISTORIAL = "/api/v1/foco/historial"
_TAREAS = "/api/v1/tareas"
_TAREA = {
    "nombre": "Migración portal",
    "descripcion": "Pasar el portal a la nube",
    "fecha_creacion": "2026-11-10T09:00:00",
}
_CAMPOS = {"id", "tarea_id", "tarea_nombre", "subtarea_id", "subtarea_nombre", "desde", "hasta"}


@pytest.fixture
def cliente() -> TestClient:
    sesion = FabricaSesiones()
    try:
        vaciar_tablas(sesion)
    finally:
        sesion.close()
    return TestClient(crear_aplicacion())


def _crear_tarea(cliente: TestClient, nombre: str = "Migración portal") -> dict:
    respuesta = cliente.post(_TAREAS, json={**_TAREA, "nombre": nombre})
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _anadir_subtarea(cliente: TestClient, id_tarea: int, nombre: str) -> dict:
    respuesta = cliente.post(f"{_TAREAS}/{id_tarea}/subtareas", json={"nombre": nombre})
    assert respuesta.status_code == 201, respuesta.text
    return next(s for s in respuesta.json()["subtareas"] if s["nombre"] == nombre)


def _fijar(cliente: TestClient, id_tarea: int, id_subtarea: int | None = None) -> dict:
    respuesta = cliente.put(_FOCO, json={"tarea_id": id_tarea, "subtarea_id": id_subtarea})
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _historial(cliente: TestClient, **filtros: str) -> list[dict]:
    respuesta = cliente.get(_HISTORIAL, params=filtros)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _ejecutar(sql: str, **parametros) -> None:
    sesion = FabricaSesiones()
    try:
        sesion.execute(text(sql), parametros)
        sesion.commit()
    finally:
        sesion.close()


def _fechar(id_periodo: int, desde: str, hasta: str | None) -> None:
    """Pone a mano el inicio y el fin de un periodo, para controlar el tiempo."""
    _ejecutar(
        "UPDATE historial_foco SET desde = :desde, hasta = :hasta WHERE id = :id",
        id=id_periodo,
        desde=desde,
        hasta=hasta,
    )


def _instante(texto: str) -> datetime:
    assert texto.endswith("Z")
    return datetime.fromisoformat(texto)


def test_sin_historial_devuelve_una_lista_vacia(cliente: TestClient) -> None:
    assert _historial(cliente) == []


def test_fijar_abre_un_periodo_en_curso_con_el_mismo_desde_que_el_foco(
    cliente: TestClient,
) -> None:
    tarea = _crear_tarea(cliente)
    subtarea = _anadir_subtarea(cliente, tarea["id"], "Copiar la base de datos")

    foco = _fijar(cliente, tarea["id"], subtarea["id"])

    periodos = _historial(cliente)
    assert len(periodos) == 1
    assert set(periodos[0]) == _CAMPOS
    assert isinstance(periodos[0]["id"], int)
    assert {k: v for k, v in periodos[0].items() if k != "id"} == {
        "tarea_id": tarea["id"],
        "tarea_nombre": "Migración portal",
        "subtarea_id": subtarea["id"],
        "subtarea_nombre": "Copiar la base de datos",
        "desde": foco["desde"],
        "hasta": None,
    }


def test_fijar_otra_cierra_el_periodo_anterior_cuando_empieza_el_nuevo(
    cliente: TestClient,
) -> None:
    primera = _crear_tarea(cliente, "Primera")
    segunda = _crear_tarea(cliente, "Segunda")
    _fijar(cliente, primera["id"])
    _fechar(_historial(cliente)[0]["id"], "2026-01-01 08:00:00", None)

    foco = _fijar(cliente, segunda["id"])

    nuevo, anterior = _historial(cliente)
    assert (nuevo["tarea_id"], nuevo["tarea_nombre"]) == (segunda["id"], "Segunda")
    assert nuevo["desde"] == foco["desde"]
    assert nuevo["hasta"] is None
    assert (anterior["tarea_id"], anterior["tarea_nombre"]) == (primera["id"], "Primera")
    assert anterior["desde"] == "2026-01-01T08:00:00Z"
    assert anterior["hasta"] == foco["desde"]


def test_volver_a_fijar_la_misma_abre_otro_periodo(cliente: TestClient) -> None:
    tarea = _crear_tarea(cliente)
    _fijar(cliente, tarea["id"])
    _fechar(_historial(cliente)[0]["id"], "2026-01-01 08:00:00", None)

    _fijar(cliente, tarea["id"])

    periodos = _historial(cliente)
    assert [p["tarea_id"] for p in periodos] == [tarea["id"], tarea["id"]]
    assert periodos[0]["hasta"] is None
    assert periodos[1]["hasta"] == periodos[0]["desde"]


def test_quitar_el_foco_cierra_el_periodo_en_curso(cliente: TestClient) -> None:
    tarea = _crear_tarea(cliente)
    _fijar(cliente, tarea["id"])
    antes = datetime.now(UTC).replace(microsecond=0)

    assert cliente.delete(_FOCO).status_code == 204

    (periodo,) = _historial(cliente)
    assert periodo["tarea_id"] == tarea["id"]
    assert antes <= _instante(periodo["hasta"]) <= datetime.now(UTC)


def test_quitar_el_foco_sin_foco_no_anade_nada(cliente: TestClient) -> None:
    tarea = _crear_tarea(cliente)
    _fijar(cliente, tarea["id"])
    cliente.delete(_FOCO)
    cerrado = _historial(cliente)

    assert cliente.delete(_FOCO).status_code == 204

    assert _historial(cliente) == cerrado


def test_borrar_la_tarea_en_foco_cierra_su_periodo_y_conserva_el_nombre(
    cliente: TestClient,
) -> None:
    tarea = _crear_tarea(cliente)
    subtarea = _anadir_subtarea(cliente, tarea["id"], "Paso")
    _fijar(cliente, tarea["id"], subtarea["id"])
    antes = datetime.now(UTC).replace(microsecond=0)

    assert cliente.delete(f"{_TAREAS}/{tarea['id']}").status_code == 204

    (periodo,) = _historial(cliente)
    assert periodo["tarea_id"] is None
    assert periodo["tarea_nombre"] == "Migración portal"
    assert periodo["subtarea_id"] is None
    assert periodo["subtarea_nombre"] == "Paso"
    assert antes <= _instante(periodo["hasta"]) <= datetime.now(UTC)
    assert cliente.get(_FOCO).json() is None


def test_borrar_la_subtarea_en_foco_cierra_su_periodo_y_conserva_la_tarea(
    cliente: TestClient,
) -> None:
    tarea = _crear_tarea(cliente)
    subtarea = _anadir_subtarea(cliente, tarea["id"], "Paso")
    _fijar(cliente, tarea["id"], subtarea["id"])

    borrado = cliente.delete(f"{_TAREAS}/{tarea['id']}/subtareas/{subtarea['id']}")
    assert borrado.status_code == 200, borrado.text

    (periodo,) = _historial(cliente)
    assert periodo["tarea_id"] == tarea["id"]
    assert periodo["tarea_nombre"] == "Migración portal"
    assert periodo["subtarea_id"] is None
    assert periodo["subtarea_nombre"] == "Paso"
    assert periodo["hasta"] is not None
    assert cliente.get(_FOCO).json() is None


def test_borrar_una_tarea_que_no_esta_en_foco_no_toca_el_historial(cliente: TestClient) -> None:
    en_foco = _crear_tarea(cliente, "En foco")
    antigua = _crear_tarea(cliente, "Antigua")
    _fijar(cliente, antigua["id"])
    foco = _fijar(cliente, en_foco["id"])
    antes = _historial(cliente)

    assert cliente.delete(f"{_TAREAS}/{antigua['id']}").status_code == 204

    despues = _historial(cliente)
    assert despues[0] == antes[0]
    assert despues[0]["hasta"] is None
    # El periodo cerrado de la borrada pierde el id y conserva el nombre.
    assert despues[1] == {**antes[1], "tarea_id": None}
    assert cliente.get(_FOCO).json() == foco


def test_borrar_otra_subtarea_de_la_tarea_en_foco_no_cierra_el_periodo(
    cliente: TestClient,
) -> None:
    tarea = _crear_tarea(cliente)
    subtarea = _anadir_subtarea(cliente, tarea["id"], "Paso")
    otra = _anadir_subtarea(cliente, tarea["id"], "Otro paso")
    _fijar(cliente, tarea["id"], subtarea["id"])
    antes = _historial(cliente)

    cliente.delete(f"{_TAREAS}/{tarea['id']}/subtareas/{otra['id']}")

    assert _historial(cliente) == antes


def test_el_historial_muestra_el_nombre_actual_mientras_existe(cliente: TestClient) -> None:
    tarea = _crear_tarea(cliente)
    subtarea = _anadir_subtarea(cliente, tarea["id"], "Paso")
    _fijar(cliente, tarea["id"], subtarea["id"])

    editada = cliente.put(f"{_TAREAS}/{tarea['id']}", json={**_TAREA, "nombre": "Portal v2"})
    assert editada.status_code == 200, editada.text
    paso = cliente.put(
        f"{_TAREAS}/{tarea['id']}/subtareas/{subtarea['id']}", json={"nombre": "Paso 2"}
    )
    assert paso.status_code == 200, paso.text

    (periodo,) = _historial(cliente)
    assert (periodo["tarea_nombre"], periodo["subtarea_nombre"]) == ("Portal v2", "Paso 2")

    cliente.delete(f"{_TAREAS}/{tarea['id']}")

    # Borrada, queda el nombre que tenía al ponerla en foco.
    (periodo,) = _historial(cliente)
    assert (periodo["tarea_nombre"], periodo["subtarea_nombre"]) == ("Migración portal", "Paso")


def test_el_historial_va_del_mas_reciente_al_mas_antiguo(cliente: TestClient) -> None:
    tareas = [_crear_tarea(cliente, f"T{i}") for i in range(3)]
    for tarea in tareas:
        _fijar(cliente, tarea["id"])
    ids = sorted(p["id"] for p in _historial(cliente))
    _fechar(ids[0], "2026-11-24 10:00:00", "2026-11-24 11:00:00")
    _fechar(ids[1], "2026-11-24 09:00:00", "2026-11-24 10:00:00")
    # Mismo inicio que el primero: desempata el id, el mayor antes.
    _fechar(ids[2], "2026-11-24 10:00:00", None)

    assert [p["id"] for p in _historial(cliente)] == [ids[2], ids[0], ids[1]]


def test_el_filtro_incluye_desde_y_excluye_hasta(cliente: TestClient) -> None:
    tareas = [_crear_tarea(cliente, f"T{i}") for i in range(4)]
    for tarea in tareas:
        _fijar(cliente, tarea["id"])
    ids = sorted(p["id"] for p in _historial(cliente))
    for id_periodo, desde in zip(
        ids,
        [
            "2026-11-23 22:59:59",
            "2026-11-23 23:00:00",
            "2026-11-24 22:59:59",
            "2026-11-24 23:00:00",
        ],
        strict=True,
    ):
        _fechar(id_periodo, desde, None if id_periodo == ids[-1] else desde)

    # Un día de Madrid (UTC+1), con la zona en el instante.
    dia = _historial(cliente, desde="2026-11-24T00:00:00+01:00", hasta="2026-11-25T00:00:00+01:00")
    assert [p["id"] for p in dia] == [ids[2], ids[1]]
    assert _historial(cliente, desde="2026-11-23T23:00:00Z", hasta="2026-11-24T23:00:00Z") == dia
    assert [p["id"] for p in _historial(cliente, desde="2026-11-24T23:00:00Z")] == [ids[3]]
    assert [p["id"] for p in _historial(cliente, hasta="2026-11-23T23:00:00Z")] == [ids[0]]


@pytest.mark.parametrize(
    "filtros",
    [
        {"desde": "ayer"},
        {"hasta": "0.5"},  # Un número no es un instante (Pydantic lo leería como segundos).
        {"desde": "1732406400"},
        {"hasta": "2026-13-01T00:00:00Z"},
        {"desde": "2026-11-24T00:00:00"},  # Sin zona: no es un instante.
        {"desde": "2026-11-24T10:00:00Z", "hasta": "2026-11-24T10:00:00Z"},
        {"desde": "2026-11-24T10:00:00Z", "hasta": "2026-11-24T09:00:00Z"},
        {"desde": "2026-11-24T10:00:00Z", "hasta": "2026-11-24T11:00:00+02:00"},
    ],
)
def test_un_filtro_invalido_responde_422(cliente: TestClient, filtros: dict) -> None:
    respuesta = cliente.get(_HISTORIAL, params=filtros)

    assert respuesta.status_code == 422, respuesta.text


@pytest.mark.parametrize(
    "cuerpo",
    [{"tarea_id": 999_999}, {"tarea_id": "1"}, {}],
)
def test_un_fijar_rechazado_no_anade_ni_cierra_periodos(cliente: TestClient, cuerpo: dict) -> None:
    tarea = _crear_tarea(cliente)
    _fijar(cliente, tarea["id"])
    antes = _historial(cliente)

    assert cliente.put(_FOCO, json=cuerpo).status_code in (404, 422)

    assert _historial(cliente) == antes


def test_un_fijar_de_una_subtarea_ajena_no_anade_periodos(cliente: TestClient) -> None:
    tarea = _crear_tarea(cliente)
    otra = _crear_tarea(cliente, "Otra")
    ajena = _anadir_subtarea(cliente, otra["id"], "Ajena")

    assert (
        cliente.put(_FOCO, json={"tarea_id": tarea["id"], "subtarea_id": ajena["id"]}).status_code
        == 404
    )

    assert _historial(cliente) == []


def test_solo_puede_haber_un_periodo_en_curso(cliente: TestClient) -> None:
    tarea = _crear_tarea(cliente)
    _fijar(cliente, tarea["id"])

    with pytest.raises(Exception, match="uq_historial_foco_en_curso"):
        _ejecutar(
            "INSERT INTO historial_foco (tarea_id, tarea_nombre, desde) "
            "VALUES (:t, 'x', '2026-11-24 10:00:00')",
            t=tarea["id"],
        )


def test_el_foco_actual_no_cambia_de_forma(cliente: TestClient) -> None:
    tarea = _crear_tarea(cliente)

    foco = _fijar(cliente, tarea["id"])

    assert set(foco) == {"tarea_id", "tarea_nombre", "subtarea_id", "subtarea_nombre", "desde"}
    assert cliente.get(_FOCO).json() == foco


def test_borrar_tareas_y_subtareas_responde_como_antes(cliente: TestClient) -> None:
    """Regresión: el cierre del periodo no cambia las respuestas de los borrados."""
    tarea = _crear_tarea(cliente)
    subtarea = _anadir_subtarea(cliente, tarea["id"], "Paso")
    otra = _anadir_subtarea(cliente, tarea["id"], "Otro paso")
    _fijar(cliente, tarea["id"], subtarea["id"])
    esperada = next(t for t in cliente.get(_TAREAS).json() if t["id"] == tarea["id"])
    esperada["subtareas"] = [s for s in esperada["subtareas"] if s["id"] != subtarea["id"]]

    borrada = cliente.delete(f"{_TAREAS}/{tarea['id']}/subtareas/{subtarea['id']}")
    assert borrada.status_code == 200
    assert borrada.json() == esperada
    sin_subtarea = cliente.delete(f"{_TAREAS}/{tarea['id']}/subtareas/{subtarea['id']}")
    assert sin_subtarea.status_code == 404
    assert sin_subtarea.json() == {
        "detalle": f"No existe la subtarea con id {subtarea['id']} en la tarea con id {tarea['id']}"
    }

    _fijar(cliente, tarea["id"], otra["id"])
    borrado = cliente.delete(f"{_TAREAS}/{tarea['id']}")
    assert borrado.status_code == 204
    assert borrado.content == b""
    sin_tarea = cliente.delete(f"{_TAREAS}/{tarea['id']}")
    assert sin_tarea.status_code == 404
    assert sin_tarea.json() == {"detalle": f"No existe la tarea con id {tarea['id']}"}
    assert [p["hasta"] is not None for p in _historial(cliente)] == [True, True]
