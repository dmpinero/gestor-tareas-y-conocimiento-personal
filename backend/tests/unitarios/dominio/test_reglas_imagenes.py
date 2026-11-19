import pytest

from gestor_tareas.dominio.imagen.reglas import TAMANO_MAXIMO, detectar_tipo
from tests import imagenes_de_prueba


def test_el_tamano_maximo_es_de_5_mb() -> None:
    assert TAMANO_MAXIMO == 5 * 1024 * 1024


@pytest.mark.parametrize(("tipo", "contenido"), list(imagenes_de_prueba.POR_TIPO.items()))
def test_detecta_el_tipo_por_la_firma_del_contenido(tipo: str, contenido: bytes) -> None:
    assert detectar_tipo(contenido) == tipo


@pytest.mark.parametrize(
    "contenido",
    [
        b"",
        b"hola, no soy una imagen",
        b"\x89PNG\r\n",
        b"GIF88a",
        b"RIFF\x00\x00\x00\x00WAVEfmt ",
        b"RIFF\x00\x00\x00\x00WEB",
        b"\xff\xd8",
        b"<svg xmlns='http://www.w3.org/2000/svg'></svg>",
        b"%PDF-1.7",
    ],
)
def test_no_reconoce_lo_que_no_es_png_jpeg_gif_ni_webp(contenido: bytes) -> None:
    assert detectar_tipo(contenido) is None
