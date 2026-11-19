"""Comentarios con imágenes en los tres sitios (tareas, subtareas y pasos de los
workflows) y en la copia de los comentarios de los pasos a las subtareas."""

import pytest
from fastapi.testclient import TestClient

from gestor_tareas.infraestructura.persistencia.sesion import FabricaSesiones
from gestor_tareas.main import crear_aplicacion
from tests import imagenes_de_prueba
from tests.integracion.tablas import vaciar_tablas

_DATOS_TAREA = {"descripcion": "d", "fecha_creacion": "2026-11-10T09:00:00"}


@pytest.fixture
def cliente() -> TestClient:
    sesion = FabricaSesiones()
    vaciar_tablas(sesion)
    sesion.close()
    return TestClient(crear_aplicacion())


def _imagen(cliente: TestClient) -> str:
    respuesta = cliente.post(
        "/api/v1/imagenes",
        files={"archivo": ("captura.png", imagenes_de_prueba.PNG, "image/png")},
        headers={"X-Requested-With": "gestor-tareas"},
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["url"]


def _rutas_de_comentarios(cliente: TestClient) -> list[str]:
    tarea = cliente.post("/api/v1/tareas", json={**_DATOS_TAREA, "nombre": "T"}).json()
    # El alta de una subtarea devuelve la tarea con sus subtareas.
    subtarea = cliente.post(f"/api/v1/tareas/{tarea['id']}/subtareas", json={"nombre": "S"}).json()[
        "subtareas"
    ][0]
    workflow = cliente.post("/api/v1/workflows", json={"nombre": "W"}).json()
    paso = cliente.post(f"/api/v1/workflows/{workflow['id']}/pasos", json={"nombre": "P"}).json()[
        "pasos"
    ][0]
    return [
        f"/api/v1/tareas/{tarea['id']}/comentarios",
        f"/api/v1/tareas/{tarea['id']}/subtareas/{subtarea['id']}/comentarios",
        f"/api/v1/workflows/{workflow['id']}/pasos/{paso['id']}/comentarios",
    ]


def test_los_tres_tipos_de_comentario_admiten_solo_una_imagen_y_al_editar(
    cliente: TestClient,
) -> None:
    url = _imagen(cliente)
    html = f'<p><img src="{url}" alt="Captura de pantalla"></p>'
    for ruta in _rutas_de_comentarios(cliente):
        alta = cliente.post(ruta, json={"texto": html})
        assert alta.status_code == 201, (ruta, alta.text)
        assert alta.json()["texto"] == html
        editado = cliente.put(
            f"{ruta}/{alta.json()['id']}",
            json={"texto": f'<p>Antes<img src="{url}" onerror="x()"></p>'},
        )
        assert editado.status_code == 200, (ruta, editado.text)
        assert editado.json()["texto"] == f'<p>Antes<img src="{url}"></p>'
        assert cliente.get(ruta).json()[0]["texto"] == f'<p>Antes<img src="{url}"></p>'


def test_los_tres_tipos_de_comentario_quitan_las_imagenes_externas(cliente: TestClient) -> None:
    for ruta in _rutas_de_comentarios(cliente):
        respuesta = cliente.post(
            ruta, json={"texto": '<p>a<img src="https://ejemplo.com/x.png"></p>'}
        )
        assert respuesta.status_code == 201, (ruta, respuesta.text)
        assert respuesta.json()["texto"] == "<p>a</p>"
        vacio = cliente.post(ruta, json={"texto": '<p><img src="https://ejemplo.com/x.png"></p>'})
        assert vacio.status_code == 422, ruta


def test_la_copia_de_los_comentarios_de_un_paso_conserva_sus_imagenes(
    cliente: TestClient,
) -> None:
    url = _imagen(cliente)
    workflow = cliente.post("/api/v1/workflows", json={"nombre": "W"}).json()
    paso = cliente.post(f"/api/v1/workflows/{workflow['id']}/pasos", json={"nombre": "P"}).json()[
        "pasos"
    ][0]
    html = f'<p>Ver<img src="{url}" alt="Captura de pantalla"></p>'
    ruta_paso = f"/api/v1/workflows/{workflow['id']}/pasos/{paso['id']}/comentarios"
    assert cliente.post(ruta_paso, json={"texto": html}).status_code == 201

    tarea = cliente.post(
        "/api/v1/tareas", json={**_DATOS_TAREA, "nombre": "T", "workflow_id": workflow["id"]}
    )
    assert tarea.status_code == 201, tarea.text
    subtarea = tarea.json()["subtareas"][0]
    copiados = cliente.get(
        f"/api/v1/tareas/{tarea.json()['id']}/subtareas/{subtarea['id']}/comentarios"
    ).json()

    assert [c["texto"] for c in copiados] == [html]
    # La copia apunta a la misma imagen guardada, que se sigue descargando.
    assert cliente.get(url).content == imagenes_de_prueba.PNG
