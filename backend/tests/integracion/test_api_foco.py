"""API del foco de trabajo: la única tarea (o subtarea) con la que se está trabajando
en cada momento. Fijar otra sustituye a la anterior; borrar la tarea o la subtarea
en foco lo quita, y completar la tarea no."""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from gestor_tareas.infraestructura.persistencia.sesion import FabricaSesiones
from gestor_tareas.main import crear_aplicacion
from tests.integracion.tablas import vaciar_tablas

_FOCO = "/api/v1/foco"
_TAREAS = "/api/v1/tareas"
_TAREA = {
    "nombre": "Migración portal",
    "descripcion": "Pasar el portal a la nube",
    "fecha_creacion": "2026-11-10T09:00:00",
}


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


def _instante(texto: str) -> datetime:
    assert texto.endswith("Z")
    return datetime.fromisoformat(texto)


def _filas_de_foco() -> int:
    sesion = FabricaSesiones()
    try:
        return sesion.scalar(text("SELECT COUNT(*) FROM foco_trabajo"))
    finally:
        sesion.close()


def _fijar_desde(instante: str) -> None:
    sesion = FabricaSesiones()
    try:
        sesion.execute(text("UPDATE foco_trabajo SET desde = :desde"), {"desde": instante})
        sesion.commit()
    finally:
        sesion.close()


def test_sin_foco_devuelve_null(cliente: TestClient) -> None:
    respuesta = cliente.get(_FOCO)

    assert respuesta.status_code == 200
    assert respuesta.json() is None


def test_fijar_una_tarea_la_pone_en_foco_desde_ahora(cliente: TestClient) -> None:
    tarea = _crear_tarea(cliente)
    antes = datetime.now(UTC).replace(microsecond=0)

    respuesta = cliente.put(_FOCO, json={"tarea_id": tarea["id"]})

    assert respuesta.status_code == 200
    foco = respuesta.json()
    assert set(foco) == {"tarea_id", "tarea_nombre", "subtarea_id", "subtarea_nombre", "desde"}
    assert foco["tarea_id"] == tarea["id"]
    assert foco["tarea_nombre"] == "Migración portal"
    assert foco["subtarea_id"] is None
    assert foco["subtarea_nombre"] is None
    assert antes <= _instante(foco["desde"]) <= datetime.now(UTC)
    assert cliente.get(_FOCO).json() == foco


def test_fijar_con_subtarea_null_explicita_pone_en_foco_la_tarea(cliente: TestClient) -> None:
    tarea = _crear_tarea(cliente)

    respuesta = cliente.put(_FOCO, json={"tarea_id": tarea["id"], "subtarea_id": None})

    assert respuesta.status_code == 200
    assert respuesta.json()["subtarea_id"] is None


def test_fijar_una_subtarea_la_pone_en_foco_con_su_tarea(cliente: TestClient) -> None:
    tarea = _crear_tarea(cliente)
    subtarea = _anadir_subtarea(cliente, tarea["id"], "Copiar la base de datos")

    respuesta = cliente.put(_FOCO, json={"tarea_id": tarea["id"], "subtarea_id": subtarea["id"]})

    assert respuesta.status_code == 200
    foco = respuesta.json()
    assert foco["tarea_id"] == tarea["id"]
    assert foco["tarea_nombre"] == "Migración portal"
    assert foco["subtarea_id"] == subtarea["id"]
    assert foco["subtarea_nombre"] == "Copiar la base de datos"
    assert cliente.get(_FOCO).json() == foco


def test_fijar_otra_sustituye_a_la_anterior_y_reinicia_desde(cliente: TestClient) -> None:
    primera = _crear_tarea(cliente, "Primera")
    segunda = _crear_tarea(cliente, "Segunda")
    assert cliente.put(_FOCO, json={"tarea_id": primera["id"]}).status_code == 200
    _fijar_desde("2026-01-01 08:00:00")

    respuesta = cliente.put(_FOCO, json={"tarea_id": segunda["id"]})

    assert respuesta.status_code == 200
    foco = respuesta.json()
    assert foco["tarea_id"] == segunda["id"]
    assert foco["tarea_nombre"] == "Segunda"
    assert _instante(foco["desde"]) > datetime(2026, 1, 2, tzinfo=UTC)
    assert cliente.get(_FOCO).json() == foco
    assert _filas_de_foco() == 1


def test_volver_a_fijar_la_misma_reinicia_desde(cliente: TestClient) -> None:
    tarea = _crear_tarea(cliente)
    assert cliente.put(_FOCO, json={"tarea_id": tarea["id"]}).status_code == 200
    _fijar_desde("2026-01-01 08:00:00")

    respuesta = cliente.put(_FOCO, json={"tarea_id": tarea["id"]})

    assert respuesta.status_code == 200
    assert _instante(respuesta.json()["desde"]) > datetime(2026, 1, 2, tzinfo=UTC)
    assert _filas_de_foco() == 1


def test_fijar_una_tarea_que_no_existe_responde_404_y_no_cambia_el_foco(
    cliente: TestClient,
) -> None:
    tarea = _crear_tarea(cliente)
    previo = cliente.put(_FOCO, json={"tarea_id": tarea["id"]}).json()

    respuesta = cliente.put(_FOCO, json={"tarea_id": tarea["id"] + 1000})

    assert respuesta.status_code == 404
    assert respuesta.json() == {"detalle": f"No existe la tarea con id {tarea['id'] + 1000}"}
    assert cliente.get(_FOCO).json() == previo


def test_fijar_una_subtarea_que_no_existe_responde_404(cliente: TestClient) -> None:
    tarea = _crear_tarea(cliente)

    respuesta = cliente.put(_FOCO, json={"tarea_id": tarea["id"], "subtarea_id": 999999})

    assert respuesta.status_code == 404
    assert respuesta.json() == {
        "detalle": f"No existe la subtarea con id 999999 en la tarea con id {tarea['id']}"
    }
    assert cliente.get(_FOCO).json() is None


def test_fijar_una_subtarea_de_otra_tarea_responde_404(cliente: TestClient) -> None:
    tarea = _crear_tarea(cliente, "Una")
    otra = _crear_tarea(cliente, "Otra")
    ajena = _anadir_subtarea(cliente, otra["id"], "Ajena")

    respuesta = cliente.put(_FOCO, json={"tarea_id": tarea["id"], "subtarea_id": ajena["id"]})

    assert respuesta.status_code == 404
    assert respuesta.json() == {
        "detalle": f"No existe la subtarea con id {ajena['id']} en la tarea con id {tarea['id']}"
    }
    assert cliente.get(_FOCO).json() is None


@pytest.mark.parametrize(
    "cuerpo",
    [
        {},
        {"subtarea_id": 1},
        {"tarea_id": None},
        {"tarea_id": "uno"},
        {"tarea_id": 1.5},
        {"tarea_id": True},
        {"tarea_id": 1, "subtarea_id": "dos"},
    ],
)
def test_un_cuerpo_invalido_responde_422(cliente: TestClient, cuerpo: dict) -> None:
    respuesta = cliente.put(_FOCO, json=cuerpo)

    assert respuesta.status_code == 422
    assert "detail" in respuesta.json()
    assert cliente.get(_FOCO).json() is None


def test_quitar_el_foco_responde_204_y_deja_null(cliente: TestClient) -> None:
    tarea = _crear_tarea(cliente)
    cliente.put(_FOCO, json={"tarea_id": tarea["id"]})

    respuesta = cliente.delete(_FOCO)

    assert respuesta.status_code == 204
    assert respuesta.content == b""
    assert cliente.get(_FOCO).json() is None
    assert _filas_de_foco() == 0


def test_quitar_el_foco_sin_foco_tambien_responde_204(cliente: TestClient) -> None:
    primera = cliente.delete(_FOCO)
    segunda = cliente.delete(_FOCO)

    assert primera.status_code == 204
    assert segunda.status_code == 204
    assert segunda.content == b""
    assert cliente.get(_FOCO).json() is None


def test_borrar_la_tarea_en_foco_quita_el_foco(cliente: TestClient) -> None:
    tarea = _crear_tarea(cliente)
    cliente.put(_FOCO, json={"tarea_id": tarea["id"]})

    assert cliente.delete(f"{_TAREAS}/{tarea['id']}").status_code == 204

    respuesta = cliente.get(_FOCO)
    assert respuesta.status_code == 200
    assert respuesta.json() is None


def test_borrar_la_tarea_de_la_subtarea_en_foco_quita_el_foco(cliente: TestClient) -> None:
    tarea = _crear_tarea(cliente)
    subtarea = _anadir_subtarea(cliente, tarea["id"], "Paso")
    cliente.put(_FOCO, json={"tarea_id": tarea["id"], "subtarea_id": subtarea["id"]})

    assert cliente.delete(f"{_TAREAS}/{tarea['id']}").status_code == 204

    assert cliente.get(_FOCO).json() is None


def test_borrar_la_subtarea_en_foco_quita_el_foco(cliente: TestClient) -> None:
    tarea = _crear_tarea(cliente)
    subtarea = _anadir_subtarea(cliente, tarea["id"], "Paso")
    cliente.put(_FOCO, json={"tarea_id": tarea["id"], "subtarea_id": subtarea["id"]})

    borrado = cliente.delete(f"{_TAREAS}/{tarea['id']}/subtareas/{subtarea['id']}")
    assert borrado.status_code in (200, 204), borrado.text

    respuesta = cliente.get(_FOCO)
    assert respuesta.status_code == 200
    assert respuesta.json() is None


def test_borrar_otra_subtarea_no_quita_el_foco(cliente: TestClient) -> None:
    tarea = _crear_tarea(cliente)
    subtarea = _anadir_subtarea(cliente, tarea["id"], "Paso")
    otra = _anadir_subtarea(cliente, tarea["id"], "Otro paso")
    foco = cliente.put(_FOCO, json={"tarea_id": tarea["id"], "subtarea_id": subtarea["id"]}).json()

    cliente.delete(f"{_TAREAS}/{tarea['id']}/subtareas/{otra['id']}")

    assert cliente.get(_FOCO).json() == foco


def test_completar_la_tarea_en_foco_no_quita_el_foco(cliente: TestClient) -> None:
    tarea = _crear_tarea(cliente)
    foco = cliente.put(_FOCO, json={"tarea_id": tarea["id"]}).json()

    completada = cliente.patch(f"{_TAREAS}/{tarea['id']}/completada", json={"completada": True})
    assert completada.status_code == 200

    respuesta = cliente.get(_FOCO)
    assert respuesta.status_code == 200
    assert respuesta.json() == foco


def test_el_foco_muestra_el_nombre_actual_de_la_tarea(cliente: TestClient) -> None:
    tarea = _crear_tarea(cliente)
    cliente.put(_FOCO, json={"tarea_id": tarea["id"]})

    editada = cliente.put(
        f"{_TAREAS}/{tarea['id']}", json={**_TAREA, "nombre": "Migración portal v2"}
    )
    assert editada.status_code == 200, editada.text

    assert cliente.get(_FOCO).json()["tarea_nombre"] == "Migración portal v2"
