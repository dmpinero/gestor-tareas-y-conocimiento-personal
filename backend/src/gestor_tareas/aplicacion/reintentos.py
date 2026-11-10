import secrets
import time
from collections.abc import Callable

from gestor_tareas.dominio.excepciones import ConflictoDeConcurrenciaError

INTENTOS_POR_CONFLICTO = 3


def reintentar_si_hay_conflicto[T](
    operacion: Callable[[], T], intentos: int = INTENTOS_POR_CONFLICTO
) -> T:
    """Ejecuta la operación y la repite entera si choca con otra simultánea.

    La operación debe ser una unidad de trabajo completa (leer, dar de alta y
    guardar), porque el conflicto deshace toda la transacción. Entre intentos
    espera unos milisegundos al azar para que las peticiones no vuelvan a chocar
    a la vez. Si se agotan los intentos, se propaga el último conflicto.
    """
    if intentos < 1:
        raise ValueError("intentos debe ser al menos 1")
    for intento in range(1, intentos):
        try:
            return operacion()
        except ConflictoDeConcurrenciaError:
            time.sleep((10 + secrets.randbelow(40)) * intento / 1000)
    return operacion()
