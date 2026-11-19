"""Pruebas de la verificación del saneado de imágenes: variantes de `src` que no
son exactamente la URL de una imagen guardada, atributos y etiquetas que intentan
colarse, y `<img` dentro del valor de otro atributo."""

import pytest

from gestor_tareas.interfaces.api.v1.esquemas.html_comentario import (
    contiene_imagenes,
    sanear_html,
)

_H = "0123456789abcdef0123456789abcdef"
_U = f"/api/v1/imagenes/{_H}"


@pytest.mark.parametrize(
    "entrada",
    [
        f'<p>a<img src="{_U.upper()}"></p>',
        f'<p>a<img src="/api/v1/imagenes/%2e%2e/{_H}"></p>',
        f'<p>a<img src="/api/v1/imagenes/\t{_H}"></p>',
        f'<p>a<img src="\\api\\v1\\imagenes\\{_H}"></p>',
        f'<p>a<img src="//evil.com{_U}"></p>',
        f'<p>a<img src="{_U}?x=1"></p>',
        f'<p>a<img src="{_U}#x"></p>',
        f'<p>a<img src=" {_U}"></p>',
        '<p>a<img src="data:image/png;base64,AAAA"></p>',
        '<p>a<svg><image href="http://e/x"/></svg></p>',
        f'<p>a<img src="javascript:alert(1)" src="{_U}"></p>',
        f'<p>a<img src="{_U}"',
    ],
)
def test_se_quita_la_imagen_cuyo_src_no_es_exactamente_el_de_una_imagen_guardada(
    entrada: str,
) -> None:
    assert sanear_html(entrada) == "<p>a</p>"


def test_el_alt_no_puede_cerrar_la_etiqueta_ni_abrir_otra() -> None:
    assert sanear_html(f'<img src="{_U}" alt=\'"><script>alert(1)</script>\'>') == (
        f'<img src="{_U}" alt="&quot;scriptalert(1)/script">'
    )


def test_de_una_imagen_solo_quedan_src_y_alt() -> None:
    entrada = (
        f'<img src="{_U}" alt="x" onerror="alert(1)" width="1" class="c" '
        'srcset="http://e/x.png 1x">'
    )
    assert sanear_html(entrada) == f'<img src="{_U}" alt="x">'


def test_picture_y_source_se_quitan_y_queda_la_imagen() -> None:
    entrada = f'<picture><source srcset="http://e/x"><img src="{_U}"></picture>'
    assert sanear_html(entrada) == f'<img src="{_U}">'


@pytest.mark.parametrize(
    "entrada",
    [
        '<a href="https://a/<img">x</a>',
        f"<mark data-color='<img src=\"{_U}\">'>x</mark>",
    ],
)
def test_un_img_dentro_del_valor_de_un_atributo_queda_escapado(entrada: str) -> None:
    saneado = sanear_html(entrada)
    assert "&lt;img" in saneado
    assert "<img" not in saneado
    assert contiene_imagenes(saneado) is False
