"""Reglas comunes a los nombres de los catálogos (etiquetas y personas)."""

from collections.abc import Iterable


def deduplicar_nombres(nombres: Iterable[str]) -> list[str]:
    """Quita los nombres repetidos sin distinguir mayúsculas.

    Se conserva la grafía de la primera aparición y el orden original.
    """
    vistos: set[str] = set()
    resultado: list[str] = []
    for nombre in nombres:
        clave = nombre.casefold()
        if clave not in vistos:
            vistos.add(clave)
            resultado.append(nombre)
    return resultado


def clave_orden_nombre(nombre: str) -> tuple[str, str]:
    """Orden alfabético sin distinguir mayúsculas; la grafía desempata."""
    return nombre.casefold(), nombre


def ordenar_nombres(nombres: Iterable[str]) -> list[str]:
    return sorted(nombres, key=clave_orden_nombre)
