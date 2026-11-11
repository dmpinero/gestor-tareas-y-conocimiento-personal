import pytest
from fastapi.testclient import TestClient
from httpx import Response
from pytest_bdd import given, parsers, scenarios, then, when
from sqlalchemy import func, select

from gestor_tareas.infraestructura.persistencia import modelos
from gestor_tareas.infraestructura.persistencia.sesion import FabricaSesiones

scenarios("borrar_tarea.feature")

_TAREAS = "/api/v1/tareas"

_DATOS = {"descripcion": "d", "fecha_creacion": "2026-11-10T09:00:00"}


def _lista(texto: str) -> list[str]:
    return texto.split(", ") if texto else []


def _tareas(cliente: TestClient) -> list[dict]:
    respuesta = cliente.get(_TAREAS)
    assert respuesta.status_code == 200
    return respuesta.json()


def _tarea(cliente: TestClient, nombre: str) -> dict:
    return next(t for t in _tareas(cliente) if t["nombre"] == nombre)


def _crear(cliente: TestClient, cuerpo: dict) -> dict:
    respuesta = cliente.post(_TAREAS, json=cuerpo)
    assert respuesta.status_code == 201
    return respuesta.json()


def _anadir_subtarea(cliente: TestClient, id_tarea: int, cuerpo: dict) -> int:
    respuesta = cliente.post(f"{_TAREAS}/{id_tarea}/subtareas", json=cuerpo)
    assert respuesta.status_code == 201
    return respuesta.json()["subtareas"][-1]["id"]


def _comentar(cliente: TestClient, ruta: str, texto: str) -> None:
    assert cliente.post(f"{ruta}/comentarios", json={"texto": texto}).status_code == 201


def _filas_de_tarea(id_tarea: int) -> dict[str, int]:
    """Número de filas de la tarea en cada tabla que depende de ella."""
    sesion = FabricaSesiones()
    try:
        id_subtareas = select(modelos.SubtareaModelo.id).where(
            modelos.SubtareaModelo.tarea_id == id_tarea
        )
        consultas = {
            "tareas": select(func.count()).where(modelos.TareaModelo.id == id_tarea),
            "oportunidades": select(func.count()).where(
                modelos.OportunidadModelo.tarea_id == id_tarea
            ),
            "tarea_etiquetas": select(func.count()).where(
                modelos.tarea_etiquetas.c.tarea_id == id_tarea
            ),
            "tarea_personas": select(func.count()).where(
                modelos.tarea_personas.c.tarea_id == id_tarea
            ),
            "subtareas": select(func.count()).where(modelos.SubtareaModelo.tarea_id == id_tarea),
            "comentarios": select(func.count()).where(
                modelos.ComentarioModelo.tarea_id == id_tarea
            ),
            "comentarios_subtarea": select(func.count()).where(
                modelos.ComentarioSubtareaModelo.subtarea_id.in_(id_subtareas)
            ),
        }
        return {tabla: sesion.scalar(consulta) for tabla, consulta in consultas.items()}
    finally:
        sesion.close()


@pytest.fixture
def ids() -> dict[str, int]:
    """Ids de las tareas de los antecedentes, por nombre."""
    return {}


@given(
    parsers.parse(
        'que existe la oportunidad "{nombre}" con la etiqueta "{etiqueta}" y la persona "{persona}"'
    )
)
def existe_la_oportunidad(
    cliente: TestClient, ids: dict[str, int], nombre: str, etiqueta: str, persona: str
) -> None:
    tarea = _crear(
        cliente,
        {
            **_DATOS,
            "nombre": nombre,
            "etiquetas": [etiqueta],
            "asignados": [persona],
            "tipo": "oportunidad",
            "oportunidad": {"codigo": "OP-1"},
        },
    )
    ids[nombre] = tarea["id"]


@given(
    parsers.parse(
        'que "{tarea}" tiene la subtarea "{subtarea}" asignada a "{persona}" con el '
        'comentario "{texto}"'
    )
)
def tiene_la_subtarea(
    cliente: TestClient, ids: dict[str, int], tarea: str, subtarea: str, persona: str, texto: str
) -> None:
    id_subtarea = _anadir_subtarea(cliente, ids[tarea], {"nombre": subtarea, "asignado": persona})
    _comentar(cliente, f"{_TAREAS}/{ids[tarea]}/subtareas/{id_subtarea}", texto)


@given(parsers.parse('que "{tarea}" tiene el comentario "{texto}"'))
def tiene_el_comentario(cliente: TestClient, ids: dict[str, int], tarea: str, texto: str) -> None:
    _comentar(cliente, f"{_TAREAS}/{ids[tarea]}", texto)


@given(
    parsers.parse(
        'que existe la tarea "{nombre}" con la subtarea "{subtarea}" y el comentario "{texto}"'
    )
)
def existe_la_tarea(
    cliente: TestClient, ids: dict[str, int], nombre: str, subtarea: str, texto: str
) -> None:
    ids[nombre] = _crear(cliente, {**_DATOS, "nombre": nombre})["id"]
    id_subtarea = _anadir_subtarea(cliente, ids[nombre], {"nombre": subtarea})
    _comentar(cliente, f"{_TAREAS}/{ids[nombre]}/subtareas/{id_subtarea}", texto)
    _comentar(cliente, f"{_TAREAS}/{ids[nombre]}", texto)


@given(parsers.parse('que he borrado la tarea "{nombre}"'))
def he_borrado_la_tarea(cliente: TestClient, ids: dict[str, int], nombre: str) -> None:
    assert cliente.delete(f"{_TAREAS}/{ids[nombre]}").status_code == 204


@when(parsers.parse('borro la tarea "{nombre}"'), target_fixture="respuesta")
def borrar_tarea(cliente: TestClient, ids: dict[str, int], nombre: str) -> Response:
    # Antes de borrar, la tarea tiene filas en todas las tablas que dependen de ella.
    assert all(n > 0 for n in _filas_de_tarea(ids[nombre]).values())
    return cliente.delete(f"{_TAREAS}/{ids[nombre]}")


@when(parsers.parse("intento borrar la tarea con id {id_tarea:d}"), target_fixture="respuesta")
def borrar_tarea_inexistente(cliente: TestClient, id_tarea: int) -> Response:
    return cliente.delete(f"{_TAREAS}/{id_tarea}")


@when(parsers.parse('intento borrar otra vez la tarea "{nombre}"'), target_fixture="respuesta")
def borrar_otra_vez(cliente: TestClient, ids: dict[str, int], nombre: str) -> Response:
    return cliente.delete(f"{_TAREAS}/{ids[nombre]}")


@then("la API responde 204 sin contenido")
def la_api_responde_sin_contenido(respuesta: Response) -> None:
    assert respuesta.status_code == 204
    assert respuesta.content == b""


@then(parsers.parse('al consultar las tareas solo aparece "{nombre}"'))
def solo_aparece(cliente: TestClient, nombre: str) -> None:
    assert [t["nombre"] for t in _tareas(cliente)] == [nombre]


@then(parsers.parse('al consultar las tareas aparecen "{nombres}"'))
def aparecen(cliente: TestClient, nombres: str) -> None:
    assert [t["nombre"] for t in _tareas(cliente)] == _lista(nombres)


@then(parsers.parse('en la base de datos no queda nada de "{nombre}"'))
def no_queda_nada(ids: dict[str, int], nombre: str) -> None:
    assert set(_filas_de_tarea(ids[nombre]).values()) == {0}


@then(parsers.parse('"{nombre}" conserva sus subtareas y sus comentarios'))
def conserva_sus_datos(cliente: TestClient, ids: dict[str, int], nombre: str) -> None:
    filas = _filas_de_tarea(ids[nombre])
    assert (filas["subtareas"], filas["comentarios"], filas["comentarios_subtarea"]) == (1, 1, 1)
    tarea = _tarea(cliente, nombre)
    assert [(s["nombre"], s["comentarios"]) for s in tarea["subtareas"]] == [("Capítulo 1", 1)]


@then(parsers.parse('el catálogo de etiquetas sigue teniendo "{nombres}"'))
def catalogo_de_etiquetas(cliente: TestClient, nombres: str) -> None:
    respuesta = cliente.get("/api/v1/etiquetas")
    assert respuesta.status_code == 200
    assert [e["nombre"] for e in respuesta.json()] == _lista(nombres)


@then(parsers.parse('el catálogo de personas sigue teniendo "{nombres}"'))
def catalogo_de_personas(cliente: TestClient, nombres: str) -> None:
    respuesta = cliente.get("/api/v1/personas")
    assert respuesta.status_code == 200
    assert [p["nombre"] for p in respuesta.json()] == _lista(nombres)


@then(parsers.parse("la API responde que no existe la tarea con id {id_tarea:d}"))
def la_api_responde_tarea_inexistente(respuesta: Response, id_tarea: int) -> None:
    # El cuerpo distingue el 404 de dominio del 404 de "ruta no encontrada".
    assert respuesta.status_code == 404
    assert respuesta.json() == {"detalle": f"No existe la tarea con id {id_tarea}"}


@then(parsers.parse('la API responde que no existe la tarea "{nombre}"'))
def la_api_responde_tarea_borrada(respuesta: Response, ids: dict[str, int], nombre: str) -> None:
    la_api_responde_tarea_inexistente(respuesta, ids[nombre])
