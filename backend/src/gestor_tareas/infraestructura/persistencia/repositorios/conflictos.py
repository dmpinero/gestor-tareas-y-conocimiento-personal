"""Traducción de los choques entre transacciones simultáneas de MySQL."""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from gestor_tareas.dominio.excepciones import ConflictoDeConcurrenciaError

# 1213: interbloqueo (InnoDB deshace toda la transacción de la víctima).
# 1205: se agotó la espera de un bloqueo.
_CODIGOS_CONFLICTO = frozenset({1213, 1205})


def _es_conflicto(error: BaseException) -> bool:
    """Busca un error de conflicto en la cadena de excepciones.

    Tras un interbloqueo dentro de un SAVEPOINT, SQLAlchemy intenta volver a él y
    falla con "SAVEPOINT ... does not exist" (1305), porque MySQL ya deshizo toda
    la transacción; el interbloqueo original queda en ``__context__``.
    """
    actual: BaseException | None = error
    while actual is not None:
        if isinstance(actual, DBAPIError) and actual.orig is not None:
            argumentos = getattr(actual.orig, "args", ())
            if argumentos and argumentos[0] in _CODIGOS_CONFLICTO:
                return True
        actual = actual.__cause__ or actual.__context__
    return False


@contextmanager
def traducir_conflictos(sesion: Session) -> Iterator[None]:
    """Convierte un interbloqueo o una espera agotada en ``ConflictoDeConcurrenciaError``.

    Antes deshace la transacción de la sesión, para que quien reintente empiece
    una nueva con una instantánea actual.
    """
    try:
        yield
    except DBAPIError as error:
        if not _es_conflicto(error):
            raise
        sesion.rollback()
        raise ConflictoDeConcurrenciaError(
            "La operación chocó con otra simultánea y se ha deshecho"
        ) from error
