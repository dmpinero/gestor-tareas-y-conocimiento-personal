"""Troceado del texto de una página para el índice de búsqueda.

Los trozos se hacen con párrafos enteros (una línea del texto es un párrafo) hasta
``tamano`` caracteres, y cada trozo repite al principio los últimos párrafos del
anterior que quepan en ``solape``, para no perder el contexto de una frase que cae
en el corte. Un párrafo más largo que ``tamano`` se parte por los espacios (con el
mismo solape, en palabras), y una palabra más larga, a la fuerza.
"""

from collections.abc import Sequence

TAMANO_POR_DEFECTO = 1200
SOLAPE_POR_DEFECTO = 200


def trocear(
    texto: str, tamano: int = TAMANO_POR_DEFECTO, solape: int = SOLAPE_POR_DEFECTO
) -> list[str]:
    """Los trozos de ``texto``, cada uno de ``tamano`` caracteres como mucho, sin
    líneas vacías ni espacios en los extremos de cada línea."""
    parrafos = [linea.strip() for linea in texto.split("\n") if linea.strip()]
    unidades: list[str] = []
    for parrafo in parrafos:
        if len(parrafo) <= tamano:
            unidades.append(parrafo)
        else:
            unidades.extend(_partir_parrafo(parrafo, tamano, solape))
    return _agrupar(unidades, "\n", tamano, solape)


def _partir_parrafo(parrafo: str, tamano: int, solape: int) -> list[str]:
    palabras: list[str] = []
    for palabra in parrafo.split():
        palabras.extend(palabra[i : i + tamano] for i in range(0, len(palabra), tamano))
    return _agrupar(palabras, " ", tamano, solape)


def _agrupar(unidades: Sequence[str], separador: str, tamano: int, solape: int) -> list[str]:
    """Junta ``unidades`` (cada una de ``tamano`` como mucho) con ``separador`` en
    trozos de hasta ``tamano``, solapando las últimas unidades que quepan en
    ``solape``."""
    trozos: list[str] = []
    actual: list[str] = []
    for unidad in unidades:
        if actual and len(separador.join([*actual, unidad])) > tamano:
            trozos.append(separador.join(actual))
            actual = _cola_para_solapar(actual, separador, solape)
            if len(separador.join([*actual, unidad])) > tamano:
                actual = []
        actual.append(unidad)
    # Siempre acaba con alguna unidad nueva: solo se corta justo antes de añadir una.
    if actual:
        trozos.append(separador.join(actual))
    return trozos


def _cola_para_solapar(unidades: list[str], separador: str, solape: int) -> list[str]:
    cola: list[str] = []
    for unidad in reversed(unidades):
        if len(separador.join([unidad, *cola])) > solape:
            break
        cola.insert(0, unidad)
    return cola
