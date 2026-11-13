"""Traducción de las claves únicas de nombre repetidas de MySQL."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager

from sqlalchemy.exc import IntegrityError

from gestor_tareas.dominio.excepciones import NombreDuplicadoError

# Error de MySQL por una clave única repetida.
_CLAVE_DUPLICADA = 1062


def _es_clave_duplicada(error: IntegrityError) -> bool:
    argumentos = getattr(error.orig, "args", ())
    return bool(argumentos) and argumentos[0] == _CLAVE_DUPLICADA


@contextmanager
def nombre_unico(error_si_repetido: Callable[[], NombreDuplicadoError]) -> Iterator[None]:
    """Traduce la clave única de nombre repetida en ``NombreDuplicadoError``.

    Solo para bloques en los que el nombre es la única clave única que puede
    repetir una petición: las posiciones las asigna el repositorio con el padre
    bloqueado.
    """
    try:
        yield
    except IntegrityError as error:
        if not _es_clave_duplicada(error):
            raise
        raise error_si_repetido() from error
