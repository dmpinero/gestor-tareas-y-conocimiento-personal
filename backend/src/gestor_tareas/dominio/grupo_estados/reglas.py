"""Reglas de los grupos de estados y de los estados de las tareas."""

from collections import Counter
from collections.abc import Iterable, Sequence

from gestor_tareas.dominio.excepciones import (
    AsignacionDeEstadoInvalidaError,
    EntidadConDependenciasError,
    OrdenDeEstadosInvalidoError,
)
from gestor_tareas.dominio.grupo_estados.entidades import EstadoGrupo, GrupoEstados


def _enumerar(ids: Iterable[int]) -> str:
    return ", ".join(str(i) for i in sorted(ids))


def comprobar_nuevo_orden(ids_actuales: Iterable[int], ids_nuevos: Sequence[int]) -> None:
    """Comprueba que el nuevo orden incluye cada estado del grupo exactamente una vez.

    Lanza ``OrdenDeEstadosInvalidoError`` indicando los ids repetidos, los que faltan
    y los que no son del grupo.
    """
    actuales = set(ids_actuales)
    repetidos = {i for i, veces in Counter(ids_nuevos).items() if veces > 1}
    faltan = actuales - set(ids_nuevos)
    ajenos = set(ids_nuevos) - actuales
    problemas = [
        f"{etiqueta}: {_enumerar(ids)}"
        for etiqueta, ids in (
            ("repetidos", repetidos),
            ("faltan", faltan),
            ("no son del grupo", ajenos),
        )
        if ids
    ]
    if problemas:
        raise OrdenDeEstadosInvalidoError(
            "El nuevo orden debe incluir cada estado del grupo exactamente una vez "
            f"({'; '.join(problemas)})"
        )


def comprobar_destino_de_las_tareas(
    grupo: GrupoEstados, eliminado: EstadoGrupo, mover_a: int | None
) -> None:
    """Comprueba a dónde van las tareas del estado que se elimina.

    Si el estado tiene tareas, ``mover_a`` es obligatorio. Si se indica (tenga o no
    tareas), debe ser otro estado del mismo grupo. Si no, lanza
    ``EntidadConDependenciasError``.
    """
    if mover_a is None:
        if eliminado.tareas:
            raise EntidadConDependenciasError(
                f"El estado «{eliminado.nombre}» tiene {eliminado.tareas} tareas: indica en "
                "mover_a a qué otro estado del grupo moverlas"
            )
        return
    if mover_a == eliminado.id or grupo.estado(mover_a) is None:
        raise EntidadConDependenciasError(
            f"mover_a debe ser otro estado del grupo de estados «{grupo.nombre}»: el estado "
            f"con id {mover_a} no lo es"
        )


def grupo_asignable(grupo: GrupoEstados | None, id_grupo: int) -> GrupoEstados:
    """Comprueba que el grupo existe y tiene estados para asignarlo a una tarea."""
    if grupo is None:
        raise AsignacionDeEstadoInvalidaError(f"No existe el grupo de estados con id {id_grupo}")
    if not grupo.estados:
        raise AsignacionDeEstadoInvalidaError(
            f"El grupo de estados «{grupo.nombre}» no tiene estados: añade al menos uno "
            "antes de asignarlo a una tarea"
        )
    return grupo


def estado_al_asignar(
    grupo: GrupoEstados, id_grupo_actual: int | None, id_estado_actual: int | None
) -> EstadoGrupo:
    """Estado en el que queda una tarea al asignarle el grupo.

    Si la tarea ya estaba en ese grupo, conserva su estado; si no (no tenía grupo o
    tenía otro), queda en el primer estado del grupo. ``grupo`` debe tener estados
    (ver ``grupo_asignable``).
    """
    if grupo.id == id_grupo_actual and id_estado_actual is not None:
        actual = grupo.estado(id_estado_actual)
        if actual is not None:
            return actual
    return min(grupo.estados, key=lambda e: e.posicion or 0)


def estado_de_destino(grupo: GrupoEstados, id_estado: int) -> EstadoGrupo:
    """El estado del grupo de la tarea al que se mueve; cualquiera es alcanzable."""
    estado = grupo.estado(id_estado)
    if estado is None:
        raise AsignacionDeEstadoInvalidaError(
            f"El estado con id {id_estado} no es del grupo de estados «{grupo.nombre}» de la tarea"
        )
    return estado
