from gestor_tareas.aplicacion.reintentos import reintentar_si_hay_conflicto
from gestor_tareas.aplicacion.tarea.errores_subtarea import subtarea_no_encontrada
from gestor_tareas.dominio.persona.repositorio import RepositorioPersonas
from gestor_tareas.dominio.tarea.entidades import Subtarea, Tarea
from gestor_tareas.dominio.tarea.repositorio import RepositorioTareas


class EditarSubtarea:
    """Sustituye el nombre, la persona asignada y la prioridad de una subtarea.

    Es un reemplazo completo: sin persona o sin prioridad, se vacían. El estado
    resuelta se conserva. La persona se busca en su catálogo sin distinguir
    mayúsculas (se conserva la grafía guardada) y se da de alta si no existe, como
    al añadir la subtarea. Si la tarea no tiene esa subtarea, no se da de alta nadie.
    """

    def __init__(
        self, repositorio: RepositorioTareas, repositorio_personas: RepositorioPersonas
    ) -> None:
        self._repositorio = repositorio
        self._repositorio_personas = repositorio_personas

    def ejecutar(
        self,
        id_tarea: int,
        id_subtarea: int,
        nombre: str,
        asignado: str | None = None,
        prioridad: int | None = None,
    ) -> Tarea:
        def guardar() -> Tarea:
            if asignado is not None:
                (persona,) = self._repositorio_personas.obtener_o_crear([asignado])
                asignado_guardado = persona.nombre
            else:
                asignado_guardado = None
            subtarea = Subtarea(
                id=id_subtarea, nombre=nombre, asignado=asignado_guardado, prioridad=prioridad
            )
            tarea = self._repositorio.editar_subtarea(id_tarea, subtarea)
            if tarea is None:
                raise subtarea_no_encontrada(self._repositorio, id_tarea, id_subtarea)
            return tarea

        # Dar de alta la persona y guardar la subtarea es una sola transacción: si
        # choca con otra petición simultánea, se repite entera.
        return reintentar_si_hay_conflicto(guardar)
