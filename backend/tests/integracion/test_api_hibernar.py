"""API de la hibernación de las tareas: hibernar detiene el contador de vencimiento
(con un comentario opcional que queda en el histórico de la tarea) y reanudar corre
su vencimiento lo que estuvo hibernada. Se puede hibernar y reanudar cuantas veces
se quiera, pero no hibernar una tarea ya hibernada ni reanudar una que no lo está."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from gestor_tareas.infraestructura.persistencia.sesion import FabricaSesiones
from gestor_tareas.main import crear_aplicacion
from tests.integracion.tablas import vaciar_tablas

_TAREAS = "/api/v1/tareas"
_TAREA = {
    "nombre": "Migración portal",
    "descripcion": "Pasar el portal a la nube",
    "fecha_creacion": "2026-11-10T09:00:00",
    "fecha_vencimiento": "2026-12-01T10:00:00",
}


@pytest.fixture
def cliente() -> TestClient:
    sesion = FabricaSesiones()
    try:
        vaciar_tablas(sesion)
    finally:
        sesion.close()
    return TestClient(crear_aplicacion())


def _crear_tarea(cliente: TestClient, **cambios: object) -> dict:
    respuesta = cliente.post(_TAREAS, json={**_TAREA, **cambios})
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _leer(cliente: TestClient, id_tarea: int) -> dict:
    """La tarea tal como la devuelve el listado (no hay lectura de una sola tarea)."""
    respuesta = cliente.get(_TAREAS)
    assert respuesta.status_code == 200
    return next(t for t in respuesta.json() if t["id"] == id_tarea)


def _ahora() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def _instante(texto: str) -> datetime:
    assert texto.endswith("Z")
    return datetime.fromisoformat(texto)


def _fila(id_tarea: int) -> tuple[datetime | None, datetime | None]:
    """(hibernada_desde, fecha_vencimiento) guardados de la tarea."""
    sesion = FabricaSesiones()
    try:
        fila = sesion.execute(
            text("SELECT hibernada_desde, fecha_vencimiento FROM tareas WHERE id = :t"),
            {"t": id_tarea},
        ).one()
        return fila.hibernada_desde, fila.fecha_vencimiento
    finally:
        sesion.close()


def _comentarios_guardados() -> list[tuple]:
    sesion = FabricaSesiones()
    try:
        return [
            tuple(f)
            for f in sesion.execute(
                text("SELECT tarea_id, texto, creado FROM comentarios ORDER BY id")
            ).all()
        ]
    finally:
        sesion.close()


def _fijar_hibernada_desde(id_tarea: int, instante: datetime) -> None:
    """Simula que la tarea lleva hibernada desde ``instante`` (UTC)."""
    sesion = FabricaSesiones()
    try:
        sesion.execute(
            text("UPDATE tareas SET hibernada_desde = :h WHERE id = :t"),
            {"h": instante.replace(tzinfo=None), "t": id_tarea},
        )
        sesion.commit()
    finally:
        sesion.close()


def test_una_tarea_nueva_no_esta_hibernada_y_conserva_sus_datos(cliente: TestClient) -> None:
    tarea = _crear_tarea(cliente)

    cuerpo = _leer(cliente, tarea["id"])

    assert cuerpo["hibernada_desde"] is None
    assert cuerpo == tarea
    assert cuerpo["fecha_vencimiento"] == "2026-12-01T10:00:00"
    assert cuerpo["congelada_en"] is None
    assert cuerpo["completada"] is False


def test_hibernar_sin_comentario_detiene_el_contador_desde_ahora(cliente: TestClient) -> None:
    tarea = _crear_tarea(cliente)
    antes = _ahora()

    respuesta = cliente.post(f"{_TAREAS}/{tarea['id']}/hibernar", json={"comentario": None})

    despues = _ahora()
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    desde = _instante(cuerpo["hibernada_desde"])
    assert antes <= desde <= despues
    # El resto de la tarea no cambia: ni el vencimiento, ni completada, ni congelada_en.
    assert {**cuerpo, "hibernada_desde": None} == tarea
    assert _fila(tarea["id"]) == (desde.replace(tzinfo=None), datetime(2026, 12, 1, 10))
    assert _comentarios_guardados() == []
    # Al leerla después sigue hibernada.
    assert _leer(cliente, tarea["id"]) == cuerpo


def test_hibernar_sin_cuerpo_tampoco_anade_comentario(cliente: TestClient) -> None:
    tarea = _crear_tarea(cliente)

    respuesta = cliente.post(f"{_TAREAS}/{tarea['id']}/hibernar")

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["hibernada_desde"] is not None
    assert _comentarios_guardados() == []


def test_hibernar_con_comentario_lo_anade_como_un_comentario_normal(
    cliente: TestClient,
) -> None:
    tarea = _crear_tarea(cliente)

    respuesta = cliente.post(
        f"{_TAREAS}/{tarea['id']}/hibernar", json={"comentario": "  Esperando al cliente  "}
    )

    assert respuesta.status_code == 200, respuesta.text
    desde = respuesta.json()["hibernada_desde"]
    comentarios = cliente.get(f"{_TAREAS}/{tarea['id']}/comentarios").json()
    # Saneado como en el alta de un comentario, con el instante de la hibernación.
    assert [(c["texto"], c["creado"], c["editado"]) for c in comentarios] == [
        ("<p>Esperando al cliente</p>", desde, None)
    ]
    assert _comentarios_guardados() == [
        (
            tarea["id"],
            "<p>Esperando al cliente</p>",
            _instante(desde).replace(tzinfo=None),
        )
    ]


@pytest.mark.parametrize("comentario", ["", "   ", "<p>  </p>", 7])
def test_un_comentario_invalido_da_422_y_no_hiberna(
    cliente: TestClient, comentario: object
) -> None:
    tarea = _crear_tarea(cliente)

    respuesta = cliente.post(f"{_TAREAS}/{tarea['id']}/hibernar", json={"comentario": comentario})

    assert respuesta.status_code == 422, respuesta.text
    assert _fila(tarea["id"]) == (None, datetime(2026, 12, 1, 10))
    assert _comentarios_guardados() == []


def test_un_comentario_demasiado_largo_da_422(cliente: TestClient) -> None:
    tarea = _crear_tarea(cliente)

    respuesta = cliente.post(f"{_TAREAS}/{tarea['id']}/hibernar", json={"comentario": "a" * 5001})

    assert respuesta.status_code == 422, respuesta.text
    assert _fila(tarea["id"])[0] is None


def test_hibernar_una_tarea_ya_hibernada_da_409_sin_cambiar_nada(cliente: TestClient) -> None:
    tarea = _crear_tarea(cliente)
    primera = cliente.post(f"{_TAREAS}/{tarea['id']}/hibernar", json={"comentario": "Primera"})
    assert primera.status_code == 200
    guardado = _fila(tarea["id"])

    respuesta = cliente.post(f"{_TAREAS}/{tarea['id']}/hibernar", json={"comentario": "Segunda"})

    assert respuesta.status_code == 409
    assert respuesta.json() == {"detalle": f"La tarea con id {tarea['id']} ya está hibernada"}
    assert _fila(tarea["id"]) == guardado
    assert [c[1] for c in _comentarios_guardados()] == ["<p>Primera</p>"]


def test_hibernar_una_tarea_que_no_existe_da_404(cliente: TestClient) -> None:
    respuesta = cliente.post(f"{_TAREAS}/999999/hibernar", json={"comentario": "Hola"})

    assert respuesta.status_code == 404
    assert respuesta.json() == {"detalle": "No existe la tarea con id 999999"}
    assert _comentarios_guardados() == []


def test_reanudar_corre_el_vencimiento_lo_que_estuvo_hibernada(cliente: TestClient) -> None:
    tarea = _crear_tarea(cliente)
    cliente.post(f"{_TAREAS}/{tarea['id']}/hibernar", json={"comentario": None})
    # Lleva hibernada dos horas y media.
    _fijar_hibernada_desde(tarea["id"], _ahora() - timedelta(hours=2, minutes=30))
    vencimiento = datetime(2026, 12, 1, 10)

    antes = _ahora()
    respuesta = cliente.post(f"{_TAREAS}/{tarea['id']}/reanudar")
    despues = _ahora()

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["hibernada_desde"] is None
    nuevo = datetime.fromisoformat(cuerpo["fecha_vencimiento"])
    hibernado = timedelta(hours=2, minutes=30)
    assert vencimiento + hibernado <= nuevo <= vencimiento + hibernado + (despues - antes)
    assert nuevo.microsecond == 0
    # Solo cambian el vencimiento y la hibernación.
    assert {**cuerpo, "fecha_vencimiento": tarea["fecha_vencimiento"]} == tarea
    assert _fila(tarea["id"]) == (None, nuevo)
    assert _comentarios_guardados() == []


def test_reanudar_una_tarea_sin_vencimiento_solo_quita_la_hibernacion(
    cliente: TestClient,
) -> None:
    tarea = _crear_tarea(cliente, fecha_vencimiento=None)
    cliente.post(f"{_TAREAS}/{tarea['id']}/hibernar")

    respuesta = cliente.post(f"{_TAREAS}/{tarea['id']}/reanudar")

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json() == tarea
    assert _fila(tarea["id"]) == (None, None)


def test_reanudar_una_tarea_que_no_esta_hibernada_da_409(cliente: TestClient) -> None:
    tarea = _crear_tarea(cliente)

    respuesta = cliente.post(f"{_TAREAS}/{tarea['id']}/reanudar")

    assert respuesta.status_code == 409
    assert respuesta.json() == {"detalle": f"La tarea con id {tarea['id']} no está hibernada"}
    assert _fila(tarea["id"]) == (None, datetime(2026, 12, 1, 10))


def test_reanudar_una_tarea_que_no_existe_da_404(cliente: TestClient) -> None:
    respuesta = cliente.post(f"{_TAREAS}/999999/reanudar")

    assert respuesta.status_code == 404
    assert respuesta.json() == {"detalle": "No existe la tarea con id 999999"}


def test_se_puede_hibernar_y_reanudar_cuantas_veces_se_quiera(cliente: TestClient) -> None:
    tarea = _crear_tarea(cliente)
    ruta = f"{_TAREAS}/{tarea['id']}"

    for vuelta in range(3):
        hibernada = cliente.post(f"{ruta}/hibernar", json={"comentario": f"Vuelta {vuelta}"})
        assert hibernada.status_code == 200, hibernada.text
        assert hibernada.json()["hibernada_desde"] is not None
        reanudada = cliente.post(f"{ruta}/reanudar")
        assert reanudada.status_code == 200, reanudada.text
        assert reanudada.json()["hibernada_desde"] is None

    assert [c[1] for c in _comentarios_guardados()] == [
        "<p>Vuelta 0</p>",
        "<p>Vuelta 1</p>",
        "<p>Vuelta 2</p>",
    ]


def test_completar_editar_o_listar_no_termina_la_hibernacion(cliente: TestClient) -> None:
    tarea = _crear_tarea(cliente)
    ruta = f"{_TAREAS}/{tarea['id']}"
    desde = cliente.post(f"{ruta}/hibernar").json()["hibernada_desde"]

    completada = cliente.patch(f"{ruta}/completada", json={"completada": True})
    assert completada.status_code == 200
    assert completada.json()["hibernada_desde"] == desde
    assert completada.json()["congelada_en"] is not None

    pendiente = cliente.patch(f"{ruta}/completada", json={"completada": False})
    assert pendiente.json()["hibernada_desde"] == desde
    assert pendiente.json()["congelada_en"] is None

    # Editar el vencimiento a mano se admite y no quita la hibernación.
    editada = cliente.put(ruta, json={**_TAREA, "fecha_vencimiento": "2026-12-05T08:00:00"})
    assert editada.status_code == 200, editada.text
    assert editada.json()["hibernada_desde"] == desde
    assert editada.json()["fecha_vencimiento"] == "2026-12-05T08:00:00"

    listado = cliente.get(_TAREAS).json()
    assert [t["hibernada_desde"] for t in listado] == [desde]
    assert _fila(tarea["id"]) == (
        _instante(desde).replace(tzinfo=None),
        datetime(2026, 12, 5, 8),
    )
