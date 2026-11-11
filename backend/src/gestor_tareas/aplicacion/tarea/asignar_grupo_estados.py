from gestor_tareas.dominio.grupo_estados.reglas import estado_al_asignar, grupo_asignable
from gestor_tareas.dominio.grupo_estados.repositorio import RepositorioGruposEstados
from gestor_tareas.dominio.tarea.entidades import (
    ReferenciaEstado,
    ReferenciaGrupoEstados,
    Tarea,
)


class GrupoPedido:
    """Grupo de estados pedido para una tarea, leído al principio de la transacción.

    Se lee antes que la tarea para tomar los bloqueos siempre en el mismo orden
    (primero el grupo y después la tarea), y se valida después, para que una tarea
    que no existe responda que no existe aunque el grupo tampoco valga.
    """

    def __init__(self, repositorio: RepositorioGruposEstados, id_grupo: int | None) -> None:
        self._id_grupo = id_grupo
        self._grupo = repositorio.leer_para_asignar(id_grupo) if id_grupo is not None else None

    def asignar(self, tarea: Tarea) -> None:
        """Deja la tarea en el grupo pedido y en el estado que le corresponde.

        Sin grupo, la tarea queda sin grupo ni estado. Con el mismo grupo que ya
        tenía, conserva su estado; con otro, queda en su primer estado. Lanza
        ``AsignacionDeEstadoInvalidaError`` si el grupo no existe o no tiene estados.
        """
        if self._id_grupo is None:
            tarea.grupo_estados, tarea.estado = None, None
            return
        grupo = grupo_asignable(self._grupo, self._id_grupo)
        estado = estado_al_asignar(
            grupo,
            tarea.grupo_estados.id if tarea.grupo_estados else None,
            tarea.estado.id if tarea.estado else None,
        )
        tarea.grupo_estados = ReferenciaGrupoEstados(id=grupo.id, nombre=grupo.nombre)
        tarea.estado = ReferenciaEstado(id=estado.id, nombre=estado.nombre)
