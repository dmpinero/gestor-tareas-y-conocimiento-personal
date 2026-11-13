from datetime import UTC, datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field, PlainSerializer, WithJsonSchema

from gestor_tareas.interfaces.api.v1.esquemas.html_comentario import sanear_html, texto_visible
from gestor_tareas.interfaces.api.v1.esquemas.texto import (
    PATRON_NO_VACIO,
    TextoObligatorio,
    recortar_espacios,
)

# Instante en UTC con precisión de segundos y "Z" final: "YYYY-MM-DDTHH:MM:SSZ".
PATRON_INSTANTE_UTC = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"


def _a_texto_utc(valor: datetime) -> str:
    return valor.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


InstanteUtc = Annotated[
    datetime,
    PlainSerializer(_a_texto_utc, return_type=str, when_used="json"),
    WithJsonSchema(
        {
            "type": "string",
            "format": "date-time",
            "pattern": PATRON_INSTANTE_UTC,
            "description": "Instante en UTC (YYYY-MM-DDTHH:MM:SSZ).",
            "examples": ["2026-11-10T16:30:05Z"],
        }
    ),
]


# Caracteres del texto visible (sin etiquetas, con las entidades decodificadas y
# sin los espacios de los extremos) y del HTML saneado que se guarda.
LONGITUD_MAXIMA_VISIBLE = 500
LONGITUD_MAXIMA_HTML = 10000


def _sanear_y_validar(texto: str) -> str:
    """Sanea el HTML y comprueba sus límites; devuelve el HTML saneado."""
    html = sanear_html(texto)
    visible = str(recortar_espacios(texto_visible(html)))
    if not visible:
        raise ValueError("El comentario no tiene texto visible")
    if len(visible) > LONGITUD_MAXIMA_VISIBLE:
        raise ValueError(
            f"El texto visible del comentario no puede pasar de {LONGITUD_MAXIMA_VISIBLE} "
            "caracteres"
        )
    if len(html) > LONGITUD_MAXIMA_HTML:
        raise ValueError(
            f"El HTML saneado del comentario no puede pasar de {LONGITUD_MAXIMA_HTML} caracteres"
        )
    return html


# Texto de un comentario: HTML o texto plano, que se guarda como HTML saneado.
TextoComentario = Annotated[TextoObligatorio, AfterValidator(_sanear_y_validar)]

_DESCRIPCION_TEXTO = (
    "HTML del comentario. Se sanea con una lista blanca (p, br, strong, em, u, s, ul, "
    "ol, li, a, span, mark; enlaces http/https/mailto) y lo demás se elimina; un texto "
    "sin etiquetas se convierte en un párrafo por línea. El texto visible (sin "
    f"etiquetas, con las entidades decodificadas y recortado) debe tener de 1 a "
    f"{LONGITUD_MAXIMA_VISIBLE} caracteres visibles, y el HTML saneado no puede pasar de "
    f"{LONGITUD_MAXIMA_HTML} caracteres (422 si no)."
)


class ComentarioCrearEsquema(BaseModel):
    """Cuerpo del alta de un comentario: HTML (o texto plano) que se guarda saneado."""

    texto: TextoComentario = Field(
        min_length=1,
        max_length=LONGITUD_MAXIMA_HTML,
        description=_DESCRIPCION_TEXTO,
        json_schema_extra=PATRON_NO_VACIO,
    )


class ComentarioEditarEsquema(ComentarioCrearEsquema):
    """Cuerpo de la edición de un comentario: el texto nuevo, con las mismas reglas
    que el alta."""


class ComentarioSalidaEsquema(BaseModel):
    id: int
    texto: str = Field(description="HTML saneado del comentario.")
    creado: InstanteUtc = Field(
        description="Instante de alta en UTC; lo pone el servidor y no cambia al editar."
    )
    editado: InstanteUtc | None = Field(
        description="Instante de la última edición en UTC, o null si nunca se editó; lo "
        "pone el servidor."
    )
