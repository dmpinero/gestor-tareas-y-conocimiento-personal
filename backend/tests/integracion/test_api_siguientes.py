"""API de la cola de siguientes tareas: lista ordenada de tareas elegidas para
trabajar después del foco. Las completadas no se ven (y vuelven a su sitio al
reabrirlas); borrar una tarea o ponerla en foco la saca de la cola."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from gestor_tareas.infraestructura.persistencia.sesion import FabricaSesiones
from gestor_tareas.main import crear_aplicacion
from tests.integracion.tablas import vaciar_tablas

_TAREAS = "/api/v1/tareas"
_SIGUIENTES = "/api/v1/siguientes"


@pytest.fixture
def cliente() -> TestClient:
    sesion = FabricaSesiones()
    try:
        vaciar_tablas(sesion)
    finally:
        sesion.close()
    return TestClient(crear_aplicacion())


def _crear_tarea(cliente: TestClient, nombre: str, subtarea: str | None = None) -> int:
    cuerpo = {"nombre": nombre, "descripcion": "d", "fecha_creacion": "2026-11-26T09:00:00"}
    respuesta = cliente.post(_TAREAS, json=cuerpo)
    assert respuesta.status_code == 201, respuesta.text
    id_tarea = respuesta.json()["id"]
    if subtarea is not None:
        respuesta = cliente.post(f"{_TAREAS}/{id_tarea}/subtareas", json={"nombre": subtarea})
        assert respuesta.status_code in (200, 201), respuesta.text
    return id_tarea


def _subtarea(cliente: TestClient, id_tarea: int) -> int:
    tarea = next(t for t in cliente.get(_TAREAS).json() if t["id"] == id_tarea)
    return tarea["subtareas"][0]["id"]


def _anadir(cliente: TestClient, *ids: int):
    respuesta = None
    for id_tarea in ids:
        respuesta = cliente.post(_SIGUIENTES, json={"tarea_id": id_tarea})
        assert respuesta.status_code == 200, respuesta.text
    return respuesta


def _cola(cliente: TestClient) -> list[int]:
    respuesta = cliente.get(_SIGUIENTES)
    assert respuesta.status_code == 200, respuesta.text
    return [t["tarea_id"] for t in respuesta.json()]


def _completar(cliente: TestClient, id_tarea: int, completada: bool = True) -> None:
    respuesta = cliente.patch(f"{_TAREAS}/{id_tarea}/completada", json={"completada": completada})
    assert respuesta.status_code == 200, respuesta.text


def _filas_guardadas() -> list[int]:
    sesion = FabricaSesiones()
    try:
        return [
            f[0]
            for f in sesion.execute(
                text("SELECT tarea_id FROM cola_siguientes ORDER BY posicion, tarea_id")
            ).all()
        ]
    finally:
        sesion.close()


def test_la_cola_empieza_vacia(cliente: TestClient) -> None:
    _crear_tarea(cliente, "A")

    respuesta = cliente.get(_SIGUIENTES)

    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_anadir_va_al_final_y_devuelve_la_cola_completa_con_los_nombres(
    cliente: TestClient,
) -> None:
    a, b = _crear_tarea(cliente, "A"), _crear_tarea(cliente, "B")

    _anadir(cliente, b)
    respuesta = _anadir(cliente, a)

    esperada = [{"tarea_id": b, "tarea_nombre": "B"}, {"tarea_id": a, "tarea_nombre": "A"}]
    assert respuesta.json() == esperada
    assert cliente.get(_SIGUIENTES).json() == esperada
    assert _filas_guardadas() == [b, a]


def test_los_nombres_son_los_actuales(cliente: TestClient) -> None:
    a = _crear_tarea(cliente, "A")
    _anadir(cliente, a)

    respuesta = cliente.put(
        f"{_TAREAS}/{a}",
        json={
            "nombre": "A renombrada",
            "descripcion": "d",
            "fecha_creacion": "2026-11-26T09:00:00",
        },
    )
    assert respuesta.status_code == 200, respuesta.text

    assert cliente.get(_SIGUIENTES).json() == [{"tarea_id": a, "tarea_nombre": "A renombrada"}]


def test_anadir_una_que_ya_estaba_no_cambia_nada(cliente: TestClient) -> None:
    a, b = _crear_tarea(cliente, "A"), _crear_tarea(cliente, "B")
    _anadir(cliente, a, b)

    respuesta = _anadir(cliente, a)

    assert [t["tarea_id"] for t in respuesta.json()] == [a, b]
    assert _filas_guardadas() == [a, b]


def test_anadir_una_tarea_que_no_existe_da_404_sin_cambiar_la_cola(cliente: TestClient) -> None:
    a = _crear_tarea(cliente, "A")
    _anadir(cliente, a)

    respuesta = cliente.post(_SIGUIENTES, json={"tarea_id": a + 1000})

    assert respuesta.status_code == 404
    assert respuesta.json() == {"detalle": f"No existe la tarea con id {a + 1000}"}
    assert _filas_guardadas() == [a]


def test_anadir_una_tarea_completada_da_422_sin_cambiar_la_cola(cliente: TestClient) -> None:
    a = _crear_tarea(cliente, "A")
    _completar(cliente, a)

    respuesta = cliente.post(_SIGUIENTES, json={"tarea_id": a})

    assert respuesta.status_code == 422
    error = respuesta.json()["detail"][0]
    assert error["loc"] == ["body", "tarea_id"]
    assert "completada" in error["msg"]
    assert _filas_guardadas() == []


@pytest.mark.parametrize("cuerpo", [{}, {"tarea_id": "1"}, {"tarea_id": True}, {"tarea_id": 1.5}])
def test_anadir_sin_un_id_entero_da_422(cliente: TestClient, cuerpo: dict) -> None:
    assert cliente.post(_SIGUIENTES, json=cuerpo).status_code == 422


def test_las_completadas_no_se_ven_y_al_reabrirlas_vuelven_a_su_sitio(cliente: TestClient) -> None:
    a, b, c = (_crear_tarea(cliente, n) for n in "ABC")
    _anadir(cliente, a, b, c)

    _completar(cliente, b)
    assert _cola(cliente) == [a, c]
    assert _filas_guardadas() == [a, b, c]

    _completar(cliente, b, completada=False)
    assert _cola(cliente) == [a, b, c]


def test_reordenar_devuelve_la_cola_en_el_nuevo_orden(cliente: TestClient) -> None:
    a, b, c = (_crear_tarea(cliente, n) for n in "ABC")
    _anadir(cliente, a, b, c)

    respuesta = cliente.put(_SIGUIENTES, json={"ids": [c, a, b]})

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json() == [
        {"tarea_id": c, "tarea_nombre": "C"},
        {"tarea_id": a, "tarea_nombre": "A"},
        {"tarea_id": b, "tarea_nombre": "B"},
    ]
    assert _cola(cliente) == [c, a, b]


def test_reordenar_deja_las_completadas_detras(cliente: TestClient) -> None:
    a, b, c = (_crear_tarea(cliente, n) for n in "ABC")
    _anadir(cliente, a, b, c)
    _completar(cliente, a)

    respuesta = cliente.put(_SIGUIENTES, json={"ids": [c, b]})

    assert respuesta.status_code == 200, respuesta.text
    assert [t["tarea_id"] for t in respuesta.json()] == [c, b]
    _completar(cliente, a, completada=False)
    assert _cola(cliente) == [c, b, a]


@pytest.mark.parametrize(
    "ids",
    [
        pytest.param(lambda a, b, c: [a, b], id="falta una"),
        pytest.param(lambda a, b, c: [a, b, c, c + 1000], id="sobra una"),
        pytest.param(lambda a, b, c: [a, b, c, c], id="repite una"),
        pytest.param(lambda a, b, c: [], id="ninguna"),
    ],
)
def test_reordenar_con_ids_que_no_son_la_cola_da_422_sin_cambiarla(
    cliente: TestClient, ids
) -> None:
    a, b, c = (_crear_tarea(cliente, n) for n in "ABC")
    _anadir(cliente, a, b, c)

    respuesta = cliente.put(_SIGUIENTES, json={"ids": ids(a, b, c)})

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"][0]["loc"][:2] == ["body", "ids"]
    assert _filas_guardadas() == [a, b, c]


def test_reordenar_incluyendo_una_completada_da_422(cliente: TestClient) -> None:
    a, b = _crear_tarea(cliente, "A"), _crear_tarea(cliente, "B")
    _anadir(cliente, a, b)
    _completar(cliente, b)

    respuesta = cliente.put(_SIGUIENTES, json={"ids": [b, a]})

    assert respuesta.status_code == 422
    assert _filas_guardadas() == [a, b]


def test_reordenar_una_cola_vacia_sin_ids(cliente: TestClient) -> None:
    respuesta = cliente.put(_SIGUIENTES, json={"ids": []})

    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_quitar_saca_la_tarea_y_devuelve_la_cola(cliente: TestClient) -> None:
    a, b = _crear_tarea(cliente, "A"), _crear_tarea(cliente, "B")
    _anadir(cliente, a, b)

    respuesta = cliente.delete(f"{_SIGUIENTES}/{a}")

    assert respuesta.status_code == 200
    assert respuesta.json() == [{"tarea_id": b, "tarea_nombre": "B"}]
    assert _filas_guardadas() == [b]


def test_quitar_una_que_no_estaba_responde_200_sin_cambios(cliente: TestClient) -> None:
    a, b = _crear_tarea(cliente, "A"), _crear_tarea(cliente, "B")
    _anadir(cliente, a)

    for id_tarea in (b, b + 1000):
        respuesta = cliente.delete(f"{_SIGUIENTES}/{id_tarea}")
        assert respuesta.status_code == 200
        assert respuesta.json() == [{"tarea_id": a, "tarea_nombre": "A"}]
    assert _filas_guardadas() == [a]


def test_borrar_una_tarea_la_saca_de_la_cola(cliente: TestClient) -> None:
    a, b = _crear_tarea(cliente, "A"), _crear_tarea(cliente, "B")
    _anadir(cliente, a, b)

    assert cliente.delete(f"{_TAREAS}/{a}").status_code == 204

    assert _cola(cliente) == [b]
    assert _filas_guardadas() == [b]


def test_poner_en_foco_una_tarea_la_saca_de_la_cola_y_la_respuesta_no_cambia(
    cliente: TestClient,
) -> None:
    a, b = _crear_tarea(cliente, "A"), _crear_tarea(cliente, "B")
    _anadir(cliente, a, b)

    respuesta = cliente.put("/api/v1/foco", json={"tarea_id": a})

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert set(cuerpo) == {"tarea_id", "tarea_nombre", "subtarea_id", "subtarea_nombre", "desde"}
    assert (cuerpo["tarea_id"], cuerpo["tarea_nombre"], cuerpo["subtarea_id"]) == (a, "A", None)
    assert _cola(cliente) == [b]
    assert _filas_guardadas() == [b]


def test_poner_en_foco_una_subtarea_saca_su_tarea_de_la_cola(cliente: TestClient) -> None:
    a = _crear_tarea(cliente, "A", subtarea="Sub")
    b = _crear_tarea(cliente, "B")
    _anadir(cliente, a, b)
    id_subtarea = _subtarea(cliente, a)

    respuesta = cliente.put("/api/v1/foco", json={"tarea_id": a, "subtarea_id": id_subtarea})

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["subtarea_id"] == id_subtarea
    assert _cola(cliente) == [b]


def test_poner_en_foco_una_tarea_que_no_esta_en_la_cola_no_la_cambia(cliente: TestClient) -> None:
    a, b = _crear_tarea(cliente, "A"), _crear_tarea(cliente, "B")
    _anadir(cliente, b)

    assert cliente.put("/api/v1/foco", json={"tarea_id": a}).status_code == 200

    assert _cola(cliente) == [b]


def test_un_foco_que_falla_no_saca_nada_de_la_cola(cliente: TestClient) -> None:
    a = _crear_tarea(cliente, "A")
    _anadir(cliente, a)

    respuesta = cliente.put("/api/v1/foco", json={"tarea_id": a, "subtarea_id": 999999})

    assert respuesta.status_code == 404
    assert _filas_guardadas() == [a]
