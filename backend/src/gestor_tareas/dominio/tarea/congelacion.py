"""Contador de vencimiento congelado de las tareas terminadas.

Una tarea está congelada mientras está completada o en el estado DONE de su grupo
(cualquier grupo; el nombre se compara sin distinguir mayúsculas). Mientras lo está,
su contador de vencimiento muestra el tiempo que faltaba (o que había pasado) en el
instante en que se congeló, y deja de correr; al dejar de estarlo, vuelve a contar en
vivo desde su fecha de vencimiento.
"""

from datetime import datetime

NOMBRE_ESTADO_TERMINADO = "DONE"


def es_estado_terminado(nombre_estado: str | None) -> bool:
    """Si el estado es el DONE de su grupo (sin distinguir mayúsculas)."""
    return (
        nombre_estado is not None and nombre_estado.casefold() == NOMBRE_ESTADO_TERMINADO.casefold()
    )


def esta_congelada(completada: bool, nombre_estado: str | None) -> bool:
    """Si la tarea está completada o en el estado DONE."""
    return completada or es_estado_terminado(nombre_estado)


def instante_de_congelacion(
    anterior: datetime | None,
    completada: bool,
    nombre_estado: str | None,
    ahora: datetime,
) -> datetime | None:
    """El instante en que queda congelada la tarea tras un cambio, o ``None`` si no
    está congelada.

    ``anterior`` es el instante que tenía antes del cambio, ``completada`` y
    ``nombre_estado`` cómo queda, y ``ahora`` el instante del cambio. Si ya estaba
    congelada conserva su instante (también al pasar de completada a DONE o al
    revés, o al cambiar su vencimiento); si se congela ahora, es ``ahora``.
    """
    if not esta_congelada(completada, nombre_estado):
        return None
    return anterior if anterior is not None else ahora
