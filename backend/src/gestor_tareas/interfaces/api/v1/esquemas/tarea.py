import re
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, PlainValidator, WithJsonSchema

# Fecha y hora local en ISO 8601 sin zona horaria: "YYYY-MM-DDTHH:MM:SS", con una
# fracción de segundo opcional que se descarta. El patrón solo admite fechas reales
# del calendario (incluido el 29 de febrero de los años bisiestos) para que el
# contrato OpenAPI describa exactamente lo que acepta la API.
_ANIO = r"(?:\d{3}[1-9]|\d{2}[1-9]\d|\d[1-9]\d{2}|[1-9]\d{3})"
_ANIO_BISIESTO = r"(?:\d{2}(?:0[48]|[2468][048]|[13579][26])|(?:0[48]|[2468][048]|[13579][26])00)"
_FECHA = (
    rf"(?:{_ANIO}-(?:(?:0[13578]|1[02])-(?:0[1-9]|[12]\d|3[01])"
    r"|(?:0[469]|11)-(?:0[1-9]|[12]\d|30)"
    r"|02-(?:0[1-9]|1\d|2[0-8]))"
    rf"|{_ANIO_BISIESTO}-02-29)"
)
_HORA = r"(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d{1,6})?"
PATRON_FECHA_HORA = rf"^{_FECHA}T{_HORA}$"
_PATRON_FECHA_HORA = re.compile(PATRON_FECHA_HORA)


def _validar_fecha_hora(valor: object) -> datetime:
    """Convierte la fecha y hora recibida en un ``datetime`` sin zona horaria.

    Es la hora local tal como la escribe la persona usuaria (supuesto de S8). Un
    valor con zona horaria (``Z`` o ``+01:00``) se rechaza con 422 en vez de
    convertirlo, porque no hay una zona de referencia a la que traducirlo. La
    precisión es de segundos, como el formulario y la columna ``DATETIME``: los
    microsegundos se descartan para que la respuesta salga siempre como
    ``YYYY-MM-DDTHH:MM:SS``.
    """
    if isinstance(valor, datetime) and valor.tzinfo is None:
        return valor.replace(microsecond=0)
    if not isinstance(valor, str) or not _PATRON_FECHA_HORA.fullmatch(valor):
        raise ValueError("La fecha y hora debe tener el formato YYYY-MM-DDTHH:MM:SS sin zona")
    return datetime.fromisoformat(valor).replace(microsecond=0)


FechaHoraLocal = Annotated[
    datetime,
    PlainValidator(_validar_fecha_hora),
    PlainSerializer(
        lambda valor: valor.isoformat(timespec="seconds"), return_type=str, when_used="json"
    ),
    WithJsonSchema(
        {
            "type": "string",
            "pattern": PATRON_FECHA_HORA,
            "description": "Fecha y hora local sin zona horaria (YYYY-MM-DDTHH:MM:SS).",
            "examples": ["2026-11-09T10:30:00"],
        }
    ),
]


class TareaCrearEsquema(BaseModel):
    # Se recortan los espacios antes de validar: un nombre o una descripción
    # formados solo por espacios quedan vacíos y se rechazan con 422.
    model_config = ConfigDict(str_strip_whitespace=True)

    nombre: str = Field(min_length=1, max_length=200)
    prioridad: int | None = Field(default=None, ge=1, le=5)
    descripcion: str = Field(min_length=1, max_length=500)
    fecha_hora: FechaHoraLocal


class TareaActualizarEsquema(TareaCrearEsquema):
    """Cuerpo de la edición: los mismos campos y validaciones que el alta."""


class TareaSalidaEsquema(BaseModel):
    id: int
    nombre: str
    prioridad: int | None
    descripcion: str
    fecha_hora: FechaHoraLocal
