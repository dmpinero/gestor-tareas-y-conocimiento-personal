"""API del catálogo de subestados (como el de etiquetas, con alta, cambio de nombre
y borrado) y del subestado de las tareas (como mucho uno, opcional)."""

import pytest
from fastapi.testclient import TestClient

from gestor_tareas.infraestructura.persistencia.sesion import FabricaSesiones
from gestor_tareas.main import crear_aplicacion
from tests.integracion.tablas import vaciar_tablas

_SUBESTADOS = "/api/v1/subestados"
_TAREAS = "/api/v1/tareas"
_TAREA = {
    "nombre": "Mudanza",
    "descripcion": "Cajas",
    "fecha_creacion": "2026-11-10T09:00:00",
    "etiquetas": ["Casa"],
}


@pytest.fixture
def cliente() -> TestClient:
    sesion = FabricaSesiones()
    try:
        vaciar_tablas(sesion)
    finally:
        sesion.close()
    return TestClient(crear_aplicacion())


def _nombres(cliente: TestClient) -> list[str]:
    respuesta = cliente.get(_SUBESTADOS)
    assert respuesta.status_code == 200
    return [s["nombre"] for s in respuesta.json()]


def _crear_subestado(cliente: TestClient, nombre: str) -> dict:
    respuesta = cliente.post(_SUBESTADOS, json={"nombre": nombre})
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _crear_tarea(cliente: TestClient, **datos: object) -> dict:
    respuesta = cliente.post(_TAREAS, json={**_TAREA, **datos})
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _tarea(cliente: TestClient, id_tarea: int) -> dict:
    return next(t for t in cliente.get(_TAREAS).json() if t["id"] == id_tarea)


# --- Catálogo ---


def test_el_catalogo_empieza_vacio(cliente: TestClient) -> None:
    assert cliente.get(_SUBESTADOS).json() == []


def test_alta_de_un_subestado_recorta_el_nombre_y_lista_por_nombre(cliente: TestClient) -> None:
    creado = _crear_subestado(cliente, "  Esperando cliente ")
    _crear_subestado(cliente, "bloqueado")

    assert set(creado) == {"id", "nombre"}
    assert creado["nombre"] == "Esperando cliente"
    assert _nombres(cliente) == ["bloqueado", "Esperando cliente"]


@pytest.mark.parametrize("nombre", ["BLOQUEADO", "bloqueado", " Bloqueado "])
def test_alta_de_un_nombre_repetido_sin_distinguir_mayusculas_responde_409(
    cliente: TestClient, nombre: str
) -> None:
    _crear_subestado(cliente, "Bloqueado")

    respuesta = cliente.post(_SUBESTADOS, json={"nombre": nombre})

    assert respuesta.status_code == 409
    assert respuesta.json() == {"detalle": f"Ya existe un subestado llamado «{nombre.strip()}»"}
    assert _nombres(cliente) == ["Bloqueado"]


def test_los_nombres_que_solo_difieren_en_tildes_son_distintos(cliente: TestClient) -> None:
    _crear_subestado(cliente, "Revision")
    _crear_subestado(cliente, "Revisión")

    assert _nombres(cliente) == ["Revision", "Revisión"]


@pytest.mark.parametrize(
    "cuerpo", [{}, {"nombre": ""}, {"nombre": "   "}, {"nombre": "a" * 51}, {"nombre": 5}]
)
def test_alta_con_un_nombre_invalido_responde_422(cliente: TestClient, cuerpo: dict) -> None:
    assert cliente.post(_SUBESTADOS, json=cuerpo).status_code == 422
    assert _nombres(cliente) == []


def test_admite_un_nombre_de_50_caracteres(cliente: TestClient) -> None:
    assert _crear_subestado(cliente, "a" * 50)["nombre"] == "a" * 50


def test_cambiar_el_nombre_lo_cambia_tambien_en_sus_tareas(cliente: TestClient) -> None:
    subestado = _crear_subestado(cliente, "Bloqueado")
    tarea = _crear_tarea(cliente, subestado="Bloqueado")

    respuesta = cliente.put(f"{_SUBESTADOS}/{subestado['id']}", json={"nombre": " En pausa "})

    assert respuesta.status_code == 200
    assert respuesta.json() == {"id": subestado["id"], "nombre": "En pausa"}
    assert _tarea(cliente, tarea["id"])["subestado"] == "En pausa"


def test_cambiar_el_nombre_a_su_misma_grafia_en_mayusculas_se_admite(cliente: TestClient) -> None:
    subestado = _crear_subestado(cliente, "bloqueado")

    respuesta = cliente.put(f"{_SUBESTADOS}/{subestado['id']}", json={"nombre": "Bloqueado"})

    assert respuesta.status_code == 200
    assert _nombres(cliente) == ["Bloqueado"]


def test_cambiar_el_nombre_al_de_otro_subestado_responde_409(cliente: TestClient) -> None:
    _crear_subestado(cliente, "Bloqueado")
    otro = _crear_subestado(cliente, "En pausa")

    respuesta = cliente.put(f"{_SUBESTADOS}/{otro['id']}", json={"nombre": "BLOQUEADO"})

    assert respuesta.status_code == 409
    assert respuesta.json() == {"detalle": "Ya existe un subestado llamado «BLOQUEADO»"}
    assert _nombres(cliente) == ["Bloqueado", "En pausa"]


def test_cambiar_el_nombre_de_un_subestado_que_no_existe_responde_404(
    cliente: TestClient,
) -> None:
    respuesta = cliente.put(f"{_SUBESTADOS}/999999", json={"nombre": "X"})

    assert respuesta.status_code == 404
    assert respuesta.json() == {"detalle": "No existe el subestado con id 999999"}


def test_eliminar_un_subestado_deja_sus_tareas_sin_subestado(cliente: TestClient) -> None:
    subestado = _crear_subestado(cliente, "Bloqueado")
    _crear_subestado(cliente, "En pausa")
    con_el = _crear_tarea(cliente, subestado="Bloqueado")
    con_otro = _crear_tarea(cliente, nombre="Otra", subestado="En pausa")

    respuesta = cliente.delete(f"{_SUBESTADOS}/{subestado['id']}")

    assert respuesta.status_code == 204
    assert respuesta.content == b""
    assert _nombres(cliente) == ["En pausa"]
    despues = _tarea(cliente, con_el["id"])
    assert despues["subestado"] is None
    # El resto de la tarea no cambia.
    assert {k: v for k, v in despues.items() if k != "subestado"} == {
        k: v for k, v in con_el.items() if k != "subestado"
    }
    assert _tarea(cliente, con_otro["id"])["subestado"] == "En pausa"


def test_eliminar_un_subestado_que_no_existe_responde_404(cliente: TestClient) -> None:
    respuesta = cliente.delete(f"{_SUBESTADOS}/999999")

    assert respuesta.status_code == 404
    assert respuesta.json() == {"detalle": "No existe el subestado con id 999999"}


# --- Subestado de las tareas ---


def test_una_tarea_sin_subestado_lo_devuelve_como_null(cliente: TestClient) -> None:
    tarea = _crear_tarea(cliente)

    assert tarea["subestado"] is None
    assert _tarea(cliente, tarea["id"])["subestado"] is None
    assert cliente.get(_SUBESTADOS).json() == []


def test_alta_con_un_subestado_nuevo_lo_da_de_alta_en_el_catalogo(cliente: TestClient) -> None:
    tarea = _crear_tarea(cliente, subestado="  Esperando cliente  ")

    assert tarea["subestado"] == "Esperando cliente"
    assert _nombres(cliente) == ["Esperando cliente"]


def test_alta_con_un_subestado_existente_lo_reutiliza_con_su_grafia(cliente: TestClient) -> None:
    _crear_subestado(cliente, "Bloqueado")

    tarea = _crear_tarea(cliente, subestado="BLOQUEADO")

    assert tarea["subestado"] == "Bloqueado"
    assert _nombres(cliente) == ["Bloqueado"]


@pytest.mark.parametrize("subestado", ["", "   ", "a" * 51, 5, ["Bloqueado"]])
def test_alta_con_un_subestado_invalido_responde_422(cliente: TestClient, subestado) -> None:
    respuesta = cliente.post(_TAREAS, json={**_TAREA, "subestado": subestado})

    assert respuesta.status_code == 422
    assert cliente.get(_TAREAS).json() == []


def test_alta_con_subestado_null_queda_sin_subestado(cliente: TestClient) -> None:
    assert _crear_tarea(cliente, subestado=None)["subestado"] is None


def test_editar_con_otro_subestado_lo_cambia(cliente: TestClient) -> None:
    tarea = _crear_tarea(cliente, subestado="Bloqueado")

    respuesta = cliente.put(f"{_TAREAS}/{tarea['id']}", json={**_TAREA, "subestado": "En pausa"})

    assert respuesta.status_code == 200
    assert respuesta.json()["subestado"] == "En pausa"
    assert _tarea(cliente, tarea["id"])["subestado"] == "En pausa"
    assert _nombres(cliente) == ["Bloqueado", "En pausa"]


def test_editar_con_subestado_null_lo_quita(cliente: TestClient) -> None:
    tarea = _crear_tarea(cliente, subestado="Bloqueado")

    respuesta = cliente.put(f"{_TAREAS}/{tarea['id']}", json={**_TAREA, "subestado": None})

    assert respuesta.status_code == 200
    assert respuesta.json()["subestado"] is None
    # Quitarlo de la tarea no lo borra del catálogo.
    assert _nombres(cliente) == ["Bloqueado"]


def test_editar_sin_el_campo_subestado_lo_conserva(cliente: TestClient) -> None:
    tarea = _crear_tarea(cliente, subestado="Bloqueado")

    respuesta = cliente.put(f"{_TAREAS}/{tarea['id']}", json={**_TAREA, "nombre": "Mudanza grande"})

    assert respuesta.status_code == 200
    assert respuesta.json()["nombre"] == "Mudanza grande"
    assert respuesta.json()["subestado"] == "Bloqueado"


def test_un_alta_sin_el_campo_se_comporta_como_antes(cliente: TestClient) -> None:
    tarea = _crear_tarea(cliente)

    assert {k: v for k, v in tarea.items() if k not in ("id", "subestado")} == {
        "nombre": "Mudanza",
        "prioridad": None,
        "descripcion": "Cajas",
        "fecha_creacion": "2026-11-10T09:00:00",
        "fecha_vencimiento": None,
        "etiquetas": ["Casa"],
        "asignados": [],
        "tipo": None,
        "oportunidad": None,
        "completada": False,
        "subtareas": [],
        "grupo_estados": None,
        "estado": None,
        "workflow": None,
        "congelada_en": None,
    }


def test_una_edicion_sin_el_campo_se_comporta_como_antes(cliente: TestClient) -> None:
    tarea = _crear_tarea(cliente)

    respuesta = cliente.put(
        f"{_TAREAS}/{tarea['id']}", json={**_TAREA, "etiquetas": [], "prioridad": 2}
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {**tarea, "etiquetas": [], "prioridad": 2, "subestado": None}


# --- Cambiar solo el subestado (PATCH /tareas/{id}/subestado) ---


def _cambiar_subestado(cliente: TestClient, id_tarea: int, cuerpo: object):
    return cliente.patch(f"{_TAREAS}/{id_tarea}/subestado", json=cuerpo)


def test_cambiar_el_subestado_solo_cambia_el_subestado(cliente: TestClient) -> None:
    tarea = _crear_tarea(
        cliente, subestado="Bloqueado", prioridad=2, asignados=["Ana"], descripcion="<p>Cajas</p>"
    )

    respuesta = _cambiar_subestado(cliente, tarea["id"], {"subestado": "En pausa"})

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json() == {**tarea, "subestado": "En pausa"}
    assert _tarea(cliente, tarea["id"]) == {**tarea, "subestado": "En pausa"}


def test_cambiar_a_un_subestado_nuevo_lo_da_de_alta_y_a_uno_existente_usa_su_grafia(
    cliente: TestClient,
) -> None:
    _crear_subestado(cliente, "Bloqueado")
    tarea = _crear_tarea(cliente)

    nuevo = _cambiar_subestado(cliente, tarea["id"], {"subestado": "  En pausa "})
    assert nuevo.json()["subestado"] == "En pausa"
    assert _nombres(cliente) == ["Bloqueado", "En pausa"]

    existente = _cambiar_subestado(cliente, tarea["id"], {"subestado": "BLOQUEADO"})
    assert existente.json()["subestado"] == "Bloqueado"
    assert _nombres(cliente) == ["Bloqueado", "En pausa"]


def test_cambiar_el_subestado_a_null_lo_quita_sin_borrarlo_del_catalogo(
    cliente: TestClient,
) -> None:
    tarea = _crear_tarea(cliente, subestado="Bloqueado")

    respuesta = _cambiar_subestado(cliente, tarea["id"], {"subestado": None})

    assert respuesta.status_code == 200
    assert respuesta.json()["subestado"] is None
    assert _tarea(cliente, tarea["id"])["subestado"] is None
    assert _nombres(cliente) == ["Bloqueado"]


def test_cambiar_el_subestado_de_una_tarea_que_no_existe_responde_404(
    cliente: TestClient,
) -> None:
    respuesta = _cambiar_subestado(cliente, 999999, {"subestado": "Bloqueado"})

    assert respuesta.status_code == 404
    assert respuesta.json() == {"detalle": "No existe la tarea con id 999999"}
    # No se da de alta en el catálogo un subestado para una tarea que no existe.
    assert _nombres(cliente) == []


@pytest.mark.parametrize(
    "cuerpo",
    [{}, {"subestado": ""}, {"subestado": "   "}, {"subestado": "a" * 51}, {"subestado": 5}],
)
def test_cambiar_el_subestado_con_un_cuerpo_invalido_responde_422_sin_cambiar_nada(
    cliente: TestClient, cuerpo: dict
) -> None:
    tarea = _crear_tarea(cliente, subestado="Bloqueado")

    respuesta = _cambiar_subestado(cliente, tarea["id"], cuerpo)

    assert respuesta.status_code == 422
    assert _tarea(cliente, tarea["id"]) == tarea
    assert _nombres(cliente) == ["Bloqueado"]
