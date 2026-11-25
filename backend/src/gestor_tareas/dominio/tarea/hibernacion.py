"""Hibernación de las tareas.

Mientras una tarea está hibernada, su contador de vencimiento deja de correr desde el
instante en que se hibernó, igual que el de una tarea congelada. Al reanudarla, su
fecha de vencimiento (si tiene) se corre exactamente el tiempo que estuvo hibernada,
así que le queda el mismo tiempo que cuando se hibernó. Se puede hibernar y reanudar
cuantas veces se quiera, pero no hibernar una tarea que ya lo está ni reanudar una que
no lo está.

La hibernación es independiente de la congelación: completar, dejar pendiente o
cambiar de estado una tarea hibernada no la reanuda.
"""

from datetime import datetime


class EstadoDeHibernacionInvalidoError(Exception):
    """Se lanza al hibernar una tarea que ya está hibernada o al reanudar una que no
    lo está."""


def vencimiento_al_reanudar(
    fecha_vencimiento: datetime | None, hibernada_desde: datetime, ahora: datetime
) -> datetime | None:
    """La fecha de vencimiento de la tarea al reanudarla: la que tenía (hora local, sin
    zona) corrida el tiempo que ha estado hibernada, de ``hibernada_desde`` a
    ``ahora`` (instantes en UTC), o ``None`` si no tiene vencimiento."""
    if fecha_vencimiento is None:
        return None
    return fecha_vencimiento + (ahora - hibernada_desde)
