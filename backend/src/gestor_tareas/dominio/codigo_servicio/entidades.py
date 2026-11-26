from dataclasses import dataclass

LONGITUD_MINIMA_CODIGO_SERVICIO = 2
LONGITUD_MAXIMA_CODIGO_SERVICIO = 20

# Espacios de ECMA-262 (`\s` del `pattern` que publica el contrato y del
# validador del frontend): WhiteSpace y LineTerminator. Es la misma lista que
# `interfaces.api.v1.esquemas.texto.ESPACIOS_JSON_SCHEMA`; no se usa `str.isspace`
# porque Python considera espacios otros caracteres (p. ej. `\x1c` o `\x85`).
ESPACIOS_ECMA = (
    "\t\n\v\f\r \u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006"
    "\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff"
)

# `pattern` que publica el contrato: de 2 a 20 caracteres sin espacios. Los
# espacios de los extremos se admiten porque la API los recorta antes de validar
# (un nombre como "AB " se guarda como "AB"); por eso la longitud va en el
# `pattern` y no en `minLength`/`maxLength`, que contarían esos espacios.
PATRON_CODIGO_SERVICIO = (
    rf"^\s*\S{{{LONGITUD_MINIMA_CODIGO_SERVICIO},{LONGITUD_MAXIMA_CODIGO_SERVICIO}}}\s*$"
)


@dataclass(frozen=True)
class CodigoServicio:
    """Código de servicio del catálogo (p. ej. «AXAS0024»). El nombre es único sin
    distinguir mayúsculas; el alta de oportunidades AXAS MS3 usa sus 2 últimos
    caracteres."""

    id: int
    nombre: str


class NombreCodigoServicioInvalidoError(ValueError):
    """El nombre no cumple las reglas de ``validar_nombre_codigo_servicio``.

    Es un ``ValueError`` para que la validación de la API lo traduzca a un 422."""


def validar_nombre_codigo_servicio(nombre: str) -> str:
    """Comprueba que el nombre, ya recortado, tenga de 2 a 20 caracteres y ningún
    espacio. Lo devuelve tal cual si es válido."""
    if len(nombre) < LONGITUD_MINIMA_CODIGO_SERVICIO:
        raise NombreCodigoServicioInvalidoError(
            f"El código de servicio debe tener al menos "
            f"{LONGITUD_MINIMA_CODIGO_SERVICIO} caracteres."
        )
    if len(nombre) > LONGITUD_MAXIMA_CODIGO_SERVICIO:
        raise NombreCodigoServicioInvalidoError(
            f"El código de servicio no puede superar los "
            f"{LONGITUD_MAXIMA_CODIGO_SERVICIO} caracteres."
        )
    if any(caracter in ESPACIOS_ECMA for caracter in nombre):
        raise NombreCodigoServicioInvalidoError("El código de servicio no puede contener espacios.")
    return nombre
