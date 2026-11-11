from datetime import UTC, datetime
from typing import Annotated

from pydantic import BaseModel, Field, PlainSerializer, WithJsonSchema

from gestor_tareas.interfaces.api.v1.esquemas.texto import PATRON_NO_VACIO, TextoObligatorio

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


class ComentarioCrearEsquema(BaseModel):
    """Cuerpo del alta de un comentario. El texto se recorta por los extremos y
    conserva los saltos de línea de su interior."""

    texto: TextoObligatorio = Field(min_length=1, max_length=500, json_schema_extra=PATRON_NO_VACIO)


class ComentarioEditarEsquema(ComentarioCrearEsquema):
    """Cuerpo de la edición de un comentario: el texto nuevo, con las mismas reglas
    que el alta."""


class ComentarioSalidaEsquema(BaseModel):
    id: int
    texto: str
    creado: InstanteUtc = Field(
        description="Instante de alta en UTC; lo pone el servidor y no cambia al editar."
    )
    editado: InstanteUtc | None = Field(
        description="Instante de la última edición en UTC, o null si nunca se editó; lo "
        "pone el servidor."
    )
