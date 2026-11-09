import re
from datetime import datetime
from typing import Annotated

from pydantic import (
    BaseModel,
    BeforeValidator,
    Field,
    PlainSerializer,
    PlainValidator,
    WithJsonSchema,
)

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


# Espacios según ECMA-262 (`\s` en las expresiones regulares de JSON Schema):
# WhiteSpace y LineTerminator. Python (`str.isspace`) y el motor de Rust de
# Pydantic usan otras definiciones (p. ej. Python trata `\x1c` como espacio),
# así que se fija la lista para que contrato y validación coincidan.
ESPACIOS_JSON_SCHEMA = (
    "\t\n\v\f\r \u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006"
    "\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff"
)


def _recortar_espacios(valor: object) -> object:
    """Recorta los espacios de JSON Schema de los extremos del texto.

    Tras recortar, un texto no vacío contiene al menos un carácter que no es
    espacio, que es justo lo que publica el contrato con `pattern: "\\S"`.
    """
    return valor.strip(ESPACIOS_JSON_SCHEMA) if isinstance(valor, str) else valor


# Texto obligatorio: se recorta antes de validar, así que uno formado solo por
# espacios (incluidos los Unicode, como el espacio duro) queda vacío y da 422.
TextoObligatorio = Annotated[str, BeforeValidator(_recortar_espacios)]

# Solo se publica en el contrato: la comprobación real es `min_length=1` tras
# recortar, para no depender de la semántica de `\S` del motor de Pydantic.
_PATRON_NO_VACIO = {"pattern": r"\S"}


def _normalizar_prioridad(valor: object) -> object:
    """Aplica la semántica de `integer` de JSON Schema.

    `3.0` es un entero válido y se convierte en 3; los booleanos no son enteros
    (en Python `True` es un `int`, así que se rechazan explícitamente). El resto
    lo valida `int` en modo estricto, que rechaza cadenas como `"2"` y `2.5`.
    """
    if isinstance(valor, bool):
        raise ValueError("La prioridad debe ser un número entero.")
    if isinstance(valor, float) and valor.is_integer():
        return int(valor)
    return valor


# Los límites van antes del `BeforeValidator`: en el orden inverso Pydantic
# publica `ge`/`le` en el JSON Schema en lugar de `minimum`/`maximum`.
PrioridadEntera = Annotated[
    int, Field(strict=True, ge=1, le=5), BeforeValidator(_normalizar_prioridad)
]


class TareaCrearEsquema(BaseModel):
    nombre: TextoObligatorio = Field(
        min_length=1, max_length=200, json_schema_extra=_PATRON_NO_VACIO
    )
    prioridad: PrioridadEntera | None = None
    descripcion: TextoObligatorio = Field(
        min_length=1, max_length=500, json_schema_extra=_PATRON_NO_VACIO
    )
    fecha_hora: FechaHoraLocal


class TareaActualizarEsquema(TareaCrearEsquema):
    """Cuerpo de la edición: los mismos campos y validaciones que el alta."""


class TareaSalidaEsquema(BaseModel):
    id: int
    nombre: str
    prioridad: int | None
    descripcion: str
    fecha_hora: FechaHoraLocal
