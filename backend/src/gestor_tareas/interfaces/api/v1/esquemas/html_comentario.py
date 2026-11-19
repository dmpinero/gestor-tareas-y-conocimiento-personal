"""Saneado del HTML de los comentarios y cálculo de su texto visible.

Los comentarios se escriben con un editor de texto enriquecido y se guardan como
HTML saneado con una lista blanca: lo que no está en ella se elimina (no se
rechaza). Un texto sin ninguna etiqueta (clientes de la API, datos antiguos) se
convierte en párrafos, uno por línea, con sus caracteres especiales escapados.
Las imágenes (`img`) solo se conservan si apuntan a una imagen guardada en la
propia aplicación (`/api/v1/imagenes/<id>`).
"""

import re
from html import escape
from html.parser import HTMLParser

import nh3

from gestor_tareas.interfaces.api.v1.esquemas.imagen import PATRON_URL_IMAGEN

# Etiquetas que admite el editor: negrita, cursiva, subrayado, tachado, listas,
# enlaces, color del texto (span), resaltado (mark) e imágenes guardadas (img).
ETIQUETAS_PERMITIDAS = frozenset(
    {"p", "br", "strong", "em", "u", "s", "ul", "ol", "li", "a", "span", "mark", "img"}
)

# `rel` no figura: nh3 lo fija siempre en los enlaces (ver REL_ENLACES).
_ATRIBUTOS_PERMITIDOS = {
    "a": {"href", "target"},
    "span": {"style"},
    "mark": {"style", "data-color"},
    "img": {"src", "alt"},
}

_ESQUEMAS_URL = {"http", "https", "mailto"}

REL_ENLACES = "noopener noreferrer nofollow"

# Única propiedad CSS que conserva cada etiqueta con `style`.
_PROPIEDAD_ESTILO = {"span": "color", "mark": "background-color"}

# Valores de color admitidos: nombres, hexadecimales y funciones como rgb()/hsl()
# con números; nada de url(), comillas, barras invertidas ni punto y coma.
_VALOR_COLOR = re.compile(r"[#a-zA-Z0-9(),.%\s-]{1,50}")

_DESTINOS_ENLACE = {"_blank"}

# Algo que parece una etiqueta, un comentario o una declaración HTML.
_ETIQUETA = re.compile(r"</?[a-zA-Z]|<!")

_SALTO_DE_LINEA = re.compile(r"\r\n|\r|\n")

# Una imagen del HTML ya saneado. Su `src` (si lo tiene) ya está validado y su
# `alt` no lleva `<` ni `>` (ver _filtrar_atributo), así que el primer `>` la cierra.
_IMAGEN = re.compile(r"<img\b[^>]*>")
_IMAGEN_CON_SRC = re.compile(r'<img\b[^>]*\ssrc="[^"]+"[^>]*>')

_LONGITUD_MAXIMA_ALT = 200


def _filtrar_atributo(etiqueta: str, atributo: str, valor: str) -> str | None:
    """Ajusta por etiqueta lo que nh3 solo sabe filtrar de forma global: el
    `style` de cada etiqueta queda solo con su propiedad, `target` solo admite
    `_blank`, el `src` de una imagen solo puede ser la URL de una imagen guardada
    y su `alt` pierde los signos de etiqueta y se acorta."""
    if etiqueta == "img":
        if atributo == "src":
            return valor if PATRON_URL_IMAGEN.fullmatch(valor) else None
        return re.sub(r"[<>]", "", valor)[:_LONGITUD_MAXIMA_ALT]
    if atributo == "style":
        propiedad = _PROPIEDAD_ESTILO.get(etiqueta)
        declaraciones = []
        for declaracion in valor.split(";"):
            nombre, separador, valor_css = declaracion.partition(":")
            valor_css = valor_css.strip()
            if (
                separador
                and nombre.strip().lower() == propiedad
                and _VALOR_COLOR.fullmatch(valor_css)
            ):
                declaraciones.append(f"{propiedad}: {valor_css}")
        return "; ".join(declaraciones) or None
    if atributo == "target":
        return valor if valor in _DESTINOS_ENLACE else None
    return valor


def _texto_a_parrafos(texto: str) -> str:
    """Un párrafo por línea, escapado; una línea vacía es `<p></p>`."""
    return "".join(f"<p>{escape(linea, quote=False)}</p>" for linea in _SALTO_DE_LINEA.split(texto))


def sanear_html(texto: str) -> str:
    """Devuelve el HTML saneado del comentario.

    Si el texto no contiene ninguna etiqueta se trata como texto plano y se
    convierte en párrafos (uno por línea) antes de sanearlo. Si tras sanearlo no
    queda ninguna etiqueta (p. ej. `<div>a &lt; b</div>`), su contenido, ya escapado,
    se envuelve en un párrafo: así sanear de nuevo lo guardado no lo cambia.
    """
    if not _ETIQUETA.search(texto):
        texto = _texto_a_parrafos(texto)
    saneado = nh3.clean(
        texto,
        tags=set(ETIQUETAS_PERMITIDAS),
        # Con "*" vacío no queda ningún atributo genérico: nh3 deja por
        # defecto lang y title en todas las etiquetas.
        attributes={"*": set(), **_ATRIBUTOS_PERMITIDOS},
        attribute_filter=_filtrar_atributo,
        url_schemes=_ESQUEMAS_URL,
        link_rel=REL_ENLACES,
        filter_style_properties=set(_PROPIEDAD_ESTILO.values()),
        strip_comments=True,
    )
    # nh3 no sabe quitar una etiqueta por el valor de un atributo: una imagen a la
    # que le ha quitado el `src` (externo, `data:`, otra ruta…) se elimina aquí.
    saneado = _IMAGEN.sub(lambda m: m[0] if _IMAGEN_CON_SRC.fullmatch(m[0]) else "", saneado)
    return saneado if _ETIQUETA.search(saneado) else f"<p>{saneado}</p>"


def contiene_imagenes(html: str) -> bool:
    """Si el HTML ya saneado tiene alguna imagen guardada (cuenta como contenido
    aunque no haya texto visible)."""
    return _IMAGEN_CON_SRC.search(html) is not None


class _ExtractorTexto(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.partes: list[str] = []

    def handle_data(self, data: str) -> None:
        self.partes.append(data)


def texto_visible(html: str) -> str:
    """El texto que se ve del HTML: sin etiquetas y con las entidades decodificadas
    (sin recortar)."""
    extractor = _ExtractorTexto()
    extractor.feed(html)
    extractor.close()
    return "".join(extractor.partes)
