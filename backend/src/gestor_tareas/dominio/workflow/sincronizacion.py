"""Cambios que llevarían las tareas abiertas de un workflow a sus pasos actuales.

Las subtareas de una tarea son una copia de los pasos de su workflow, hecha al
asignárselo: añadir o renombrar pasos después no las altera. Sincronizar las tareas
con el workflow, que solo se hace a petición de la persona usuaria, añade una
subtarea por cada paso que no tiene ninguna vinculada y da a cada subtarea vinculada
el nombre actual de su paso. Las subtareas de un paso eliminado (ya sin vínculo), las
añadidas a mano y las de pasos de otro workflow no cambian.
"""

from collections.abc import Iterable
from dataclasses import dataclass, field

from gestor_tareas.dominio.tarea.entidades import Tarea
from gestor_tareas.dominio.workflow.entidades import PasoWorkflow, Workflow


@dataclass
class RenombreSubtarea:
    """Subtarea vinculada a un paso que tomará el nombre actual del paso."""

    id_subtarea: int
    nombre_actual: str
    nombre_nuevo: str


@dataclass
class CambiosDeTarea:
    """Lo que cambiaría en una tarea al sincronizarla con su workflow.

    ``pasos_nuevos`` son los pasos sin subtarea vinculada, por número;
    ``renombres``, las subtareas cuyo nombre no es el de su paso, en el orden en que
    se muestran.
    """

    id_tarea: int
    nombre_tarea: str
    pasos_nuevos: list[PasoWorkflow] = field(default_factory=list)
    renombres: list[RenombreSubtarea] = field(default_factory=list)


def cambios_de_tarea(workflow: Workflow, tarea: Tarea) -> CambiosDeTarea | None:
    """Los cambios que llevarían la tarea a los pasos del workflow, o ``None`` si ya
    está al día. La tarea debe ser del workflow y no estar completada (lo comprueba
    quien la lee)."""
    if tarea.id is None:
        raise ValueError("La tarea a sincronizar debe tener id")
    pasos = {paso.id: paso for paso in workflow.pasos}
    vinculados = {s.paso_id for s in tarea.subtareas if s.paso_id is not None}
    nuevos = [
        p for p in sorted(workflow.pasos, key=lambda p: p.numero or 0) if p.id not in vinculados
    ]
    renombres = []
    for subtarea in tarea.subtareas:
        paso = pasos.get(subtarea.paso_id) if subtarea.paso_id is not None else None
        if paso is not None and subtarea.id is not None and subtarea.nombre != paso.nombre:
            renombres.append(
                RenombreSubtarea(
                    id_subtarea=subtarea.id, nombre_actual=subtarea.nombre, nombre_nuevo=paso.nombre
                )
            )
    if not nuevos and not renombres:
        return None
    return CambiosDeTarea(
        id_tarea=tarea.id, nombre_tarea=tarea.nombre, pasos_nuevos=nuevos, renombres=renombres
    )


def cambios_pendientes(workflow: Workflow, tareas: Iterable[Tarea]) -> list[CambiosDeTarea]:
    """Los cambios de cada tarea que no está al día, en el orden recibido."""
    return [c for c in (cambios_de_tarea(workflow, t) for t in tareas) if c is not None]
