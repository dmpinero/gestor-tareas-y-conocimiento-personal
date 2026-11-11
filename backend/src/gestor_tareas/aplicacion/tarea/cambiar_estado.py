from gestor_tareas.aplicacion.reintentos import reintentar_si_hay_conflicto
from gestor_tareas.dominio.excepciones import (
    AsignacionDeEstadoInvalidaError,
    EntidadNoEncontradaError,
)
from gestor_tareas.dominio.grupo_estados.reglas import estado_de_destino
from gestor_tareas.dominio.grupo_estados.repositorio import RepositorioGruposEstados
from gestor_tareas.dominio.tarea.entidades import ReferenciaEstado, Tarea
from gestor_tareas.dominio.tarea.repositorio import RepositorioTareas


class CambiarEstadoTarea:
    """Mueve una tarea a otro estado de su grupo de estados.

    Cualquier estado del grupo es alcanzable desde cualquier otro: no hay secuencia.
    Solo cambia el estado; el resto de datos de la tarea se conserva.
    """

    def __init__(
        self, repositorio: RepositorioTareas, repositorio_grupos: RepositorioGruposEstados
    ) -> None:
        self._repositorio = repositorio
        self._repositorio_grupos = repositorio_grupos

    def ejecutar(self, id_tarea: int, id_estado: int) -> Tarea:
        def guardar() -> Tarea:
            # Los bloqueos se toman como en el resto de operaciones: primero el grupo y
            # después la tarea. Para saber qué grupo bloquear, antes se lee la tarea
            # sin bloqueo; después se vuelve a leer con bloqueo, ya actualizada.
            leida = self._repositorio.obtener_por_id(id_tarea)
            if leida is None:
                raise _tarea_no_encontrada(id_tarea)
            if leida.grupo_estados is None:
                raise _sin_grupo(id_tarea)
            grupo = self._repositorio_grupos.leer_para_asignar(leida.grupo_estados.id)
            tarea = self._repositorio.obtener_para_modificar(id_tarea)
            if tarea is None:
                raise _tarea_no_encontrada(id_tarea)
            if tarea.grupo_estados is None:
                raise _sin_grupo(id_tarea)
            if grupo is None or tarea.grupo_estados.id != grupo.id:
                # Otra petición le cambió el grupo entre las dos lecturas. Un estado
                # solo es de un grupo: el pedido, que se buscaba en el anterior, no es
                # del nuevo, como si este cambio hubiera llegado después de aquel.
                raise AsignacionDeEstadoInvalidaError(
                    f"El estado con id {id_estado} no es del grupo de estados "
                    f"«{tarea.grupo_estados.nombre}» de la tarea"
                )
            estado = estado_de_destino(grupo, id_estado)
            return self._repositorio.cambiar_estado(
                id_tarea, ReferenciaEstado(id=estado.id, nombre=estado.nombre)
            )

        # Si choca con otra petición simultánea (p. ej. el borrado del estado), se
        # repite entera.
        return reintentar_si_hay_conflicto(guardar)


def _tarea_no_encontrada(id_tarea: int) -> EntidadNoEncontradaError:
    return EntidadNoEncontradaError(f"No existe la tarea con id {id_tarea}")


def _sin_grupo(id_tarea: int) -> AsignacionDeEstadoInvalidaError:
    return AsignacionDeEstadoInvalidaError(f"La tarea con id {id_tarea} no tiene grupo de estados")
