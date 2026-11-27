"""API de la cola de siguientes tareas: lista ordenada de tareas elegidas para
trabajar después del foco. Las completadas no se ven (y vuelven a su sitio al
reabrirlas); borrar una tarea o ponerla en foco la saca de la cola.

S12: las sugerencias elegidas son una segunda lista con las mismas reglas; una tarea
está como mucho en una de las dos, y añadirla a una la quita de la otra.

Subtareas en Siguientes (S4): una entrada es una tarea entera o una subtarea suya;
la tarea y sus subtareas son entradas distintas."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from gestor_tareas.infraestructura.persistencia.sesion import FabricaSesiones
from gestor_tareas.main import crear_aplicacion
from tests.integracion.tablas import vaciar_tablas

_TAREAS = "/api/v1/tareas"
_SIGUIENTES = "/api/v1/siguientes"
_SUGERENCIAS = "/api/v1/sugerencias"


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


def _e(
    id_tarea: int, nombre: str, id_subtarea: int | None = None, subtarea: str | None = None
) -> dict:
    """Una entrada como la devuelve la API."""
    return {
        "tarea_id": id_tarea,
        "tarea_nombre": nombre,
        "subtarea_id": id_subtarea,
        "subtarea_nombre": subtarea,
    }


def _orden(claves) -> dict:
    """Cuerpo de la reordenación: ids de tareas enteras o pares (tarea, subtarea)."""
    entradas = []
    for clave in claves:
        id_tarea, id_subtarea = clave if isinstance(clave, tuple) else (clave, None)
        entradas.append({"tarea_id": id_tarea, "subtarea_id": id_subtarea})
    return {"entradas": entradas}


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

    esperada = [_e(b, "B"), _e(a, "A")]
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

    assert cliente.get(_SIGUIENTES).json() == [_e(a, "A renombrada")]


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

    respuesta = cliente.put(_SIGUIENTES, json=_orden([c, a, b]))

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json() == [
        _e(c, "C"),
        _e(a, "A"),
        _e(b, "B"),
    ]
    assert _cola(cliente) == [c, a, b]


def test_reordenar_deja_las_completadas_detras(cliente: TestClient) -> None:
    a, b, c = (_crear_tarea(cliente, n) for n in "ABC")
    _anadir(cliente, a, b, c)
    _completar(cliente, a)

    respuesta = cliente.put(_SIGUIENTES, json=_orden([c, b]))

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

    respuesta = cliente.put(_SIGUIENTES, json=_orden(ids(a, b, c)))

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"][0]["loc"][:2] == ["body", "entradas"]
    assert _filas_guardadas() == [a, b, c]


def test_reordenar_incluyendo_una_completada_da_422(cliente: TestClient) -> None:
    a, b = _crear_tarea(cliente, "A"), _crear_tarea(cliente, "B")
    _anadir(cliente, a, b)
    _completar(cliente, b)

    respuesta = cliente.put(_SIGUIENTES, json=_orden([b, a]))

    assert respuesta.status_code == 422
    assert _filas_guardadas() == [a, b]


def test_reordenar_una_cola_vacia_sin_ids(cliente: TestClient) -> None:
    respuesta = cliente.put(_SIGUIENTES, json=_orden([]))

    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_quitar_saca_la_tarea_y_devuelve_la_cola(cliente: TestClient) -> None:
    a, b = _crear_tarea(cliente, "A"), _crear_tarea(cliente, "B")
    _anadir(cliente, a, b)

    respuesta = cliente.delete(f"{_SIGUIENTES}/{a}")

    assert respuesta.status_code == 200
    assert respuesta.json() == [_e(b, "B")]
    assert _filas_guardadas() == [b]


def test_quitar_una_que_no_estaba_responde_200_sin_cambios(cliente: TestClient) -> None:
    a, b = _crear_tarea(cliente, "A"), _crear_tarea(cliente, "B")
    _anadir(cliente, a)

    for id_tarea in (b, b + 1000):
        respuesta = cliente.delete(f"{_SIGUIENTES}/{id_tarea}")
        assert respuesta.status_code == 200
        assert respuesta.json() == [_e(a, "A")]
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


# S12: sugerencias elegidas.


def _sugerir(cliente: TestClient, *ids: int):
    respuesta = None
    for id_tarea in ids:
        respuesta = cliente.post(_SUGERENCIAS, json={"tarea_id": id_tarea})
        assert respuesta.status_code == 200, respuesta.text
    return respuesta


def _sugerencias(cliente: TestClient) -> list[int]:
    respuesta = cliente.get(_SUGERENCIAS)
    assert respuesta.status_code == 200, respuesta.text
    return [t["tarea_id"] for t in respuesta.json()]


def _filas_por_lista() -> dict[str, list[tuple[int, int]]]:
    """Las filas guardadas de cada lista, como (tarea_id, posicion) en su orden."""
    sesion = FabricaSesiones()
    try:
        filas: dict[str, list[tuple[int, int]]] = {"siguientes": [], "sugerencias": []}
        for id_tarea, lista, posicion in sesion.execute(
            text(
                "SELECT tarea_id, lista, posicion FROM cola_siguientes "
                "ORDER BY lista, posicion, tarea_id"
            )
        ).all():
            filas[lista].append((id_tarea, posicion))
        return filas
    finally:
        sesion.close()


def test_las_sugerencias_empiezan_vacias(cliente: TestClient) -> None:
    a = _crear_tarea(cliente, "A")
    _anadir(cliente, a)

    respuesta = cliente.get(_SUGERENCIAS)

    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_anadir_a_la_cola_guarda_la_lista_siguientes(cliente: TestClient) -> None:
    a, b = _crear_tarea(cliente, "A"), _crear_tarea(cliente, "B")

    _anadir(cliente, a, b)

    assert _filas_por_lista() == {"siguientes": [(a, 0), (b, 1)], "sugerencias": []}


def test_anadir_a_sugerencias_va_al_final_con_los_nombres_y_no_toca_la_cola(
    cliente: TestClient,
) -> None:
    a, b, c = (_crear_tarea(cliente, n) for n in "ABC")
    _anadir(cliente, c)

    _sugerir(cliente, b)
    respuesta = _sugerir(cliente, a)

    esperada = [_e(b, "B"), _e(a, "A")]
    assert respuesta.json() == esperada
    assert cliente.get(_SUGERENCIAS).json() == esperada
    assert _cola(cliente) == [c]
    assert _filas_por_lista() == {"siguientes": [(c, 0)], "sugerencias": [(b, 0), (a, 1)]}


def test_anadir_a_sugerencias_una_que_ya_estaba_no_cambia_nada(cliente: TestClient) -> None:
    a, b = _crear_tarea(cliente, "A"), _crear_tarea(cliente, "B")
    _sugerir(cliente, a, b)

    respuesta = _sugerir(cliente, a)

    assert [t["tarea_id"] for t in respuesta.json()] == [a, b]
    assert _filas_por_lista()["sugerencias"] == [(a, 0), (b, 1)]


def test_anadir_a_sugerencias_una_de_la_cola_la_mueve_al_final(cliente: TestClient) -> None:
    a, b, c = (_crear_tarea(cliente, n) for n in "ABC")
    _anadir(cliente, a, b)
    _sugerir(cliente, c)

    respuesta = _sugerir(cliente, a)

    assert [t["tarea_id"] for t in respuesta.json()] == [c, a]
    assert _cola(cliente) == [b]
    assert _filas_por_lista() == {"siguientes": [(b, 1)], "sugerencias": [(c, 0), (a, 1)]}


def test_anadir_a_la_cola_una_de_sugerencias_la_mueve_al_final_y_responde_la_cola(
    cliente: TestClient,
) -> None:
    a, b, c = (_crear_tarea(cliente, n) for n in "ABC")
    _sugerir(cliente, a, b)
    _anadir(cliente, c)

    respuesta = _anadir(cliente, a)

    assert respuesta.json() == [
        _e(c, "C"),
        _e(a, "A"),
    ]
    assert _sugerencias(cliente) == [b]
    assert _filas_por_lista() == {"siguientes": [(c, 0), (a, 1)], "sugerencias": [(b, 1)]}


def test_las_posiciones_son_por_lista(cliente: TestClient) -> None:
    a, b, c, d = (_crear_tarea(cliente, n) for n in "ABCD")
    _sugerir(cliente, a, b, c)

    _anadir(cliente, d)

    # La primera de la cola empieza en 0 aunque las sugerencias lleguen a 2.
    assert _filas_por_lista()["siguientes"] == [(d, 0)]


def test_anadir_a_sugerencias_una_tarea_que_no_existe_da_404_sin_cambiar_nada(
    cliente: TestClient,
) -> None:
    a = _crear_tarea(cliente, "A")
    _sugerir(cliente, a)

    respuesta = cliente.post(_SUGERENCIAS, json={"tarea_id": a + 1000})

    assert respuesta.status_code == 404
    assert respuesta.json() == {"detalle": f"No existe la tarea con id {a + 1000}"}
    assert _filas_por_lista() == {"siguientes": [], "sugerencias": [(a, 0)]}


def test_anadir_a_sugerencias_una_tarea_completada_da_422_sin_cambiar_nada(
    cliente: TestClient,
) -> None:
    a = _crear_tarea(cliente, "A")
    _anadir(cliente, a)
    _completar(cliente, a)

    respuesta = cliente.post(_SUGERENCIAS, json={"tarea_id": a})

    assert respuesta.status_code == 422
    error = respuesta.json()["detail"][0]
    assert error["loc"] == ["body", "tarea_id"]
    assert "completada" in error["msg"]
    assert _filas_por_lista() == {"siguientes": [(a, 0)], "sugerencias": []}


@pytest.mark.parametrize("cuerpo", [{}, {"tarea_id": "1"}, {"tarea_id": True}, {"tarea_id": 1.5}])
def test_anadir_a_sugerencias_sin_un_id_entero_da_422(cliente: TestClient, cuerpo: dict) -> None:
    assert cliente.post(_SUGERENCIAS, json=cuerpo).status_code == 422


def test_las_completadas_no_se_ven_en_sugerencias_y_al_reabrirlas_vuelven(
    cliente: TestClient,
) -> None:
    a, b, c = (_crear_tarea(cliente, n) for n in "ABC")
    _sugerir(cliente, a, b, c)

    _completar(cliente, b)
    assert _sugerencias(cliente) == [a, c]

    _completar(cliente, b, completada=False)
    assert _sugerencias(cliente) == [a, b, c]


def test_quitar_de_sugerencias_saca_la_tarea_y_es_idempotente(cliente: TestClient) -> None:
    a, b = _crear_tarea(cliente, "A"), _crear_tarea(cliente, "B")
    _sugerir(cliente, a, b)

    for id_tarea in (a, a, a + 1000):
        respuesta = cliente.delete(f"{_SUGERENCIAS}/{id_tarea}")
        assert respuesta.status_code == 200
        assert respuesta.json() == [_e(b, "B")]
    assert _filas_por_lista()["sugerencias"] == [(b, 1)]


def test_quitar_de_una_lista_no_toca_una_tarea_de_la_otra(cliente: TestClient) -> None:
    a, b = _crear_tarea(cliente, "A"), _crear_tarea(cliente, "B")
    _anadir(cliente, a)
    _sugerir(cliente, b)

    respuesta = cliente.delete(f"{_SIGUIENTES}/{b}")
    assert respuesta.status_code == 200
    assert [t["tarea_id"] for t in respuesta.json()] == [a]

    respuesta = cliente.delete(f"{_SUGERENCIAS}/{a}")
    assert respuesta.status_code == 200
    assert [t["tarea_id"] for t in respuesta.json()] == [b]

    assert _filas_por_lista() == {"siguientes": [(a, 0)], "sugerencias": [(b, 0)]}


def test_quitar_de_sugerencias_con_un_id_no_entero_da_404(cliente: TestClient) -> None:
    assert cliente.delete(f"{_SUGERENCIAS}/abc").status_code == 404


def test_reordenar_la_cola_valida_solo_contra_la_cola(cliente: TestClient) -> None:
    a, b, c = (_crear_tarea(cliente, n) for n in "ABC")
    _anadir(cliente, a, b)
    _sugerir(cliente, c)

    con_una_sugerencia = cliente.put(_SIGUIENTES, json=_orden([b, a, c]))
    assert con_una_sugerencia.status_code == 422

    respuesta = cliente.put(_SIGUIENTES, json=_orden([b, a]))
    assert respuesta.status_code == 200, respuesta.text
    assert [t["tarea_id"] for t in respuesta.json()] == [b, a]
    assert _filas_por_lista() == {"siguientes": [(b, 0), (a, 1)], "sugerencias": [(c, 0)]}


def test_reordenar_la_cola_deja_detras_sus_completadas_sin_tocar_sugerencias(
    cliente: TestClient,
) -> None:
    a, b, c, d = (_crear_tarea(cliente, n) for n in "ABCD")
    _anadir(cliente, a, b, c)
    _sugerir(cliente, d)
    _completar(cliente, a)
    _completar(cliente, d)

    respuesta = cliente.put(_SIGUIENTES, json=_orden([c, b]))

    assert respuesta.status_code == 200, respuesta.text
    _completar(cliente, a, completada=False)
    _completar(cliente, d, completada=False)
    assert _cola(cliente) == [c, b, a]
    assert _sugerencias(cliente) == [d]


def test_borrar_una_tarea_la_saca_de_sugerencias(cliente: TestClient) -> None:
    a, b = _crear_tarea(cliente, "A"), _crear_tarea(cliente, "B")
    _sugerir(cliente, a, b)

    assert cliente.delete(f"{_TAREAS}/{a}").status_code == 204

    assert _sugerencias(cliente) == [b]
    assert _filas_por_lista()["sugerencias"] == [(b, 1)]


def test_poner_en_foco_saca_la_tarea_de_sugerencias(cliente: TestClient) -> None:
    a = _crear_tarea(cliente, "A", subtarea="Sub")
    b, c = _crear_tarea(cliente, "B"), _crear_tarea(cliente, "C")
    _sugerir(cliente, a, b)
    _anadir(cliente, c)

    respuesta = cliente.put("/api/v1/foco", json={"tarea_id": b})
    assert respuesta.status_code == 200, respuesta.text
    respuesta = cliente.put(
        "/api/v1/foco", json={"tarea_id": a, "subtarea_id": _subtarea(cliente, a)}
    )
    assert respuesta.status_code == 200, respuesta.text

    assert _sugerencias(cliente) == []
    assert _cola(cliente) == [c]


# Subtareas en Siguientes (S4): una entrada es una tarea entera o una subtarea suya.


def _nueva_subtarea(cliente: TestClient, id_tarea: int, nombre: str) -> int:
    respuesta = cliente.post(f"{_TAREAS}/{id_tarea}/subtareas", json={"nombre": nombre})
    assert respuesta.status_code in (200, 201), respuesta.text
    tarea = next(t for t in cliente.get(_TAREAS).json() if t["id"] == id_tarea)
    return next(s["id"] for s in tarea["subtareas"] if s["nombre"] == nombre)


def _resolver(cliente: TestClient, id_tarea: int, id_subtarea: int, resuelta: bool = True) -> None:
    respuesta = cliente.patch(
        f"{_TAREAS}/{id_tarea}/subtareas/{id_subtarea}/resuelta", json={"resuelta": resuelta}
    )
    assert respuesta.status_code == 200, respuesta.text


def _entrada(url: str, cliente: TestClient, id_tarea: int, id_subtarea: int | None = None):
    respuesta = cliente.post(url, json={"tarea_id": id_tarea, "subtarea_id": id_subtarea})
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _claves(cliente: TestClient, url: str = _SIGUIENTES) -> list[tuple[int, int | None]]:
    respuesta = cliente.get(url)
    assert respuesta.status_code == 200, respuesta.text
    return [(t["tarea_id"], t["subtarea_id"]) for t in respuesta.json()]


def _filas_con_subtarea() -> list[tuple[int, int | None, str, int]]:
    sesion = FabricaSesiones()
    try:
        return [
            tuple(f)
            for f in sesion.execute(
                text(
                    "SELECT tarea_id, subtarea_id, lista, posicion FROM cola_siguientes "
                    "ORDER BY lista, posicion, id"
                )
            ).all()
        ]
    finally:
        sesion.close()


@pytest.mark.parametrize("url", [_SIGUIENTES, _SUGERENCIAS])
def test_anadir_una_subtarea_a_cada_lista_devuelve_sus_nombres(cliente: TestClient, url) -> None:
    a = _crear_tarea(cliente, "A")
    sub = _nueva_subtarea(cliente, a, "Buscar persona fuera de kmm")

    lista = _entrada(url, cliente, a, sub)

    assert lista == [_e(a, "A", sub, "Buscar persona fuera de kmm")]
    assert cliente.get(url).json() == lista
    nombre_lista = "siguientes" if url == _SIGUIENTES else "sugerencias"
    assert _filas_con_subtarea() == [(a, sub, nombre_lista, 0)]


def test_anadir_sin_subtarea_o_con_null_es_la_tarea_entera(cliente: TestClient) -> None:
    a, b = _crear_tarea(cliente, "A"), _crear_tarea(cliente, "B")

    _anadir(cliente, a)
    respuesta = cliente.post(_SIGUIENTES, json={"tarea_id": b, "subtarea_id": None})

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json() == [_e(a, "A"), _e(b, "B")]


@pytest.mark.parametrize("url", [_SIGUIENTES, _SUGERENCIAS])
def test_anadir_una_subtarea_que_no_es_de_la_tarea_da_404_sin_cambiar_nada(
    cliente: TestClient, url
) -> None:
    a, b = _crear_tarea(cliente, "A"), _crear_tarea(cliente, "B")
    de_b = _nueva_subtarea(cliente, b, "Sub B")

    for id_subtarea in (de_b, de_b + 1000):
        respuesta = cliente.post(url, json={"tarea_id": a, "subtarea_id": id_subtarea})
        assert respuesta.status_code == 404
        assert respuesta.json() == {
            "detalle": f"No existe la subtarea con id {id_subtarea} en la tarea con id {a}"
        }
    respuesta = cliente.post(url, json={"tarea_id": a + 1000, "subtarea_id": de_b})
    assert respuesta.status_code == 404
    assert respuesta.json() == {"detalle": f"No existe la tarea con id {a + 1000}"}
    assert _filas_con_subtarea() == []


@pytest.mark.parametrize("url", [_SIGUIENTES, _SUGERENCIAS])
def test_anadir_una_subtarea_resuelta_da_422_en_subtarea_id(cliente: TestClient, url) -> None:
    a = _crear_tarea(cliente, "A")
    sub = _nueva_subtarea(cliente, a, "Sub")
    _resolver(cliente, a, sub)

    respuesta = cliente.post(url, json={"tarea_id": a, "subtarea_id": sub})

    assert respuesta.status_code == 422
    error = respuesta.json()["detail"][0]
    assert error["loc"] == ["body", "subtarea_id"]
    assert "resuelta" in error["msg"]
    assert _filas_con_subtarea() == []


@pytest.mark.parametrize("url", [_SIGUIENTES, _SUGERENCIAS])
def test_anadir_una_subtarea_de_una_tarea_completada_da_422_en_tarea_id(
    cliente: TestClient, url
) -> None:
    a = _crear_tarea(cliente, "A")
    sub = _nueva_subtarea(cliente, a, "Sub")
    _completar(cliente, a)

    respuesta = cliente.post(url, json={"tarea_id": a, "subtarea_id": sub})

    assert respuesta.status_code == 422
    error = respuesta.json()["detail"][0]
    assert error["loc"] == ["body", "tarea_id"]
    assert "completada" in error["msg"]
    assert _filas_con_subtarea() == []


@pytest.mark.parametrize("cuerpo", [{"tarea_id": 1, "subtarea_id": "2"}, {"subtarea_id": 2}])
def test_anadir_con_una_subtarea_que_no_es_un_id_entero_da_422(
    cliente: TestClient, cuerpo: dict
) -> None:
    assert cliente.post(_SIGUIENTES, json=cuerpo).status_code == 422


def test_una_tarea_y_su_subtarea_estan_a_la_vez_y_cada_una_una_sola_vez(
    cliente: TestClient,
) -> None:
    a = _crear_tarea(cliente, "A")
    s1, s2 = _nueva_subtarea(cliente, a, "S1"), _nueva_subtarea(cliente, a, "S2")

    _entrada(_SIGUIENTES, cliente, a)
    _entrada(_SIGUIENTES, cliente, a, s1)
    _entrada(_SUGERENCIAS, cliente, a, s2)
    cola = _entrada(_SIGUIENTES, cliente, a, s1)

    assert cola == [_e(a, "A"), _e(a, "A", s1, "S1")]
    assert _claves(cliente, _SUGERENCIAS) == [(a, s2)]
    assert _filas_con_subtarea() == [
        (a, None, "siguientes", 0),
        (a, s1, "siguientes", 1),
        (a, s2, "sugerencias", 0),
    ]


def test_la_base_de_datos_no_admite_la_misma_entrada_dos_veces(cliente: TestClient) -> None:
    a = _crear_tarea(cliente, "A")
    sub = _nueva_subtarea(cliente, a, "Sub")
    _entrada(_SIGUIENTES, cliente, a)
    _entrada(_SIGUIENTES, cliente, a, sub)

    for subtarea in ("NULL", str(sub)):
        sesion = FabricaSesiones()
        try:
            with pytest.raises(IntegrityError):
                sesion.execute(
                    text(
                        "INSERT INTO cola_siguientes (tarea_id, subtarea_id, lista, posicion) "
                        f"VALUES ({a}, {subtarea}, 'sugerencias', 9)"
                    )
                )
        finally:
            sesion.rollback()
            sesion.close()


def test_una_subtarea_se_mueve_de_lista_sin_mover_su_tarea(cliente: TestClient) -> None:
    a, b = _crear_tarea(cliente, "A"), _crear_tarea(cliente, "B")
    sub = _nueva_subtarea(cliente, a, "Sub")
    _entrada(_SIGUIENTES, cliente, a)
    _entrada(_SIGUIENTES, cliente, a, sub)
    _entrada(_SUGERENCIAS, cliente, b)

    sugerencias = _entrada(_SUGERENCIAS, cliente, a, sub)
    assert sugerencias == [_e(b, "B"), _e(a, "A", sub, "Sub")]
    assert _claves(cliente) == [(a, None)]

    cola = _entrada(_SIGUIENTES, cliente, a, sub)
    assert cola == [_e(a, "A"), _e(a, "A", sub, "Sub")]
    assert _claves(cliente, _SUGERENCIAS) == [(b, None)]


def test_reordenar_con_entradas_de_tareas_y_subtareas(cliente: TestClient) -> None:
    a, b = _crear_tarea(cliente, "A"), _crear_tarea(cliente, "B")
    sub = _nueva_subtarea(cliente, a, "Sub")
    _entrada(_SIGUIENTES, cliente, a)
    _entrada(_SIGUIENTES, cliente, b)
    _entrada(_SIGUIENTES, cliente, a, sub)

    respuesta = cliente.put(_SIGUIENTES, json=_orden([(a, sub), b, a]))

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json() == [_e(a, "A", sub, "Sub"), _e(b, "B"), _e(a, "A")]
    assert _claves(cliente) == [(a, sub), (b, None), (a, None)]


@pytest.mark.parametrize(
    "orden",
    [
        pytest.param(lambda a, b, s: [b, a], id="falta la subtarea"),
        pytest.param(lambda a, b, s: [(a, s), (a, s), b, a], id="repite la subtarea"),
        pytest.param(lambda a, b, s: [(a, s), (b, s), a], id="subtarea de otra tarea"),
        pytest.param(lambda a, b, s: [(a, s), b, a, (a, s + 1000)], id="sobra una"),
    ],
)
def test_reordenar_con_entradas_que_no_son_la_cola_da_422_sin_cambiarla(
    cliente: TestClient, orden
) -> None:
    a, b = _crear_tarea(cliente, "A"), _crear_tarea(cliente, "B")
    sub = _nueva_subtarea(cliente, a, "Sub")
    for id_tarea, id_subtarea in ((a, None), (b, None), (a, sub)):
        _entrada(_SIGUIENTES, cliente, id_tarea, id_subtarea)
    antes = _filas_con_subtarea()

    respuesta = cliente.put(_SIGUIENTES, json=_orden(orden(a, b, sub)))

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"][0]["loc"][:2] == ["body", "entradas"]
    assert _filas_con_subtarea() == antes


def test_reordenar_con_el_cuerpo_antiguo_de_ids_da_422(cliente: TestClient) -> None:
    a = _crear_tarea(cliente, "A")
    _anadir(cliente, a)

    assert cliente.put(_SIGUIENTES, json={"ids": [a]}).status_code == 422
    assert _filas_guardadas() == [a]


def test_reordenar_deja_detras_las_subtareas_resueltas(cliente: TestClient) -> None:
    a, b = _crear_tarea(cliente, "A"), _crear_tarea(cliente, "B")
    sub = _nueva_subtarea(cliente, a, "Sub")
    for id_tarea, id_subtarea in ((a, sub), (a, None), (b, None)):
        _entrada(_SIGUIENTES, cliente, id_tarea, id_subtarea)
    _resolver(cliente, a, sub)

    respuesta = cliente.put(_SIGUIENTES, json=_orden([b, a]))

    assert respuesta.status_code == 200, respuesta.text
    _resolver(cliente, a, sub, resuelta=False)
    assert _claves(cliente) == [(b, None), (a, None), (a, sub)]


@pytest.mark.parametrize("url", [_SIGUIENTES, _SUGERENCIAS])
def test_quitar_con_o_sin_subtarea_id_saca_solo_esa_entrada_y_es_idempotente(
    cliente: TestClient, url
) -> None:
    a = _crear_tarea(cliente, "A")
    sub = _nueva_subtarea(cliente, a, "Sub")
    _entrada(url, cliente, a)
    _entrada(url, cliente, a, sub)

    for _ in range(2):
        respuesta = cliente.delete(f"{url}/{a}")
        assert respuesta.status_code == 200
        assert respuesta.json() == [_e(a, "A", sub, "Sub")]
    _entrada(url, cliente, a)
    for id_subtarea in (sub, sub, sub + 1000):
        respuesta = cliente.delete(f"{url}/{a}", params={"subtarea_id": id_subtarea})
        assert respuesta.status_code == 200
        assert respuesta.json() == [_e(a, "A")]


def test_quitar_con_una_subtarea_id_que_no_es_entera_da_422(cliente: TestClient) -> None:
    assert cliente.delete(f"{_SIGUIENTES}/1", params={"subtarea_id": "x"}).status_code == 422


@pytest.mark.parametrize("url", [_SIGUIENTES, _SUGERENCIAS])
def test_las_subtareas_resueltas_o_de_tareas_completadas_no_se_ven_y_vuelven(
    cliente: TestClient, url
) -> None:
    a, b = _crear_tarea(cliente, "A"), _crear_tarea(cliente, "B")
    sa, sb = _nueva_subtarea(cliente, a, "SA"), _nueva_subtarea(cliente, b, "SB")
    for id_tarea, id_subtarea in ((a, sa), (a, None), (b, sb)):
        _entrada(url, cliente, id_tarea, id_subtarea)

    _resolver(cliente, a, sa)
    _completar(cliente, b)
    assert _claves(cliente, url) == [(a, None)]
    assert len(_filas_con_subtarea()) == 3

    _resolver(cliente, a, sa, resuelta=False)
    _completar(cliente, b, completada=False)
    assert _claves(cliente, url) == [(a, sa), (a, None), (b, sb)]


def test_borrar_una_subtarea_quita_sus_entradas_y_deja_la_de_su_tarea(
    cliente: TestClient,
) -> None:
    a = _crear_tarea(cliente, "A")
    s1, s2 = _nueva_subtarea(cliente, a, "S1"), _nueva_subtarea(cliente, a, "S2")
    _entrada(_SIGUIENTES, cliente, a)
    _entrada(_SIGUIENTES, cliente, a, s1)
    _entrada(_SUGERENCIAS, cliente, a, s2)

    assert cliente.delete(f"{_TAREAS}/{a}/subtareas/{s1}").status_code in (200, 204)
    assert cliente.delete(f"{_TAREAS}/{a}/subtareas/{s2}").status_code in (200, 204)

    assert _claves(cliente) == [(a, None)]
    assert _claves(cliente, _SUGERENCIAS) == []
    assert _filas_con_subtarea() == [(a, None, "siguientes", 0)]


def test_borrar_una_tarea_quita_tambien_las_entradas_de_sus_subtareas(
    cliente: TestClient,
) -> None:
    a, b = _crear_tarea(cliente, "A"), _crear_tarea(cliente, "B")
    sub = _nueva_subtarea(cliente, a, "Sub")
    _entrada(_SIGUIENTES, cliente, a, sub)
    _entrada(_SUGERENCIAS, cliente, b)

    assert cliente.delete(f"{_TAREAS}/{a}").status_code == 204

    assert _filas_con_subtarea() == [(b, None, "sugerencias", 0)]


def test_foco_en_una_subtarea_quita_su_entrada_y_la_de_su_tarea(cliente: TestClient) -> None:
    a = _crear_tarea(cliente, "A")
    s1, s2 = _nueva_subtarea(cliente, a, "S1"), _nueva_subtarea(cliente, a, "S2")
    _entrada(_SIGUIENTES, cliente, a)
    _entrada(_SUGERENCIAS, cliente, a, s1)
    _entrada(_SIGUIENTES, cliente, a, s2)

    respuesta = cliente.put("/api/v1/foco", json={"tarea_id": a, "subtarea_id": s1})

    assert respuesta.status_code == 200, respuesta.text
    assert _claves(cliente) == [(a, s2)]
    assert _claves(cliente, _SUGERENCIAS) == []


def test_foco_en_una_tarea_entera_quita_solo_su_entrada(cliente: TestClient) -> None:
    a = _crear_tarea(cliente, "A")
    sub = _nueva_subtarea(cliente, a, "Sub")
    _entrada(_SIGUIENTES, cliente, a)
    _entrada(_SUGERENCIAS, cliente, a, sub)

    respuesta = cliente.put("/api/v1/foco", json={"tarea_id": a})

    assert respuesta.status_code == 200, respuesta.text
    assert _claves(cliente) == []
    assert _claves(cliente, _SUGERENCIAS) == [(a, sub)]
