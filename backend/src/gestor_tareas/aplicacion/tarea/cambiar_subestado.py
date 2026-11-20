from gestor_tareas.aplicacion.reintentos import reintentar_si_hay_conflicto
from gestor_tareas.aplicacion.tarea.resolver_catalogos import resolver_nombre
from gestor_tareas.dominio.excepciones import EntidadNoEncontradaError
from gestor_tareas.dominio.subestado.repositorio import RepositorioSubestados
from gestor_tareas.dominio.tarea.entidades import Tarea
from gestor_tareas.dominio.tarea.repositorio import RepositorioTareas


class CambiarSubestadoTarea:
    """Cambia solo el subestado de una tarea; el resto de sus datos se conserva.

    Con un nombre, se busca en el catálogo de subestados como en la edición (y se da
    de alta si no existe); con ``None``, la tarea queda sin subestado.
    """

    def __init__(
        self, repositorio: RepositorioTareas, repositorio_subestados: RepositorioSubestados
    ) -> None:
        self._repositorio = repositorio
        self._repositorio_subestados = repositorio_subestados

    def ejecutar(self, id_tarea: int, subestado: str | None) -> Tarea:
        def guardar() -> Tarea:
            # Antes de dar de alta nada en el catálogo se comprueba que la tarea existe.
            if self._repositorio.obtener_por_id(id_tarea) is None:
                raise _tarea_no_encontrada(id_tarea)
            # Como en la edición, el subestado se bloquea (o se da de alta) antes que
            # la tarea, para que su borrado no se cruce con este guardado.
            nuevo = resolver_nombre(self._repositorio_subestados, subestado)
            tarea = self._repositorio.obtener_para_modificar(id_tarea)
            if tarea is None:
                raise _tarea_no_encontrada(id_tarea)
            tarea.subestado = nuevo
            return self._repositorio.actualizar(tarea)

        # Si choca con otra petición simultánea, se repite entera.
        return reintentar_si_hay_conflicto(guardar)


def _tarea_no_encontrada(id_tarea: int) -> EntidadNoEncontradaError:
    return EntidadNoEncontradaError(f"No existe la tarea con id {id_tarea}")
