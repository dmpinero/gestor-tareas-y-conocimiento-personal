from gestor_tareas.aplicacion.reintentos import reintentar_si_hay_conflicto
from gestor_tareas.dominio.excepciones import EntidadNoEncontradaError
from gestor_tareas.dominio.persona.repositorio import RepositorioPersonas
from gestor_tareas.dominio.tarea.entidades import Subtarea, Tarea
from gestor_tareas.dominio.tarea.repositorio import RepositorioTareas


class AnadirSubtarea:
    """Añade una subtarea pendiente al final de las de una tarea existente.

    La persona asignada se busca en su catálogo sin distinguir mayúsculas (se
    conserva la grafía guardada) y se da de alta si no existe, como las personas
    asignadas a una tarea. Si la tarea no existe, no se da de alta nadie.
    """

    def __init__(
        self, repositorio: RepositorioTareas, repositorio_personas: RepositorioPersonas
    ) -> None:
        self._repositorio = repositorio
        self._repositorio_personas = repositorio_personas

    def ejecutar(
        self,
        id_tarea: int,
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
            subtarea = Subtarea(nombre=nombre, asignado=asignado_guardado, prioridad=prioridad)
            tarea = self._repositorio.anadir_subtarea(id_tarea, subtarea)
            if tarea is None:
                raise EntidadNoEncontradaError(f"No existe la tarea con id {id_tarea}")
            return tarea

        # Dar de alta la persona y guardar la subtarea es una sola transacción: si
        # choca con otra petición simultánea, se repite entera.
        return reintentar_si_hay_conflicto(guardar)
