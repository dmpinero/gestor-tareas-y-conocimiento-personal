"""Validación de los textos de los cuerpos, común a todos los esquemas."""

from typing import Annotated

from pydantic import BeforeValidator

# Espacios según ECMA-262 (`\s` en las expresiones regulares de JSON Schema):
# WhiteSpace y LineTerminator. Python (`str.isspace`) y el motor de Rust de
# Pydantic usan otras definiciones (p. ej. Python trata `\x1c` como espacio),
# así que se fija la lista para que contrato y validación coincidan.
ESPACIOS_JSON_SCHEMA = "\t\n\v\f\r                  　﻿"


def recortar_espacios(valor: object) -> object:
    """Recorta los espacios de JSON Schema de los extremos del texto.

    Tras recortar, un texto no vacío contiene al menos un carácter que no es
    espacio, que es justo lo que publica el contrato con `pattern: "\\S"`.
    """
    return valor.strip(ESPACIOS_JSON_SCHEMA) if isinstance(valor, str) else valor


# Texto obligatorio: se recorta antes de validar, así que uno formado solo por
# espacios (incluidos los Unicode, como el espacio duro) queda vacío y da 422.
TextoObligatorio = Annotated[str, BeforeValidator(recortar_espacios)]

# Solo se publica en el contrato: la comprobación real es `min_length=1` tras
# recortar, para no depender de la semántica de `\S` del motor de Pydantic.
PATRON_NO_VACIO = {"pattern": r"\S"}
