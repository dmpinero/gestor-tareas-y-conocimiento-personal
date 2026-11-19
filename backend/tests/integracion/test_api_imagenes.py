"""API de las imágenes de los comentarios: subirlas (multipart) y descargarlas."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from gestor_tareas.infraestructura.persistencia.modelos import ImagenModelo
from gestor_tareas.infraestructura.persistencia.sesion import FabricaSesiones
from gestor_tareas.main import crear_aplicacion
from tests import imagenes_de_prueba

_IMAGENES = "/api/v1/imagenes"


@pytest.fixture(scope="module")
def cliente() -> TestClient:
    return TestClient(crear_aplicacion())


_CABECERA = {"X-Requested-With": "gestor-tareas"}


def _subir(
    cliente: TestClient,
    contenido: bytes,
    nombre: str = "captura.png",
    tipo: str = "image/png",
    cabeceras: dict[str, str] | None = None,
):
    return cliente.post(
        _IMAGENES,
        files={"archivo": (nombre, contenido, tipo)},
        headers=_CABECERA if cabeceras is None else cabeceras,
    )


def _numero_de_imagenes() -> int:
    sesion = FabricaSesiones()
    try:
        return sesion.scalar(select(func.count()).select_from(ImagenModelo)) or 0
    finally:
        sesion.close()


@pytest.mark.parametrize(
    "cabeceras",
    [{}, {"X-Requested-With": "XMLHttpRequest"}, {"X-Requested-With": ""}],
)
def test_subir_sin_la_cabecera_de_la_aplicacion_se_rechaza_con_403_y_no_guarda_nada(
    cliente: TestClient, cabeceras: dict[str, str]
) -> None:
    antes = _numero_de_imagenes()

    respuesta = _subir(cliente, imagenes_de_prueba.PNG, cabeceras=cabeceras)

    assert respuesta.status_code == 403
    assert respuesta.json() == {
        "detalle": "La subida de imágenes solo se admite desde la propia aplicación"
    }
    assert _numero_de_imagenes() == antes


def test_subir_con_la_cabecera_de_la_aplicacion_se_admite(cliente: TestClient) -> None:
    antes = _numero_de_imagenes()

    respuesta = _subir(cliente, imagenes_de_prueba.PNG)

    assert respuesta.status_code == 201, respuesta.text
    assert _numero_de_imagenes() == antes + 1


@pytest.mark.parametrize(("tipo", "contenido"), list(imagenes_de_prueba.POR_TIPO.items()))
def test_subir_una_imagen_de_un_tipo_admitido_la_guarda_y_devuelve_su_url(
    cliente: TestClient, tipo: str, contenido: bytes
) -> None:
    # El tipo que declara el cliente no cuenta: se guarda el detectado.
    respuesta = _subir(cliente, contenido, tipo="application/octet-stream")

    assert respuesta.status_code == 201, respuesta.text
    datos = respuesta.json()
    assert set(datos) == {"id", "url", "tipo", "tamano"}
    assert len(datos["id"]) == 32
    assert datos["url"] == f"{_IMAGENES}/{datos['id']}"
    assert (datos["tipo"], datos["tamano"]) == (tipo, len(contenido))


def test_descargar_una_imagen_devuelve_sus_bytes_con_su_tipo_y_cache_larga(
    cliente: TestClient,
) -> None:
    url = _subir(cliente, imagenes_de_prueba.GIF, tipo="image/png").json()["url"]

    respuesta = cliente.get(url)

    assert respuesta.status_code == 200
    assert respuesta.content == imagenes_de_prueba.GIF
    assert respuesta.headers["content-type"] == "image/gif"
    assert respuesta.headers["x-content-type-options"] == "nosniff"
    assert respuesta.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert respuesta.headers["content-disposition"] == "inline"
    assert respuesta.headers["content-length"] == str(len(imagenes_de_prueba.GIF))


def test_cada_subida_tiene_su_propio_id(cliente: TestClient) -> None:
    ids = {_subir(cliente, imagenes_de_prueba.PNG).json()["id"] for _ in range(3)}
    assert len(ids) == 3


@pytest.mark.parametrize(
    "contenido",
    [
        b"hola, soy un texto con extension png",
        b"<svg xmlns='http://www.w3.org/2000/svg' onload='alert(1)'></svg>",
        b"",
    ],
)
def test_subir_un_archivo_que_no_es_una_imagen_admitida_se_rechaza_con_422(
    cliente: TestClient, contenido: bytes
) -> None:
    respuesta = _subir(cliente, contenido, nombre="captura.png", tipo="image/png")

    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": "El archivo no es una imagen PNG, JPEG, GIF o WebP"}


def test_subir_una_imagen_de_mas_de_5_mb_se_rechaza_con_413(cliente: TestClient) -> None:
    contenido = imagenes_de_prueba.PNG + b"\x00" * (5 * 1024 * 1024)

    respuesta = _subir(cliente, contenido)

    assert respuesta.status_code == 413
    assert respuesta.json() == {"detalle": "La imagen no puede pasar de 5 MB"}


def test_se_admite_una_imagen_de_justo_5_mb(cliente: TestClient) -> None:
    contenido = imagenes_de_prueba.PNG
    contenido += b"\x00" * (5 * 1024 * 1024 - len(contenido))

    respuesta = _subir(cliente, contenido)

    assert respuesta.status_code == 201, respuesta.text
    assert cliente.get(respuesta.json()["url"]).content == contenido


def test_subir_sin_archivo_se_rechaza_con_422(cliente: TestClient) -> None:
    assert cliente.post(_IMAGENES, data={"otro": "x"}, headers=_CABECERA).status_code == 422


def test_descargar_una_imagen_que_no_existe_devuelve_404(cliente: TestClient) -> None:
    respuesta = cliente.get(f"{_IMAGENES}/{'0' * 32}")

    assert respuesta.status_code == 404
    assert respuesta.json() == {"detalle": f"No existe la imagen con id {'0' * 32}"}


@pytest.mark.parametrize("id_imagen", ["123", "..%2Ftareas", "0" * 31 + "G", "A" * 32])
def test_descargar_con_un_id_mal_formado_se_rechaza(cliente: TestClient, id_imagen: str) -> None:
    assert cliente.get(f"{_IMAGENES}/{id_imagen}").status_code in (404, 422)
