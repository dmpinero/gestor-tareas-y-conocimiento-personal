from gestor_tareas.aplicacion.reintentos import reintentar_si_hay_conflicto
from gestor_tareas.dominio.excepciones import EntidadNoEncontradaError
from gestor_tareas.dominio.tarea.entidades import Tarea
from gestor_tareas.dominio.tarea.repositorio import RepositorioTareas


class MarcarPasoHecho:
    """Marca un paso de una oportunidad como hecho o lo deja pendiente.

    Solo cambia ese paso; el resto de datos de la tarea se conserva.
    """

    def __init__(self, repositorio: RepositorioTareas) -> None:
        self._repositorio = repositorio

    def ejecutar(self, id_tarea: int, id_paso: int, hecho: bool) -> Tarea:
        def guardar() -> Tarea:
            tarea = self._repositorio.cambiar_hecho_paso(id_tarea, id_paso, hecho)
            if tarea is not None:
                return tarea
            if self._repositorio.obtener_por_id(id_tarea) is None:
                raise EntidadNoEncontradaError(f"No existe la tarea con id {id_tarea}")
            raise EntidadNoEncontradaError(
                f"No existe el paso con id {id_paso} en la tarea con id {id_tarea}"
            )

        # Si choca con otra petición simultánea sobre la misma tarea, se repite.
        return reintentar_si_hay_conflicto(guardar)
