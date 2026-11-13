"""Saneado del HTML de los comentarios y cálculo de su texto visible.

Los comentarios se escriben con un editor de texto enriquecido y se guardan como
HTML saneado con una lista blanca: lo que no está en ella se elimina (no se
rechaza). Un texto sin ninguna etiqueta (clientes de la API, datos antiguos) se
convierte en párrafos, uno por línea, con sus caracteres especiales escapados.
"""

import re
from html import escape
from html.parser import HTMLParser

import nh3

# Etiquetas que admite el editor: negrita, cursiva, subrayado, tachado, listas,
# enlaces, color del texto (span) y resaltado (mark).
ETIQUETAS_PERMITIDAS = frozenset(
    {"p", "br", "strong", "em", "u", "s", "ul", "ol", "li", "a", "span", "mark"}
)

# `rel` no figura: nh3 lo fija siempre en los enlaces (ver REL_ENLACES).
_ATRIBUTOS_PERMITIDOS = {
    "a": {"href", "target"},
    "span": {"style"},
    "mark": {"style", "data-color"},
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


def _filtrar_atributo(etiqueta: str, atributo: str, valor: str) -> str | None:
    """Ajusta por etiqueta lo que nh3 solo sabe filtrar de forma global: el
    `style` de cada etiqueta queda solo con su propiedad, y `target` solo admite
    `_blank`."""
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
    return saneado if _ETIQUETA.search(saneado) else f"<p>{saneado}</p>"


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
