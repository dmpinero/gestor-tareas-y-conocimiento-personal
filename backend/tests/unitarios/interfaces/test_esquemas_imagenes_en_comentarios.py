"""Imágenes en los comentarios: el saneado solo deja `img` que apuntan a las imágenes
guardadas en la propia aplicación, y un comentario con solo imágenes es válido."""

import pytest
from pydantic import ValidationError

from gestor_tareas.interfaces.api.v1.esquemas.comentario import ComentarioCrearEsquema

_ID = "0123456789abcdef0123456789abcdef"
_SRC = f"/api/v1/imagenes/{_ID}"


def test_el_comentario_conserva_una_imagen_guardada_con_su_texto_alternativo() -> None:
    html = f'<p>Mira:</p><p><img src="{_SRC}" alt="Captura de pantalla"></p>'
    assert ComentarioCrearEsquema(texto=html).texto == html


def test_el_comentario_conserva_una_imagen_guardada_sin_texto_alternativo() -> None:
    html = f'<p>a<img src="{_SRC}"></p>'
    assert ComentarioCrearEsquema(texto=html).texto == html


@pytest.mark.parametrize(
    "src",
    [
        "https://ejemplo.com/a.png",
        "http://ejemplo.com/api/v1/imagenes/" + _ID,
        "//ejemplo.com/api/v1/imagenes/" + _ID,
        "data:image/png;base64,iVBORw0KGgo=",
        "javascript:alert(1)",
        "/api/v1/imagenes/../tareas",
        f"/api/v1/imagenes/{_ID}/../../tareas",
        f"/api/v1/imagenes/{_ID}?x=1",
        f"/api/v1/imagenes/{_ID}#x",
        "/api/v1/imagenes/" + _ID.upper(),
        "/api/v1/imagenes/123",
        "/api/v1/tareas/1",
        "imagenes/" + _ID,
        f" {_SRC}",
        "",
    ],
)
def test_el_comentario_elimina_una_imagen_que_no_es_de_la_aplicacion(src: str) -> None:
    assert ComentarioCrearEsquema(texto=f'<p>a<img src="{src}" alt="x"></p>').texto == "<p>a</p>"


def test_el_comentario_elimina_una_imagen_sin_src() -> None:
    assert ComentarioCrearEsquema(texto='<p>a<img alt="x"></p>').texto == "<p>a</p>"


@pytest.mark.parametrize(
    "atributo",
    [
        'onerror="alert(1)"',
        'style="position:fixed"',
        'width="9999"',
        'height="1"',
        'title="t"',
        'class="c"',
        'srcset="https://ejemplo.com/a.png 2x"',
        'loading="lazy"',
    ],
)
def test_el_comentario_quita_a_la_imagen_los_atributos_no_permitidos(atributo: str) -> None:
    texto = f'<p>a<img src="{_SRC}" alt="x" {atributo}></p>'
    assert ComentarioCrearEsquema(texto=texto).texto == f'<p>a<img src="{_SRC}" alt="x"></p>'


def test_el_texto_alternativo_de_la_imagen_no_lleva_signos_de_etiqueta() -> None:
    texto = f'<p><img src="{_SRC}" alt="a<b>c"></p>'
    assert ComentarioCrearEsquema(texto=texto).texto == f'<p><img src="{_SRC}" alt="abc"></p>'


def test_un_comentario_con_solo_una_imagen_es_valido() -> None:
    html = f'<p><img src="{_SRC}" alt="Captura de pantalla"></p>'
    assert ComentarioCrearEsquema(texto=html).texto == html


@pytest.mark.parametrize(
    "texto",
    [
        "<p> </p>",
        '<p><img src="https://ejemplo.com/a.png"></p>',
        '<p><img src="data:image/png;base64,iVBORw0KGgo="></p>',
        f'<p><img alt="{_SRC}"></p>',
    ],
)
def test_un_comentario_sin_texto_ni_imagenes_guardadas_se_rechaza(texto: str) -> None:
    with pytest.raises(ValidationError):
        ComentarioCrearEsquema(texto=texto)


def test_las_imagenes_no_cuentan_para_el_limite_de_5000_caracteres_visibles() -> None:
    imagen = f'<img src="{_SRC}" alt="Captura de pantalla">'
    html = f"<p>{'a' * 5000}{imagen}</p>"
    assert ComentarioCrearEsquema(texto=html).texto == html
    with pytest.raises(ValidationError):
        ComentarioCrearEsquema(texto=f"<p>{'a' * 5001}{imagen}</p>")


def test_sanear_de_nuevo_un_comentario_con_imagenes_no_lo_cambia() -> None:
    guardado = ComentarioCrearEsquema(texto=f'<p>a<img src="{_SRC}" alt="b &amp; c"></p>').texto
    assert ComentarioCrearEsquema(texto=guardado).texto == guardado


def test_el_contrato_del_comentario_menciona_las_imagenes() -> None:
    texto = ComentarioCrearEsquema.model_json_schema()["properties"]["texto"]
    assert "/api/v1/imagenes/" in texto["description"]
