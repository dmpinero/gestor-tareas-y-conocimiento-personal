"""API de las tareas vinculadas: desde una tarea se vinculan una o varias tareas
existentes y la relación se ve desde las dos (simple, sin tipos). Se quita en ambos
sentidos y desaparece al borrar cualquiera de las dos tareas."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from gestor_tareas.infraestructura.persistencia.sesion import FabricaSesiones
from gestor_tareas.main import crear_aplicacion
from tests.integracion.tablas import vaciar_tablas

_TAREAS = "/api/v1/tareas"


@pytest.fixture
def cliente() -> TestClient:
    sesion = FabricaSesiones()
    try:
        vaciar_tablas(sesion)
    finally:
        sesion.close()
    return TestClient(crear_aplicacion())


def _crear_tarea(cliente: TestClient, nombre: str) -> int:
    respuesta = cliente.post(
        _TAREAS,
        json={"nombre": nombre, "descripcion": "d", "fecha_creacion": "2026-11-26T09:00:00"},
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["id"]


def _vinculadas_en_el_listado(cliente: TestClient) -> dict[int, list[int]]:
    respuesta = cliente.get(_TAREAS)
    assert respuesta.status_code == 200
    return {t["id"]: t["vinculadas"] for t in respuesta.json()}


def _filas_guardadas() -> list[tuple[int, int]]:
    sesion = FabricaSesiones()
    try:
        return [
            tuple(f)
            for f in sesion.execute(
                text(
                    "SELECT tarea_id, vinculada_id FROM tareas_vinculadas "
                    "ORDER BY tarea_id, vinculada_id"
                )
            ).all()
        ]
    finally:
        sesion.close()


def _vincular(cliente: TestClient, id_tarea: int, ids: list[int]):
    return cliente.post(f"{_TAREAS}/{id_tarea}/vinculadas", json={"ids": ids})


def test_una_tarea_nueva_no_tiene_vinculadas(cliente: TestClient) -> None:
    id_tarea = _crear_tarea(cliente, "A")

    assert _vinculadas_en_el_listado(cliente) == {id_tarea: []}


def test_vincular_varias_a_la_vez_se_ve_desde_todas_y_en_orden(cliente: TestClient) -> None:
    a, b, c = (_crear_tarea(cliente, n) for n in "ABC")

    respuesta = _vincular(cliente, a, [c, b])

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["id"] == a
    assert respuesta.json()["vinculadas"] == [b, c]
    assert _vinculadas_en_el_listado(cliente) == {a: [b, c], b: [a], c: [a]}
    assert _filas_guardadas() == sorted([(a, b), (b, a), (a, c), (c, a)])


def test_las_vinculadas_del_listado_van_en_orden_ascendente(cliente: TestClient) -> None:
    a, b, c, d = (_crear_tarea(cliente, n) for n in "ABCD")
    assert _vincular(cliente, d, [a]).status_code == 200
    assert _vincular(cliente, b, [d]).status_code == 200
    assert _vincular(cliente, c, [d]).status_code == 200

    assert _vinculadas_en_el_listado(cliente)[d] == [a, b, c]


def test_vincular_ignora_las_ya_vinculadas(cliente: TestClient) -> None:
    a, b, c = (_crear_tarea(cliente, n) for n in "ABC")
    assert _vincular(cliente, a, [b]).status_code == 200

    # También si se vincula desde la otra tarea.
    respuesta = _vincular(cliente, b, [a, c])

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["vinculadas"] == [a, c]
    assert _vinculadas_en_el_listado(cliente) == {a: [b], b: [a, c], c: [b]}
    assert _filas_guardadas() == sorted([(a, b), (b, a), (b, c), (c, b)])


def test_vincular_una_tarea_que_no_existe_es_404(cliente: TestClient) -> None:
    a = _crear_tarea(cliente, "A")

    respuesta = _vincular(cliente, a + 1000, [a])

    assert respuesta.status_code == 404
    assert respuesta.json() == {"detalle": f"No existe la tarea con id {a + 1000}"}
    assert _filas_guardadas() == []


def test_vincular_con_un_id_que_no_existe_es_404_y_no_vincula_ninguna(
    cliente: TestClient,
) -> None:
    a, b = (_crear_tarea(cliente, n) for n in "AB")

    respuesta = _vincular(cliente, a, [b, b + 1000])

    assert respuesta.status_code == 404
    assert respuesta.json() == {"detalle": f"No existe la tarea con id {b + 1000}"}
    assert _filas_guardadas() == []
    assert _vinculadas_en_el_listado(cliente) == {a: [], b: []}


def test_vincular_una_tarea_consigo_misma_es_422(cliente: TestClient) -> None:
    a, b = (_crear_tarea(cliente, n) for n in "AB")

    respuesta = _vincular(cliente, a, [b, a])

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"][0]["loc"] == ["body", "ids"]
    assert _filas_guardadas() == []


@pytest.mark.parametrize("cuerpo", [{"ids": []}, {}, {"ids": ["x"]}, {"ids": [True]}])
def test_vincular_con_un_cuerpo_invalido_es_422(cliente: TestClient, cuerpo: dict) -> None:
    a = _crear_tarea(cliente, "A")

    respuesta = cliente.post(f"{_TAREAS}/{a}/vinculadas", json=cuerpo)

    assert respuesta.status_code == 422
    assert _filas_guardadas() == []


def test_desvincular_quita_la_relacion_en_ambos_sentidos(cliente: TestClient) -> None:
    a, b, c = (_crear_tarea(cliente, n) for n in "ABC")
    assert _vincular(cliente, a, [b, c]).status_code == 200

    respuesta = cliente.delete(f"{_TAREAS}/{b}/vinculadas/{a}")

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["id"] == b
    assert respuesta.json()["vinculadas"] == []
    assert _vinculadas_en_el_listado(cliente) == {a: [c], b: [], c: [a]}
    assert _filas_guardadas() == sorted([(a, c), (c, a)])


def test_desvincular_tareas_no_vinculadas_es_200_sin_cambios(cliente: TestClient) -> None:
    a, b, c = (_crear_tarea(cliente, n) for n in "ABC")
    assert _vincular(cliente, a, [c]).status_code == 200

    respuesta = cliente.delete(f"{_TAREAS}/{a}/vinculadas/{b}")

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["vinculadas"] == [c]
    assert _filas_guardadas() == sorted([(a, c), (c, a)])


def test_desvincular_con_una_tarea_que_no_existe_es_404(cliente: TestClient) -> None:
    a = _crear_tarea(cliente, "A")
    inexistente = a + 1000

    for ruta in (
        f"{_TAREAS}/{inexistente}/vinculadas/{a}",
        f"{_TAREAS}/{a}/vinculadas/{inexistente}",
    ):
        respuesta = cliente.delete(ruta)
        assert respuesta.status_code == 404
        assert respuesta.json() == {"detalle": f"No existe la tarea con id {inexistente}"}


def test_borrar_una_tarea_la_quita_de_las_vinculadas_de_las_demas(cliente: TestClient) -> None:
    a, b, c = (_crear_tarea(cliente, n) for n in "ABC")
    assert _vincular(cliente, a, [b, c]).status_code == 200

    assert cliente.delete(f"{_TAREAS}/{b}").status_code == 204

    assert _vinculadas_en_el_listado(cliente) == {a: [c], c: [a]}
    assert _filas_guardadas() == sorted([(a, c), (c, a)])


def test_editar_una_tarea_conserva_sus_vinculadas(cliente: TestClient) -> None:
    a, b = (_crear_tarea(cliente, n) for n in "AB")
    assert _vincular(cliente, a, [b]).status_code == 200

    respuesta = cliente.put(
        f"{_TAREAS}/{a}",
        json={"nombre": "A2", "descripcion": "d", "fecha_creacion": "2026-11-26T09:00:00"},
    )

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["vinculadas"] == [b]
    assert _vinculadas_en_el_listado(cliente) == {a: [b], b: [a]}
